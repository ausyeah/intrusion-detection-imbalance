"""第 5 周轻量化改进：类别权重 XGBoost + 特征筛选（红队后协议，结论限定所测协议内）。

协议（在看到任何结果之前固定，并记录于 configs/experiment_hyperparams.yaml）：
- 基线模型：类别权重 XGBoost（与第 3 周完全同参：300 树/depth 6/lr 0.1/hist，
  sample_weight=balanced），是第 3 周网格中 Balanced Acc 最优（0.6549）的配置。
- 特征筛选：XGBoost 增益重要性排序。排序模型在训练划分上拟合（seed 42，全量特征，
  类别权重）——筛选信息只来自训练划分，valid/test 不参与（防泄漏）。
- K 扫描：[194(全量), 128, 64, 32, 16, 8]，seed 42，在验证集上以 Macro-F1 选 K；
  并列取更小 K（轻量化优先）。测试集不参与选 K。
- 终评：选出的 K 与全量基线各跑 seeds [0,1,2] 在测试集评估；体积一律用纯模型口径
  （红队 S4 教训：pipeline 口径含采样器索引不可比；本脚本无采样器，两者一致）。
- 披露：特征排序模型自身用 seed 42 单次拟合，排序稳定性未做多种子检验（列入局限）。

产出：runs/lightweight/sweep.csv、final_metrics.csv、report.md、
     figures/lightweight_tradeoff.png
用法：python src/08_lightweight.py

--v2 方差补测（第 8 周，红队三轮 A1-2/A1-3/用户决策 T4；v1 行为与产物不变）：
- 数据：resplit.make_splits(seed) 每种子重切官方训练池；官方测试集冻结只 transform。
- 特征排序逐种子重做（排序模型在各 train_s 上 fit，random_state=seed）——直接回应
  v1 披露的「单次特征排序（seed 42）未做稳定性检验」局限；同时报告各种子 top-K
  特征集与 v1 top-K 的重合度（Jaccard）。
- K* 不重新选择：从 v1 封板产物 runs/lightweight/sweep.csv 按同一选型规则
  （验证 Macro-F1 最高、并列取更小 K）读出，保证「选型决策只做一次」不变。
- 终评：full 与 topK* 各 3 种子在测试集评估（真实方差）；每类 Recall 增量附 std。
- 产出：runs/lightweight_v2/、reports/week5/variance_recheck.md；v1 目录不写。
"""
import json
import pickle
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             f1_score, recall_score)
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
OUT = ROOT / "runs/lightweight"
FIGS = ROOT / "figures"
SEEDS = [0, 1, 2]
SWEEP_SEED = 42
K_LIST = [194, 128, 64, 32, 16, 8]

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def make_cw_xgb(seed):
    return XGBClassifier(objective="multi:softprob", num_class=10,
                         n_estimators=300, max_depth=6, learning_rate=0.1,
                         tree_method="hist", random_state=seed, n_jobs=-1)


def fit_eval(model, Xs, ys, seed, tag, eval_test=True):
    w = compute_sample_weight("balanced", ys["train"])
    t0 = time.perf_counter()
    model.fit(Xs["train"], ys["train"], sample_weight=w)
    fit_s = time.perf_counter() - t0
    pred = model.predict(Xs["valid"])
    pred_test = model.predict(Xs["test"]) if eval_test else None
    if eval_test:
        t0 = time.perf_counter()
        pred_test = model.predict(Xs["test"])
        infer_s = time.perf_counter() - t0
    size_mb = len(pickle.dumps(model)) / 1e6
    row = {
        "tag": tag, "seed": seed, "n_features": Xs["train"].shape[1],
        "valid_macro_f1": round(float(f1_score(ys["valid"], pred, average="macro")), 4),
        "test_macro_f1": round(float(f1_score(ys["test"], pred_test, average="macro")), 4)
                         if eval_test else None,
        "test_balanced_acc": round(float(balanced_accuracy_score(ys["test"], pred_test)), 4)
                             if eval_test else None,
        "test_accuracy": round(float(accuracy_score(ys["test"], pred_test)), 4)
                         if eval_test else None,
        "fit_s": round(fit_s, 1),
        "infer_test_s": round(infer_s, 3) if eval_test else None,
        "model_only_mb": round(size_mb, 2),
    }
    return row, pred_test


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    Xs, ys = {}, {}
    for split in ("train", "valid", "test"):
        df = pd.read_parquet(PROC / f"{split}.parquet")
        Xs[split] = df.drop(columns=["attack_cat", "label"])
        ys[split] = df["attack_cat"]
    classes = sorted(ys["train"].unique())
    code = {c: i for i, c in enumerate(classes)}
    ys_enc = {k: v.map(code).astype(int) for k, v in ys.items()}
    n_full = Xs["train"].shape[1]

    # ---- 特征排序（仅训练划分，seed 42 单次拟合——局限见 docstring）----
    rank_model = make_cw_xgb(SWEEP_SEED)
    w = compute_sample_weight("balanced", ys_enc["train"])
    rank_model.fit(Xs["train"], ys_enc["train"], sample_weight=w)
    imp = pd.Series(rank_model.feature_importances_, index=Xs["train"].columns)
    ranking = imp.sort_values(ascending=False).index.tolist()
    imp.sort_values(ascending=False).to_csv(OUT / "feature_importance.csv",
                                            encoding="utf-8-sig")

    # ---- K 扫描（seed 42，仅验证集评估——测试集不进入扫描阶段）----
    sweep_rows = []
    for k in K_LIST:
        feats = ranking[:k]
        row, _ = fit_eval(make_cw_xgb(SWEEP_SEED),
                          {"train": Xs["train"][feats], "valid": Xs["valid"][feats],
                           "test": Xs["test"][feats]},
                          ys_enc, SWEEP_SEED, f"top{k}", eval_test=False)
        sweep_rows.append(row)
        print(f"[sweep] K={k}: valid mF1={row['valid_macro_f1']} "
              f"size={row['model_only_mb']}MB", flush=True)
    sweep = pd.DataFrame(sweep_rows)
    sweep.to_csv(OUT / "sweep.csv", index=False, encoding="utf-8-sig")

    best = sweep.sort_values(["valid_macro_f1", "n_features"],
                             ascending=[False, True]).iloc[0]
    k_star = int(best["n_features"])
    feats_star = ranking[:k_star]
    print(f"[select] K* = {k_star}（验证集 Macro-F1 {best['valid_macro_f1']}，并列取更小 K）")

    # ---- 终评：K* 与全量各 3 种子（测试集只在终评使用）----
    final_rows = []
    recalls = {}
    for tag, feats in [(f"top{k_star}", feats_star), (f"full{n_full}", None)]:
        for seed in SEEDS:
            sub = {s: (Xs[s][feats] if feats is not None else Xs[s]) for s in Xs}
            row, pred = fit_eval(make_cw_xgb(seed), sub, ys_enc, seed, tag)
            final_rows.append(row)
            for cls, r in zip(classes, recall_score(ys_enc["test"], pred,
                                                    average=None,
                                                    labels=range(len(classes)),
                                                    zero_division=0)):
                recalls.setdefault(f"{tag}|{cls}", []).append(round(float(r), 4))
            print(f"[final] {tag} seed{seed}: test mF1={row['test_macro_f1']} "
                  f"size={row['model_only_mb']}MB fit={row['fit_s']}s", flush=True)
    final = pd.DataFrame(final_rows)
    final.to_csv(OUT / "final_metrics.csv", index=False, encoding="utf-8-sig")
    rec_df = pd.DataFrame({k: pd.Series(v) for k, v in recalls.items()})
    rec_summary = rec_df.apply(lambda c: f"{c.mean():.3f}±{c.std():.3f}")
    (OUT / "recall_summary.csv").write_text(
        rec_summary.to_csv(header=["recall_mean_std"]), encoding="utf-8-sig")

    agg = final.groupby("tag").agg(
        macro_f1_mean=("test_macro_f1", "mean"), macro_f1_std=("test_macro_f1", "std"),
        bal_acc_mean=("test_balanced_acc", "mean"),
        fit_s_mean=("fit_s", "mean"), size_mb_mean=("model_only_mb", "mean"),
    ).round(4)
    speedup = round(float(agg.loc[f"full{n_full}", "fit_s_mean"] /
                          max(agg.loc[f"top{k_star}", "fit_s_mean"], 1e-9)), 2)
    size_cut = round(float(1 - agg.loc[f"top{k_star}", "size_mb_mean"] /
                           agg.loc[f"full{n_full}", "size_mb_mean"]) * 100, 1)
    if size_cut <= 0:
        size_note = (f"模型体积不降反增 {-size_cut}%——XGBoost 体积由树结构主导，"
                     "特征筛选不减小其体积（负结果，如实报告）")
    else:
        size_note = f"模型体积缩减 ≈ {size_cut}%"

    delta_rows = []
    for cls in classes:
        t = float(np.mean(recalls[f"top{k_star}|{cls}"]))
        f_ = float(np.mean(recalls[f"full{n_full}|{cls}"]))
        delta_rows.append((cls, round(t, 3), round(f_, 3), round(t - f_, 3)))
    delta_df = (pd.DataFrame(delta_rows, columns=["class", "topK_recall", "full_recall",
                                                  "delta"])
                .sort_values("delta", ascending=False))

    lines = ["# 第 5 周轻量化报告（类别权重 XGBoost + 特征筛选）", "",
             f"- 协议：增益重要性排序（训练划分、seed {SWEEP_SEED} 单次拟合——排序稳定性"
             "未做多种子检验，列入局限）；验证集选 K（并列取更小）；测试集仅终评",
             f"- K 扫描：{K_LIST}；**选型 K* = {k_star}**"
             f"（验证 Macro-F1 {best['valid_macro_f1']}）",
             "", "## K 扫描（seed 42，验证集）", "", "```",
             sweep[["tag", "valid_macro_f1", "test_macro_f1", "fit_s",
                    "model_only_mb"]].to_string(index=False), "```", "",
             "## 终评（测试集，3 种子均值±标准差）", "", "```",
             agg.to_string(), "```", "",
             f"- 训练加速比（全量/精简）≈ **{speedup}×**；{size_note}",
             f"- Balanced Accuracy：top{k_star} {agg.loc[f'top{k_star}', 'bal_acc_mean']} "
             f"对全量 {agg.loc[f'full{n_full}', 'bal_acc_mean']}",
             f"- 每类 Recall 变化（top{k_star} 对全量，均值，按增量排序）：", "```",
             delta_df.to_string(index=False), "```", "",
             "- 结论限定：以上比较在所测协议内成立（单一数据集、one-hot 编码、"
             "固定超参、单次特征排序）；体积为纯模型 pickle 口径。", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- 权衡图 ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    sw = sweep.sort_values("n_features", ascending=False)
    axes[0].plot(sw.n_features, sw.valid_macro_f1, "o-", label="验证集（选 K 用）",
                 color="#4878a8")
    ax0_test = agg.loc[[f"full{n_full}", f"top{k_star}"], "macro_f1_mean"]
    axes[0].plot([n_full, k_star], ax0_test.values, "s--", color="#d97f4a",
                 label="测试集（仅终评两点）")
    axes[0].axvline(k_star, color="gray", ls=":", label=f"K*={k_star}")
    axes[0].set_xscale("log", base=2)
    axes[0].set_xlabel("特征数 K")
    axes[0].set_ylabel("Macro-F1")
    axes[0].set_title("性能-特征数")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].plot(sw.n_features, sw.model_only_mb, "o-", color="#6aa179")
    axes[1].set_xscale("log", base=2)
    axes[1].set_xlabel("特征数 K")
    axes[1].set_ylabel("纯模型体积 (MB)")
    axes[1].set_title("体积-特征数")
    axes[1].grid(alpha=0.3)
    axes[2].plot(sw.n_features, sw.fit_s, "o-", color="#a678b8")
    axes[2].set_xscale("log", base=2)
    axes[2].set_xlabel("特征数 K")
    axes[2].set_ylabel("训练耗时 (s)")
    axes[2].set_title("训练耗时-特征数")
    axes[2].grid(alpha=0.3)
    fig.suptitle(f"轻量化权衡：类别权重 XGBoost 特征筛选（K*={k_star}, "
                 f"加速 {speedup}×, 体积 -{size_cut}%）")
    fig.tight_layout()
    fig.savefig(FIGS / "lightweight_tradeoff.png", dpi=200)
    plt.close(fig)

    print(f"[OK] K* = {k_star}, 加速 {speedup}x, 体积 -{size_cut}%")
    print(f"[OK] -> {OUT}")
    print(f"[OK] 图 -> figures/lightweight_tradeoff.png")


def run_v2():
    """v2 方差补测：per-seed 重切 + 逐种子重排序，K* 从 v1 封板产物读取。"""
    import resplit  # noqa: 与本脚本同目录

    out_dir = ROOT / "runs/lightweight_v2"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- K* 从 v1 封板产物按同一规则读取（选型决策仍只做一次）----
    v1_sweep_path = OUT / "sweep.csv"
    if v1_sweep_path.exists():
        v1_sweep = pd.read_csv(v1_sweep_path)
        k_star = int(v1_sweep.sort_values(["valid_macro_f1", "n_features"],
                                          ascending=[False, True]).iloc[0]["n_features"])
        k_source = f"v1 sweep.csv（runs/lightweight/sweep.csv，验证集选型封板决策）"
    else:
        k_star, k_source = 32, "v1 sweep.csv 缺失，回退到 v1 报告值 32（需人工核对）"

    final_rows, recalls, rankings, top_sets = [], {}, {}, {}
    classes = None
    for seed in SEEDS:
        splits = resplit.make_splits(seed)
        Xs = {k: splits[k].drop(columns=["attack_cat", "label"]) for k in splits}
        ys_raw = {k: splits[k]["attack_cat"] for k in splits}
        if classes is None:
            classes = sorted(ys_raw["train"].unique())
        ys_enc = {k: v.map(classes.index).astype(int) for k, v in ys_raw.items()}

        # ---- 逐种子特征排序（排序模型仅 fit 该种子训练划分）----
        rank_model = make_cw_xgb(seed)
        w = compute_sample_weight("balanced", ys_enc["train"])
        rank_model.fit(Xs["train"], ys_enc["train"], sample_weight=w)
        ranking = pd.Series(rank_model.feature_importances_,
                            index=Xs["train"].columns).sort_values(ascending=False)
        ranking.to_csv(out_dir / f"feature_importance_seed{seed}.csv", encoding="utf-8-sig")
        rankings[seed] = ranking
        top_sets[seed] = set(ranking.index[:k_star])

        # ---- 终评：full 与 topK*（该种子排序）各评一次 ----
        for tag, feats in [(f"top{k_star}", list(ranking.index[:k_star])), (f"full{n_full_v2(Xs)}", None)]:
            sub = {s: (Xs[s][feats] if feats is not None else Xs[s]) for s in Xs}
            row, pred = fit_eval(make_cw_xgb(seed), sub, ys_enc, seed, tag)
            row["split_seed"] = seed
            final_rows.append(row)
            for cls, r in zip(classes, recall_score(ys_enc["test"], pred, average=None,
                                                    labels=range(len(classes)),
                                                    zero_division=0)):
                recalls.setdefault(f"{tag}|{cls}", []).append(round(float(r), 4))
            print(f"[v2 final] {tag} seed{seed}: test mF1={row['test_macro_f1']}", flush=True)

    final = pd.DataFrame(final_rows)
    final.to_csv(out_dir / "final_metrics_v2.csv", index=False, encoding="utf-8-sig")

    # ---- 逐种子×逐类 Recall 明细落盘（可审计性：报告中的 mean±std 必须可回溯）----
    rec_rows = []
    for key, vals in recalls.items():
        tag, cls = key.split("|")
        for i, v in enumerate(vals):
            rec_rows.append({"tag": tag, "split_seed": SEEDS[i], "class": cls,
                             "recall": v})
    pd.DataFrame(rec_rows).to_csv(out_dir / "recall_per_class_per_seed_v2.csv",
                                  index=False, encoding="utf-8-sig")

    # ---- 排序稳定性：各种子 top-K 重合度（对 v1 排序与两两之间）----
    v1_imp_path = OUT / "feature_importance.csv"
    overlap_rows = []
    if v1_imp_path.exists():
        v1_top = set(pd.read_csv(v1_imp_path, index_col=0).index[:k_star])
        for seed in SEEDS:
            inter = len(top_sets[seed] & v1_top)
            union = len(top_sets[seed] | v1_top)
            overlap_rows.append({"comparison": f"seed{seed}_vs_v1",
                                 "n_overlap": inter, "jaccard": round(inter / union, 3)})
    for i, s1 in enumerate(SEEDS):
        for s2 in SEEDS[i + 1:]:
            inter = len(top_sets[s1] & top_sets[s2])
            union = len(top_sets[s1] | top_sets[s2])
            overlap_rows.append({"comparison": f"seed{s1}_vs_seed{s2}",
                                 "n_overlap": inter, "jaccard": round(inter / union, 3)})
    overlap = pd.DataFrame(overlap_rows)
    overlap.to_csv(out_dir / "ranking_overlap.csv", index=False, encoding="utf-8-sig")

    agg = final.groupby("tag").agg(
        macro_f1_mean=("test_macro_f1", "mean"), macro_f1_std=("test_macro_f1", "std"),
        bal_acc_mean=("test_balanced_acc", "mean"), bal_acc_std=("test_balanced_acc", "std"),
        fit_s_mean=("fit_s", "mean"), size_mb_mean=("model_only_mb", "mean"),
    ).round(4)

    full_tag = [t for t in agg.index if t.startswith("full")][0]
    top_tag = [t for t in agg.index if t.startswith("top")][0]
    speedup = round(float(agg.loc[full_tag, "fit_s_mean"] /
                          max(agg.loc[top_tag, "fit_s_mean"], 1e-9)), 2)

    delta_rows = []
    for cls in classes:
        t = np.array(recalls[f"{top_tag}|{cls}"])
        f_ = np.array(recalls[f"{full_tag}|{cls}"])
        d = t - f_
        delta_rows.append((cls, round(float(t.mean()), 3), round(float(f_.mean()), 3),
                           round(float(d.mean()), 3), round(float(np.std(d, ddof=1)), 3)))
    delta_df = (pd.DataFrame(delta_rows, columns=["class", "topK_recall", "full_recall",
                                                  "delta_mean", "delta_std"])
                .sort_values("delta_mean", ascending=False))

    lines = ["# 轻量化方差补测 v2（第 8 周，红队三轮 A1-2/A1-3）", "",
             "- 协议 v2：resplit.make_splits(seed) 每种子重切官方训练池（编码器/标准化器"
             "逐种子仅 fit 训练划分，官方测试集冻结只 transform）；特征排序逐种子重做"
             "（排序模型 fit 各自训练划分）；K* 不重新选型——",
             f"  K* = {k_star}（来源：{k_source}）。",
             "- v1 已披露局限「单次特征排序（seed 42）未做稳定性检验」由排名重合度直接检验：",
             "", "## 终评（测试集，3 种子均值±标准差，真实切分+排序方差）", "", "```",
             agg.to_string(), "```", "",
             f"- 训练加速比（全量/精简）≈ **{speedup}×**（v1 为 2.52×，口径：per-seed 重切后重训；"
             "fit 时间为 wall-clock，批间有约 2% 波动，指标本身为确定性可逐位复现）",
             "", "## 每类 Recall 增量（topK* − 全量，均值±标准差[ddof=1]，按增量排序）", "", "```",
             delta_df.to_string(index=False), "```", "",
             "## 特征排序重合度（top-K 集合 Jaccard）", "", "```",
             overlap.to_string(index=False), "```", "",
             "- 结论限定：v2 方差含「切分敏感性 + 排序敏感性」两个来源，与 v1 的确定性"
             "口径（std=0）不可直接混读；v1 封板产物与结论保持原样，v2 为其方差注脚。",
             "- 体积负结果（不降反增）在 v2 下逐种子复核见 final_metrics_v2.csv。", ""]
    (ROOT / "reports/week5/variance_recheck.md").write_text("\n".join(lines), encoding="utf-8")
    print(agg.to_string())
    print(f"\n[OK v2] -> {out_dir} 与 reports/week5/variance_recheck.md")


def n_full_v2(Xs):
    return Xs["train"].shape[1]


if __name__ == "__main__":
    if "--v2" in sys.argv:
        run_v2()
    else:
        main()
