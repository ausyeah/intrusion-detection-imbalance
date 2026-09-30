"""第 6 周 D 项：不平衡比例敏感性衰减曲线（预注册于本 docstring）。

协议：
- 基础配置：XGBoost，none 与 class_weight 两种处理（第 3 周同参），seeds [0,1,2]。
- 操纵：训练划分内，对非 Normal 类按比例 p ∈ {1.0, 0.5, 0.25, 0.1} 随机降采样
  （seed=比例索引+0，固定可复现）；Normal 保持 44,800 不动 → 不平衡度随 p 递减而加剧。
  valid/test 不做任何操纵。p=1.0 等价于第 3 周 none/cw 格子（应复现其数值）。
- 指标：测试集 Macro-F1 与少数类宏 Recall（Analysis/Backdoor/Shellcode/Worms）。
- 判定（冻结）：若 p=0.25 时两方法的 Macro-F1 相对 p=1.0 的降幅均 < 0.02，则称
  「结论对训练不平衡度扰动稳健」；否则报告衰减曲线并给出敏感的区间。

产出：runs/imbalance_decay/decay_results.csv、reports/week6/imbalance_decay.md、
     figures/imbalance_decay.png
用法：python src/13_imbalance_decay.py

--v2 方差补测（第 8 周，红队三轮 A1-3 + T14 用户决策；v1 行为与产物不变）：
- 数据：resplit.make_splits(seed) 每种子重切官方训练池（80/20 分层），编码器与
  标准化器逐种子仅 fit 各自训练划分；官方测试集冻结只 transform（先划分后拟合）。
- 降采样随机数随种子变化：RandomState(100 + 1000*seed + 比例索引)——v1 的
  RandomState(100+比例索引) 不随 seed 变化是 A1-3 指出的确定性坍缩根因之一。
- 新增 SMOTE 配置（T14）：降采样后 SMOTE 重采样（k_neighbors 取
  configs/experiment_hyperparams.yaml；若某少数类样本数 <= k，回退 k=min(类样本数)-1
  并在 CSV 记录 smote_k_used 披露；类样本数 < 2 则该格 FAILED 留痕不静默）。
- p=1.0 不再预期精确复现第 3 周格子（切分本身随种子变化）——这正是补测目的。
- 判定标准沿用预注册阈值（p=0.25 时 Macro-F1 降幅 <0.02），但以真实 std 呈现，
  且少数类宏 Recall 衰减一并入判定表述（红队三轮 A1-1：v1 仅 Macro-F1 口径）。
- 产出：runs/imbalance_decay_v2/、reports/week6/imbalance_decay_v2.md、
       figures/imbalance_decay_v2.png；v1 目录不写。
"""
import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from imblearn.over_sampling import SMOTE
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
OUT = ROOT / "runs/imbalance_decay"
REPORT = ROOT / "reports/week6"
FIGS = ROOT / "figures"
SEEDS = [0, 1, 2]
PROPORTIONS = [1.0, 0.5, 0.25, 0.1]
MINORITY = ["Analysis", "Backdoor", "Shellcode", "Worms"]
HP = yaml.safe_load((ROOT / "configs/experiment_hyperparams.yaml").read_text(encoding="utf-8"))

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "exp05", ROOT / "src/05_run_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    tr = pd.read_parquet(PROC / "train.parquet")
    te = pd.read_parquet(PROC / "test.parquet")
    va = pd.read_parquet(PROC / "valid.parquet")
    Xte, yte = te.drop(columns=["attack_cat", "label"]), te["attack_cat"]
    Xva, yva = va.drop(columns=["attack_cat", "label"]), va["attack_cat"]
    classes = sorted(tr["attack_cat"].unique())
    code = {c: i for i, c in enumerate(classes)}
    yte_c, yva_c = yte.map(code).astype(int), yva.map(code).astype(int)
    minority_idx = [code[c] for c in MINORITY]

    minority_mask = tr["attack_cat"] != "Normal"
    rows = []
    for prop in PROPORTIONS:
        for seed in SEEDS:
            rng = np.random.RandomState(100 + PROPORTIONS.index(prop))
            part = tr[~minority_mask]
            if prop < 1.0:
                keep = tr[minority_mask].groupby("attack_cat").sample(
                    frac=prop, random_state=int(rng.randint(1e9)))
                sub = pd.concat([part, keep])
            else:
                sub = tr
            Xs = sub.drop(columns=["attack_cat", "label"])
            ys = sub["attack_cat"].map(code).astype(int)
            for config in ("none", "class_weight"):
                model = mod.make_model("XGBoost", seed, config)
                kw = {}
                if config == "class_weight":
                    kw["sample_weight"] = compute_sample_weight("balanced", ys)
                model.fit(Xs, ys, **kw)
                pred = model.predict(Xte)
                rows.append({
                    "proportion": prop, "seed": seed, "config": config,
                    "n_train": len(Xs),
                    "test_macro_f1": round(float(f1_score(yte_c, pred, average="macro")), 4),
                    "test_balanced_acc": round(float(balanced_accuracy_score(yte_c, pred)), 4),
                    "minority_recall": round(float(np.mean(recall_score(
                        yte_c, pred, average=None, labels=range(len(classes)),
                        zero_division=0)[minority_idx])), 4),
                })
        print(f"[done] proportion={prop}", flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "decay_results.csv", index=False, encoding="utf-8-sig")
    agg = res.groupby(["config", "proportion"])[
        ["test_macro_f1", "minority_recall"]].mean().round(4).reset_index()

    drop = {}
    for config in ("none", "class_weight"):
        f1_full = agg[(agg.config == config) & (agg.proportion == 1.0)].test_macro_f1.iloc[0]
        f1_quarter = agg[(agg.config == config) & (agg.proportion == 0.25)].test_macro_f1.iloc[0]
        drop[config] = round(f1_full - f1_quarter, 4)
    robust = all(v < 0.02 for v in drop.values())
    verdict = ("两方法在 p=0.25 时 Macro-F1 降幅均 < 0.02——结论对训练不平衡度扰动稳健"
               if robust else
               f"结论随训练不平衡度明显衰减（none 降 {drop['none']}，cw 降 {drop['class_weight']}），"
               "按预注册标准不判稳健，报告衰减区间")

    lines = ["# 不平衡比例敏感性衰减（预注册判定）", "",
             "- 协议：训练划分非 Normal 类降采样至 p ∈ {1.0, 0.5, 0.25, 0.1}（Normal 不动），"
             "XGBoost none/类别权重，3 种子；valid/test 不操纵；p=1.0 复现第 3 周对应格子。",
             f"- 预注册判定：{verdict}", "",
             "## 均值表（3 种子）", "", "```", agg.to_string(index=False), "```", "",
             f"- p=1.0→0.25 的 Macro-F1 降幅：none {drop['none']}，类别权重 {drop['class_weight']}。",
             "- 少数类宏 Recall 的衰减见 decay_results.csv 与下图。", ""]
    (REPORT / "imbalance_decay.md").write_text("\n".join(lines), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharex=True)
    for ax, col, title in [(axes[0], "test_macro_f1", "测试 Macro-F1"),
                           (axes[1], "minority_recall", "少数类宏 Recall")]:
        for config, color in [("none", "#4878a8"), ("class_weight", "#d97f4a")]:
            sub = agg[agg.config == config].sort_values("proportion")
            ax.plot(sub.proportion, sub[col], "o-", label=config, color=color)
        ax.set_xscale("log")
        ax.set_xticks(PROPORTIONS, [str(p_) for p_ in PROPORTIONS])
        ax.set_xlabel("少数类保留比例 p")
        ax.set_title(title)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("3 种子均值")
    axes[1].legend(fontsize=9)
    fig.suptitle("训练不平衡度敏感性衰减曲线（XGBoost，测试集）")
    fig.tight_layout()
    fig.savefig(FIGS / "imbalance_decay.png", dpi=200)
    plt.close(fig)
    print(agg.to_string(index=False))
    print(f"\n判定：{verdict}")
    print(f"[OK] -> {OUT} 与 {REPORT / 'imbalance_decay.md'}")


def run_v2():
    """v2 方差补测：per-seed 重切验证集 + 种子相关降采样 RNG + SMOTE 衰减（T14）。"""
    import resplit  # noqa: 与本脚本同目录

    out_dir = ROOT / "runs/imbalance_decay_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "exp05", ROOT / "src/05_run_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    smote_k_cfg = int(HP["SMOTE"]["k_neighbors"])

    classes, code, rows = None, None, []
    for seed in SEEDS:
        splits = resplit.make_splits(seed)
        tr_s = splits["train"]
        te_s = splits["test"]
        Xte = te_s.drop(columns=["attack_cat", "label"])
        if classes is None:
            classes = sorted(tr_s["attack_cat"].unique())
            code = {c: i for i, c in enumerate(classes)}
        yte_c = te_s["attack_cat"].map(code).astype(int)
        minority_idx = [code[c] for c in MINORITY]
        minority_mask = tr_s["attack_cat"] != "Normal"

        for prop in PROPORTIONS:
            rng = np.random.RandomState(100 + 1000 * seed + PROPORTIONS.index(prop))
            part = tr_s[~minority_mask]
            if prop < 1.0:
                keep = tr_s[minority_mask].groupby("attack_cat").sample(
                    frac=prop, random_state=int(rng.randint(1e9)))
                sub = pd.concat([part, keep])
            else:
                sub = tr_s
            Xs = sub.drop(columns=["attack_cat", "label"])
            ys = sub["attack_cat"].map(code).astype(int)

            for config in ("none", "class_weight", "smote"):
                rec = {"proportion": prop, "seed": seed, "config": config,
                       "n_train": len(Xs), "smote_k_used": None, "status": "ok"}
                try:
                    if config == "smote":
                        counts = pd.Series(ys).value_counts()
                        maj_n = int(counts.max())
                        min_min = int(counts[counts.index != counts.idxmax()].min())
                        k = smote_k_cfg
                        if min_min <= k:
                            k = max(1, min_min - 1)
                            rec["smote_k_used"] = k  # 回退披露
                        if min_min < 2:
                            raise ValueError(
                                f"SMOTE 不可行：最小少数类仅 {min_min} 个样本 (p={prop}, seed={seed})")
                        sampler = SMOTE(random_state=seed, k_neighbors=k)
                        Xr, yr = sampler.fit_resample(Xs, ys)
                        rec["n_train"] = len(Xr)
                        model = mod.make_model("XGBoost", seed, "none")
                        model.fit(Xr, yr)
                    else:
                        model = mod.make_model("XGBoost", seed, config)
                        kw = {}
                        if config == "class_weight":
                            kw["sample_weight"] = compute_sample_weight("balanced", ys)
                        model.fit(Xs, ys, **kw)
                    pred = model.predict(Xte)
                    rec.update({
                        "test_macro_f1": round(float(f1_score(yte_c, pred, average="macro")), 4),
                        "test_balanced_acc": round(float(balanced_accuracy_score(yte_c, pred)), 4),
                        "minority_recall": round(float(np.mean(recall_score(
                            yte_c, pred, average=None, labels=range(len(classes)),
                            zero_division=0)[minority_idx])), 4),
                    })
                except Exception as exc:  # 单格失败留痕不静默（05 同款约定）
                    rec["status"] = f"FAILED: {exc}"
                    print(f"[FAILED] p={prop} seed={seed} {config}: {exc}", flush=True)
                rows.append(rec)
        print(f"[done v2] seed={seed}", flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(out_dir / "decay_results_v2.csv", index=False, encoding="utf-8-sig")
    ok = res[res.status == "ok"]
    agg = ok.groupby(["config", "proportion"])[
        ["test_macro_f1", "minority_recall"]].agg(["mean", "std"]).round(4)

    # 预注册判定（阈值不变）+ 少数类衰减一并呈现（A1-1 修订要求）
    drop, quarter_std = {}, {}
    for config in ("none", "class_weight", "smote"):
        sub = ok[ok.config == config].groupby("proportion").test_macro_f1.agg(["mean", "std"])
        if 1.0 in sub.index and 0.25 in sub.index:
            drop[config] = round(float(sub.loc[1.0, "mean"] - sub.loc[0.25, "mean"]), 4)
            quarter_std[config] = round(float(sub.loc[0.25, "std"]), 4)
    core = {c: v for c, v in drop.items() if c in ("none", "class_weight")}
    robust = all(v < 0.02 for v in core.values())
    verdict = ("none/类别权重在 p=0.25 时 Macro-F1 均值降幅均 < 0.02——Macro-F1 口径判稳健"
               if robust else
               f"按预注册标准不判稳健（none 降 {core.get('none')}，cw 降 {core.get('class_weight')}），"
               "报告衰减区间")

    # v1 对照（直接读 v1 CSV，不手填）
    v1_note = ""
    v1_path = OUT / "decay_results.csv"
    if v1_path.exists():
        v1 = pd.read_csv(v1_path)
        v1_agg = v1.groupby(["config", "proportion"]).test_macro_f1.mean().round(4)
        v1_note = "\n".join(
            f"  - v1 固定切分: {c} p=1.0→0.25 Macro-F1 "
            f"{v1_agg.get((c, 1.0))}→{v1_agg.get((c, 0.25))}（降幅 {round(float(v1_agg.get((c, 1.0)) - v1_agg.get((c, 0.25))), 4)}）"
            for c in ("none", "class_weight"))

    minority_decay = ok.groupby(["config", "proportion"]).minority_recall.agg(
        ["mean", "std"]).round(4)

    lines = ["# 不平衡比例敏感性衰减 v2（方差补测，第 8 周）", "",
             "- 协议 v2（红队三轮 A1-3/T14 修复）：每种子重切官方训练池（80/20 分层，"
             "编码器/标准化器逐种子仅 fit 训练划分，官方测试集冻结只 transform）；降采样"
             "随机数随种子变化 RandomState(100+1000*seed+比例索引)；新增 SMOTE 配置（T14），"
             "SMOTE k 回退时逐格披露 smote_k_used。",
             f"- 预注册判定（阈值与 v1 相同）：{verdict}",
             "- p=1.0 不再精确复现第 3 周格子——切分本身随种子变化，这是补测目的。",
             "- v1 对照（runs/imbalance_decay/decay_results.csv，固定 seed 42 切分）：",
             v1_note or "  - （v1 CSV 缺失，未附）", "",
             "## 均值±标准差（3 种子，真实切分方差）", "", "```",
             agg.to_string(), "```", "",
             "## 少数类宏 Recall 衰减（均值±标准差）", "", "```",
             minority_decay.to_string(), "```", "",
             "- 判定表述限定（A1-1）：Macro-F1 稳健性结论仅覆盖上述口径；少数类宏 Recall "
             "衰减与 Macro-F1 衰减分别阅读，不得互相外推。",
             "- SMOTE 格若存在 smote_k_used 非空或 FAILED 行，见 decay_results_v2.csv 逐格披露。", ""]
    (REPORT / "imbalance_decay_v2.md").write_text("\n".join(lines), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.6), sharex=True)
    colors = {"none": "#4878a8", "class_weight": "#d97f4a", "smote": "#6aa179"}
    std_ok = ok.copy()
    for ax, col, title in [(axes[0], "test_macro_f1", "测试 Macro-F1（误差棒=3种子std）"),
                           (axes[1], "minority_recall", "少数类宏 Recall（误差棒=3种子std）")]:
        for config in ("none", "class_weight", "smote"):
            sub = (std_ok[std_ok.config == config].groupby("proportion")[col]
                   .agg(["mean", "std"]).reindex(PROPORTIONS))
            ax.errorbar(PROPORTIONS, sub["mean"], yerr=sub["std"].fillna(0), fmt="o-",
                        label=config, color=colors[config], capsize=3)
        ax.set_xscale("log")
        ax.set_xticks(PROPORTIONS, [str(p_) for p_ in PROPORTIONS])
        ax.set_xlabel("少数类保留比例 p")
        ax.set_title(title)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("3 种子均值")
    axes[1].legend(fontsize=9)
    fig.suptitle("训练不平衡度敏感性衰减曲线 v2（per-seed 重切验证集，真实方差）")
    fig.tight_layout()
    fig.savefig(FIGS / "imbalance_decay_v2.png", dpi=200)
    plt.close(fig)
    print(agg.to_string())
    print(f"\n判定：{verdict}")
    print(f"[OK v2] -> {out_dir} 与 {REPORT / 'imbalance_decay_v2.md'}")


if __name__ == "__main__":
    if "--v2" in sys.argv:
        run_v2()
    else:
        main()

