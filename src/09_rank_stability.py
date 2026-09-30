"""第 6 周 A 项：方法排序稳定性（Kendall τ），按 reports/week6/preregistration_rank_stability.md
冻结的口径计算。不得增删比较对；τ 必须与完整排序表一并输出。

用法：python src/09_rank_stability.py
"""
from pathlib import Path

import pandas as pd
from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs/experiments"
OUT = ROOT / "reports/week6"
METHODS = ["none", "class_weight", "ROS", "SMOTE"]
MINORITY = ["Analysis", "Backdoor", "Shellcode", "Worms"]  # 预注册定义（训练数 ≤ 2000）


def rank_series(s):
    """按均值降序给方法排序，返回 method→名次 的向量（顺序与 METHODS 一致）。"""
    r = s.rank(ascending=False, method="min")
    return [float(r[m]) for m in METHODS]


def main():
    df = pd.read_csv(RUNS / "summary_full.csv")
    g = df.groupby(["model", "method"])
    mean = g.agg(mf1=("test_macro_f1", "mean"), ba=("test_balanced_acc", "mean"),
                 vf1=("valid_macro_f1", "mean"))
    for c in MINORITY:
        mean[f"r_{c}"] = g[f"recall[{c}]"].mean()
    mean["minority_macro_recall"] = mean[[f"r_{c}" for c in MINORITY]].mean(axis=1)

    models = ["LR", "XGBoost", "MLP"]
    results = []
    rankings = {}

    def add(group, a_col, b_col, a_name, b_name, extra=""):
        for model in models:
            sa = mean.loc[model, a_col]
            sb = mean.loc[model, b_col]
            ta = rank_series(sa)
            tb = rank_series(sb)
            tau, _ = kendalltau(ta, tb)
            results.append({"group": group, "model": model,
                            "comparison": f"{a_name} vs {b_name}", "tau": round(float(tau), 3),
                            "order_a": " > ".join(sa.sort_values(ascending=False).index),
                            "order_b": " > ".join(sb.sort_values(ascending=False).index),
                            "note": extra})
        rankings.setdefault(group, {})

    add("选型分割间", "vf1", "mf1", "验证集 Macro-F1", "测试集 Macro-F1")
    for a, b in [("mf1", "ba"),
                 ("mf1", "minority_macro_recall")]:
        add("指标间", a, b, a, b)
    for metric, label in [("mf1", "测试 Macro-F1"),
                          ("ba", "测试 Balanced Acc")]:
        pairs = [("LR", "XGBoost"), ("XGBoost", "MLP"), ("LR", "MLP")]
        for ma, mb in pairs:
            ta = rank_series(mean.loc[ma, metric])
            tb = rank_series(mean.loc[mb, metric])
            tau, _ = kendalltau(ta, tb)
            results.append({"group": "模型间", "model": f"{ma} vs {mb}",
                            "comparison": f"{label} 下方法排序", "tau": round(float(tau), 3),
                            "order_a": " > ".join(mean.loc[ma, metric].sort_values(ascending=False).index),
                            "order_b": " > ".join(mean.loc[mb, metric].sort_values(ascending=False).index),
                            "note": ""})
    res = pd.DataFrame(results)
    res.to_csv(OUT / "rank_stability.csv", index=False, encoding="utf-8-sig")

    def judge(t):
        return "方向基本一致" if t >= 2 / 3 else ("部分一致" if t >= 1 / 3 else "不一致")

    lines = ["# 方法排序稳定性（预注册 τ 检验结果）", "",
             "- 口径与判定标准见 preregistration_rank_stability.md（回溯性预注册，"
             "冻结于计算前）；n=4 方法的 τ 取值离散，结论以「τ + 完整排序」共同呈现。", ""]
    for group in ["选型分割间", "指标间", "模型间"]:
        sub = res[res.group == group]
        avg = sub.tau.mean()
        lines += [f"## {group}（平均 τ = {avg:.3f} → {judge(avg)}）", "", "```",
                  sub.to_string(index=False), "```", ""]
    lines += ["## 预注册判定回顾", ""]
    for h, group in [("H1 选型分割", "选型分割间"), ("H2 指标口径", "指标间"), ("H3 模型", "模型间")]:
        avg = res[res.group == group].tau.mean()
        verdict = "支持（排序不稳定）" if avg < 2 / 3 else "不支持（排序在该维度基本一致）"
        lines.append(f"- {h}：平均 τ = {avg:.3f} < 2/3 → {verdict}" if avg < 2 / 3
                     else f"- {h}：平均 τ = {avg:.3f} ≥ 2/3 → {verdict}")
    lines += ["", "- 限定：n=4 描述性检验，无 p 值宣称；τ 与排序表共同阅读。",
              "- 数据源：runs/experiments/summary_full.csv（3 种子均值），与第 3 周稳定性表同源。"]
    (OUT / "rank_stability.md").write_text("\n".join(lines), encoding="utf-8")
    print(res.to_string(index=False))
    print(f"\n[OK] -> {OUT / 'rank_stability.md'}")


if __name__ == "__main__":
    main()
