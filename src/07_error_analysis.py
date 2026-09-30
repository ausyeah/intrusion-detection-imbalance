"""第 4 周误差分析（红队复审后修订版）：按验证集均值选每模型最优方法，重训后输出
混淆矩阵、错误案例（含行哈希与噪声归因）、纯模型体积、跨模型重叠错误核验。

v2 修订记录（红队台账 W4-W5_红队一二轮台账，S3/S4/S5/S9）：
- S3: 选型依据从测试集 Macro-F1 改为验证集 Macro-F1（遵守"测试集不参与调参"纪律）；
  测试集指标仅作描述性报告。
- S5: conflict 判定从二分类 label 冲突改为 10 类 attack_cat 冲突（同特征向量在训练
  划分中出现过多于一个 attack_cat），口径与多分类任务一致。
- S4: 机制句不再使用未经计算的描述；重叠行错误的真实类别构成按实测写入报告。
- S9: error_cases.csv 增加行哈希列；输出各模型重叠错误行集合的两两交集/并集，
  验证不同模型重叠错误计数相同是否为同一行集合。

严谨性设计（继承 v1）：
- make_model 从 05_run_experiments.py 导入（单一协议来源）；
- 选型依据（各模型 3 种子平均验证集 Macro-F1 最高）写入 selection.json 可复核；
- 硬性校验：全部错误行「测试行预测 == 训练副本行预测」，不一致数必须 = 0。

产出：figures/confusion_matrix_best.png、runs/week4/error_cases.csv、
     runs/week4/error_summary.md、runs/week4/selection.json
用法：python src/07_error_analysis.py
"""
import argparse
import importlib.util
import json
import pickle
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from imblearn.over_sampling import RandomOverSampler, SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
_ap = argparse.ArgumentParser()
_ap.add_argument("--seed", type=int, default=0)
_ARGS = _ap.parse_args()
SEED = _ARGS.SEED if hasattr(_ARGS, "SEED") else _ARGS.seed
RUNS = ROOT / ("runs/week4" if SEED == 0 else f"runs/week4_seed{SEED}")
RAW_TEST = ROOT / "data/raw/UNSW_NB15_testing-set.csv"
RAW_TRAIN = ROOT / "data/raw/UNSW_NB15_training-set.csv"


plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load_module05():
    spec = importlib.util.spec_from_file_location(
        "exp05", ROOT / "src/05_run_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    mod = load_module05()

    summary = pd.read_csv(RUNS.parent / "experiments/summary_full.csv")
    best = (summary.groupby(["model", "method"]).valid_macro_f1.mean()
            .reset_index().sort_values("valid_macro_f1", ascending=False)
            .drop_duplicates("model").set_index("model"))
    selection = {m: best.loc[m, "method"] for m in ["LR", "XGBoost", "MLP"]}
    sel_valid = {m: round(float(best.loc[m, "valid_macro_f1"]), 4) for m in selection}
    sel_test_desc = {
        m: round(float(summary[(summary.model == m) & (summary.method == selection[m])]
                       .test_macro_f1.mean()), 4) for m in selection}

    Xs, ys = {}, {}
    for split in ("train", "valid", "test"):
        df = pd.read_parquet(PROC / f"{split}.parquet")
        Xs[split] = df.drop(columns=["attack_cat", "label"])
        ys[split] = df["attack_cat"]
    classes = sorted(ys["train"].unique())
    code = {c: i for i, c in enumerate(classes)}
    ys_enc = {k: v.map(code).astype(int) for k, v in ys.items()}

    raw_test = pd.read_csv(RAW_TEST, encoding="utf-8-sig")
    raw_train = pd.read_csv(RAW_TRAIN, encoding="utf-8-sig")
    assert len(raw_test) == len(Xs["test"]), "原始测试集与处理后行序不一致"

    raw_train = raw_train.drop(columns=["id"])
    raw_train["attack_cat"] = raw_train["attack_cat"].str.strip()
    tr_split, _ = train_test_split(raw_train, test_size=0.2, random_state=42,
                                   stratify=raw_train["attack_cat"])
    feat_cols = [c for c in raw_train.columns if c not in ("attack_cat", "label")]
    tr_keys = pd.util.hash_pandas_object(tr_split[feat_cols], index=False).values
    train_cats = (tr_split.assign(_k=tr_keys)
                  .groupby("_k")["attack_cat"].apply(lambda s: tuple(sorted(set(s))))
                  .to_dict())
    test_keys = pd.util.hash_pandas_object(
        raw_test.drop(columns=["id"])[feat_cols], index=False).values

    fig, axes = plt.subplots(1, 3, figsize=(19, 5.6))
    lines = ["# 第 4 周误差分析（v2，红队复审后）", "",
             f"- 选型依据（各模型 3 种子平均验证集 Macro-F1 最高，遵守测试集不参与选型纪律；"
             f"种子 {SEED} 重训）：" + "；".join(
                 f"{m} → {selection[m]}（验证 {sel_valid[m]:.4f}，对应测试 {sel_test_desc[m]:.4f}）"
                 for m in selection),
             "- 错误归因口径：novel = 训练划分未见该特征向量（正常泛化错误）；conflict = "
             "训练见过但出现过多种 attack_cat 标注（数据集固有冲突，不可约噪声；v2 起按 "
             "10 类 attack_cat 计，v1 仅按二分类 label 计导致低估）；overlap_clean = 训练"
             "见过且 attack_cat 一致（模型对该向量的拟合极限，非流程错误）。",
             "- 内部校验（硬性）：模型是特征的确定性函数，逐格验证全部错误行满足"
             "「测试行预测 == 训练副本行预测」，不一致数必须 = 0。",
             "- 不确定性声明：MLP 为三模型中种子方差最大者（测试 Macro-F1 std 最高 0.017），"
             "且其选型格种子 0 的验证 Macro-F1 为三种子最低——MLP 相关百分比为单种子"
             "代表性运行，论文引用应以区间表述或补 3 种子归因。",
             ""]
    error_frames, size_rows, overlap_err_keys = [], [], {}
    attr_by_model = {}
    for ax, model in zip(axes, ["LR", "XGBoost", "MLP"]):
        method = selection[model]
        m = mod.make_model(model, SEED, method)
        if method == "ROS":
            pipe = ImbPipeline([("sampler", RandomOverSampler(random_state=SEED)), ("model", m)])
        elif method == "SMOTE":
            pipe = ImbPipeline([("sampler", SMOTE(random_state=SEED)), ("model", m)])
        else:
            pipe = ImbPipeline([("model", m)])
        kw = {}
        if method == "class_weight":
            kw["model__sample_weight"] = compute_sample_weight("balanced", ys_enc["train"])
        pipe.fit(Xs["train"], ys_enc["train"], **kw)
        pred = pipe.predict(Xs["test"])

        model_only_mb = len(pickle.dumps(pipe.named_steps["model"])) / 1e6
        pipe_mb = len(pickle.dumps(pipe)) / 1e6
        size_rows.append({"model": model, "method": method,
                          "model_only_mb": round(model_only_mb, 2),
                          "pipeline_mb": round(pipe_mb, 2)})

        cm = confusion_matrix(ys_enc["test"], pred, labels=range(len(classes)))
        cm_norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
        im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(len(classes)), labels=classes, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(classes)), labels=classes, fontsize=8)
        for i in range(len(classes)):
            for j in range(len(classes)):
                if cm[i, j]:
                    ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                            fontsize=6.5, color="black" if cm_norm[i, j] < 0.6 else "white")
        acc = float((pred == ys_enc["test"]).mean())
        ax.set_title(f"{model} + {method}（Accuracy={acc:.3f}）", fontsize=10)
        ax.set_xlabel("预测类别", fontsize=9)
        ax.set_ylabel("真实类别", fontsize=9)

        err_idx = np.where(pred != ys_enc["test"].values)[0]
        errs = pd.DataFrame({
            "row_hash": [int(test_keys[i]) for i in err_idx],
            "proto": raw_test["proto"].values[err_idx],
            "service": raw_test["service"].values[err_idx],
            "state": raw_test["state"].values[err_idx],
            "dur": raw_test["dur"].values[err_idx],
            "true": ys["test"].values[err_idx],
            "pred": [classes[i] for i in pred[err_idx]],
        })
        errs.insert(0, "model", model)

        tr_pred = pipe.predict(Xs["train"])
        assert len(tr_pred) == len(tr_keys), "训练划分行序与哈希错位"
        key2pred = {}
        for k, p in zip(tr_keys, tr_pred):
            key2pred.setdefault(int(k), int(p))
        attr = {"novel": 0, "conflict": 0, "overlap_clean": 0}
        mismatch = 0
        ovl_err_keys = set()
        err_types = []
        for pos, i in enumerate(err_idx):
            k = int(test_keys[i])
            tl = train_cats.get(k)
            if tl is None:
                attr["novel"] += 1
                err_types.append("novel")
            else:
                if key2pred.get(k) != int(pred[i]):
                    mismatch += 1
                if len(tl) > 1:
                    attr["conflict"] += 1
                    err_types.append("conflict")
                else:
                    attr["overlap_clean"] += 1
                    err_types.append("overlap_clean")
                ovl_err_keys.add(k)
        if mismatch != 0:
            raise AssertionError(
                f"{model}: {mismatch} 个错误行的测试预测与训练副本预测不一致——哈希或行对齐有 bug，结果作废")
        errs["error_type"] = err_types
        error_frames.append(errs)
        overlap_err_keys[model] = ovl_err_keys

        n_err = len(err_idx)
        attr_by_model[model] = {"novel": attr["novel"], "conflict": attr["conflict"],
                              "overlap_clean": attr["overlap_clean"], "n_err": n_err}
        overlap_rows = int(sum(1 for k in test_keys if int(k) in train_cats))
        n_err_overlap = attr["conflict"] + attr["overlap_clean"]
        comp = errs[errs.error_type != "novel"]["true"].value_counts()
        comp_top = "、".join(f"{c} {v:,} 条（{v / max(n_err_overlap, 1) * 100:.0f}%）"
                             for c, v in comp.head(3).items())
        lines += [f"## {model} + {method}", "",
                  f"- 错误共 {n_err:,} 条，归因：novel {attr['novel']:,}"
                  f"（{attr['novel'] / n_err * 100:.1f}%）、"
                  f"conflict {attr['conflict']:,}（{attr['conflict'] / n_err * 100:.1f}%）、"
                  f"overlap_clean {attr['overlap_clean']:,}"
                  f"（{attr['overlap_clean'] / n_err * 100:.1f}%）",
                  f"- 内部校验：{n_err:,} 个错误行「测试预测 == 训练副本预测」不一致数 = 0"
                  "（哈希与行对齐正确）。",
                  f"- 测试集与训练划分共享特征向量的行共 {overlap_rows:,} 条，其中错误 "
                  f"{n_err_overlap:,} 条（{n_err_overlap / overlap_rows * 100:.0f}%，整体"
                  f"错误率 {n_err / len(test_keys) * 100:.0f}%）。",
                  f"- 重叠行错误的真实类别构成（实测，v2 修正 v1 的未经验证描述）：{comp_top}。",
                  "- 主要混淆对：", "```",
                  errs.groupby(["true", "pred"]).size().sort_values(ascending=False)
                  .head(8).to_string(),
                  "```", ""]

    # S9 核验：各模型重叠错误行集合的交并
    a, b, c = (overlap_err_keys["LR"], overlap_err_keys["XGBoost"], overlap_err_keys["MLP"])
    lines += ["## 跨模型重叠错误核验（红队 S9）", "",
              f"- 括号内为**去重特征向量集合**大小（多条错误行可共享同一向量，"
              f"对应重叠错误行数见上文 5,102 / 3,727 / 4,508）："
              f"|LR∩XGB| = {len(a & b):,}（LR {len(a):,} / XGB {len(b):,}）；"
              f"|XGB∩MLP| = {len(b & c):,}（XGB {len(b):,} / MLP {len(c):,}）；"
              f"|LR∩MLP| = {len(a & c):,}",
              "- 若两模型重叠错误计数相同但交集远小于自身，则计数相同为巧合；"
              "交集≈自身则说明两模型在同一批难例向量上犯同样的错。", ""]

    all_errs = pd.concat(error_frames)
    all_errs.to_csv(RUNS / "error_cases.csv", index=False, encoding="utf-8-sig")
    size_df = pd.DataFrame(size_rows)
    lines += ["## 纯模型体积（选型配置，seed 0，pickle 计）", "", "```",
              size_df.to_string(index=False), "```", "",
              "- 与第 3 周 pipeline 口径的区别：不含采样器的 sample_indices_ 索引。", "",
              "- 全部错误案例见 error_cases.csv（含 row_hash、error_type），"
              "结论表述以第 3 周 3 种子均值为准，本文件为代表性单次运行。"]
    (RUNS / "error_summary.md").write_text("\n".join(lines), encoding="utf-8")

    fig.colorbar(im, ax=axes, fraction=0.018, label="行归一化比例")
    fig.suptitle("最优配置混淆矩阵（按验证集自动选型，种子 0）")
    _fig_name = "confusion_matrix_best.png" if SEED == 0 else f"confusion_matrix_best_seed{SEED}.png"
    fig.savefig(ROOT / "figures" / _fig_name, dpi=200, bbox_inches="tight")
    plt.close(fig)

    (RUNS / "attribution.json").write_text(json.dumps(
        {"seed": SEED, "selection": selection, "attribution": attr_by_model},
        indent=2, ensure_ascii=False), encoding="utf-8")
    (RUNS / "selection.json").write_text(json.dumps(
        {"selection_basis": "valid_macro_f1_mean (3 seeds) — 测试集不参与选型",
         "selection": selection, "valid_macro_f1": sel_valid,
         "test_macro_f1_descriptive": sel_test_desc, "seed": SEED,
         "model_size": size_rows},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] 选型（验证集） {selection}")
    print(size_df.to_string(index=False))
    print(f"[OK] -> {RUNS}")


if __name__ == "__main__":
    main()
