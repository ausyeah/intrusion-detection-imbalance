"""第 3 周汇总分析：读取 36 组实验的 metrics.json，产出稳定性表与对比图。

产出：
- runs/experiments/summary_full.csv        全部 run 的扁平表
- runs/week3/stability_macroF1.csv         测试集 Macro-F1 均值±标准差（模型×方法）
- runs/week3/stability_balanced_acc.csv    Balanced Accuracy 同上
- runs/week3/recall_per_class_mean.csv     每类 Recall 均值（模型×方法×类别）
- runs/week3/report.md                     汇总报告（协议、披露、结论素材）
- figures/method_comparison_macroF1.png    方法对比图（误差棒=种子间标准差）

用法：python src/06_analyze_week3.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs/experiments"
OUT = ROOT / "runs/week3"
FIGS = ROOT / "figures"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

METHOD_CN = {"none": "无处理", "class_weight": "类别权重", "ROS": "随机过采样", "SMOTE": "SMOTE"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    failed = []
    for d in sorted(RUNS.iterdir()):
        mpath = d / "metrics.json"
        cpath = d / "config.json"
        if not mpath.exists():
            continue
        m = json.loads(mpath.read_text(encoding="utf-8"))
        c = json.loads(cpath.read_text(encoding="utf-8"))
        if str(m.get("error", "")).startswith("FAILED"):
            failed.append(m)
            continue
        row = {
            "model": c["model"], "method": c["method"], "seed": c["seed"],
            "valid_macro_f1": m["valid"]["macro_f1"],
            "test_macro_f1": m["test"]["macro_f1"],
            "test_balanced_acc": m["test"]["balanced_acc"],
            "test_accuracy": m["test"]["accuracy"],
            "fit_s": m["fit_s"], "infer_test_s": m["infer_test_s"],
            "model_pickle_bytes": m["model_pickle_bytes"],
            "n_train_after_resample": m["n_train_after_resample"],
        }
        for cls, r in m["test_recall_per_class"].items():
            row[f"recall[{cls}]"] = r
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(RUNS / "summary_full.csv", index=False, encoding="utf-8-sig")
    n_expected = 36
    lines = ["# 第 3 周实验矩阵汇总", "",
             f"- 完成并读取 {len(df)}/{n_expected} 组；失败 {len(failed)} 组"
             + (f"：{[f['run_id'] for f in failed]}" if failed else ""),
             f"- 种子 [0,1,2]；协议与超参见各 run 的 config.json（先于结果固定）",
             ""]

    def pivot_with_std(metric):
        g = df.groupby(["model", "method"])[metric]
        mean = g.mean().unstack().round(4)
        std = g.std().unstack().round(4)
        comb = mean.copy().astype(object)
        for i in mean.index:
            for j in mean.columns:
                comb.loc[i, j] = f"{mean.loc[i, j]:.4f} ± {std.loc[i, j]:.4f}"
        return mean, std, comb

    for metric, fname in [("test_macro_f1", "stability_macroF1.csv"),
                          ("test_balanced_acc", "stability_balanced_acc.csv"),
                          ("valid_macro_f1", "stability_macroF1_valid.csv")]:
        mean, std, comb = pivot_with_std(metric)
        comb.to_csv(OUT / fname, encoding="utf-8-sig")
        title = "测试集" if metric.startswith("test") else "验证集"
        lines += [f"## {title} {metric}（均值 ± 标准差，3 种子）", "", "```",
                  comb.to_string(), "```", ""]
        if metric == "test_macro_f1":
            mf_mean, mf_std = mean, std

    # 开销表：耗时 / 模型大小 / 过采样后训练规模
    cost = df.groupby(["model", "method"]).agg(
        fit_s_mean=("fit_s", "mean"), infer_test_s_mean=("infer_test_s", "mean"),
        model_mb=("model_pickle_bytes", lambda x: round(x.mean() / 1e6, 2)),
        n_train_after=("n_train_after_resample", "mean"),
    ).round(2)
    cost.to_csv(OUT / "stability_cost.csv", encoding="utf-8-sig")
    lines += ["## 开销（均值）", "", "```", cost.to_string(), "```", ""]

    # 每类 Recall 均值
    recall_cols = [c for c in df.columns if c.startswith("recall[")]
    rec_mean = df.groupby(["model", "method"])[recall_cols].mean().round(4)
    rec_mean.to_csv(OUT / "recall_per_class_mean.csv", encoding="utf-8-sig")
    lines += ["## 每类 Recall 均值（测试集）", "", "```", rec_mean.to_string(), "```", ""]

    # 披露事项
    lines += ["## 披露", "",
              "- LR 的 lbfgs 求解器与 XGBoost(hist, 无行列采样) 在相同数据下具有确定性，"
              "none/class_weight 格子三种种子结果相同（标准差 0）是协议的如实反映，非错误；"
              "种子间变异来自 MLP 的初始化/洗牌与 ROS/SMOTE 的重采样随机性。",
              "- SMOTE 在 one-hot 编码空间插值会生成非 0/1 的合成哑变量取值，为该协议已知局限，"
              "论文局限性一节需说明。",
              "- ROS/SMOTE 将训练集过采样至最大类规模（约 44.8 万行），拟合与推理耗时的变化已记录。",
              "- model_pickle_bytes 是整个 pipeline 的 pickle 体积：ROS 格子因 RandomOverSampler "
              "保留 sample_indices_ 索引（数 MB）而偏大，不代表模型本体体积；"
              "论文口径的模型大小将在第 4 周单独测量纯模型组件。",
              "- 全部 9 个 SMOTE 格子的 n_train_after_resample 因 SMOTE 不暴露 sample_indices_ "
              "而记录为原始训练规模 140,272（红队复审更正：此前误写为「部分早期格子」），实际过采样后规模"
              "与 ROS 相同（约 448,000，各类补至多数类规模）；05 脚本已修正，后续运行不再出现。",
              "- MLP+ROS 有 1 格触发 ConvergenceWarning（max_iter=100 上限），协议统一不放宽。", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")

    # 图：Macro-F1 对比（误差棒 = 种子间标准差）
    order = ["none", "class_weight", "ROS", "SMOTE"]
    x = np.arange(len(order))
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), sharey=True)
    for ax, model in zip(axes, ["LR", "XGBoost", "MLP"]):
        means = [mf_mean.loc[model, m] for m in order]
        stds = [mf_std.loc[model, m] for m in order]
        ax.bar(x, means, yerr=stds, capsize=4,
               color=["#8ea8c3", "#d97f4a", "#6aa179", "#a678b8"])
        ax.set_xticks(x, [METHOD_CN[m] for m in order], fontsize=9)
        ax.set_title(model, fontsize=11)
        ax.grid(axis="y", alpha=0.3)
        for xi, v, s in zip(x, means, stds):
            ax.text(xi, v + s + 0.012, f"{v:.3f}", ha="center", va="bottom", fontsize=8.5)
    axes[0].set_ylabel("测试集 Macro-F1（3 种子均值）")
    fig.suptitle("不平衡处理方法对比（误差棒 = 种子间标准差）")
    fig.tight_layout()
    fig.savefig(FIGS / "method_comparison_macroF1.png", dpi=200)
    plt.close(fig)

    print(f"[OK] 完成读取 {len(df)}/{n_expected} 组，失败 {len(failed)} 组")
    print(f"[OK] -> {OUT}")
    print(f"[OK] 图 -> {FIGS / 'method_comparison_macroF1.png'}")
    print(comb.to_string())


if __name__ == "__main__":
    main()
