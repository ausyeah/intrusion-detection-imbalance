"""第 6 周 E②：误差归因 3 种子区间版（红队台账 K5）。

读取 runs/week4{,_seed1,_seed2}/attribution.json（同选型、不同种子的重训归因），
输出每个模型 novel/conflict/overlap_clean 计数与占比的均值±区间，回答
「归因百分比是单种子代表性运行还是稳定结论」。

用法：python src/14_attribution_summary.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/week6"


def main():
    rows = []
    for seed, d in [(0, "runs/week4"), (1, "runs/week4_seed1"), (2, "runs/week4_seed2")]:
        p = ROOT / d / "attribution.json"
        j = json.loads(p.read_text(encoding="utf-8"))
        for model, a in j["attribution"].items():
            total = a["novel"] + a["conflict"] + a["overlap_clean"]
            rows.append({"model": model, "seed": seed, "n_err": total,
                         "novel_n": a["novel"], "conflict_n": a["conflict"],
                         "overlap_clean_n": a["overlap_clean"],
                         "novel_pct": round(a["novel"] / total * 100, 1),
                         "conflict_pct": round(a["conflict"] / total * 100, 1),
                         "overlap_pct": round(a["overlap_clean"] / total * 100, 1)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "attribution_3seeds.csv", index=False, encoding="utf-8-sig")

    agg = df.groupby("model")[["novel_pct", "conflict_pct", "overlap_pct",
                               "n_err"]].agg(["mean", "min", "max"]).round(1)
    lines = ["# 误差归因 3 种子区间版（红队台账 K5）", "",
             "- 选型：验证集（三模型均 SMOTE）；seeds [0,1,2] 各自重训后归因。",
             "- 目的：检验第 4 周 v2 的归因百分比（novel 83–84%、conflict 7.4–8.4%、"
             "overlap 8–9%）是否为稳定的种子级结论。", "",
             "## 按模型汇总（均值 / 最小 / 最大）", "", "```", agg.to_string(), "```", "",
             "## 明细", "", "```", df.to_string(index=False), "```", "",
             "- 结论表述规则：区间宽度 ≤1 个百分点的归因可写为点估计；更宽的以区间表述。"]
    (OUT / "attribution_3seeds.md").write_text("\n".join(lines), encoding="utf-8")
    print(df.to_string(index=False))
    print(agg.to_string())
    print(f"\n[OK] -> {OUT / 'attribution_3seeds.md'}")


if __name__ == "__main__":
    main()
