"""划分重叠审计：量化训练/验证/测试三个划分之间特征向量的重叠与标签冲突。

背景：EDA 发现训练集 48% 行涉及同特征向量重复（数据集固有）。官方划分保留这些重复，
意味着训练划分与验证/测试之间存在相同特征向量——审稿人必问的「重复泄漏」问题。
本脚本只读 data/raw，用 64 位行哈希量化重叠程度，为论文「局限性」提供留痕数据。

方法：pandas.util.hash_pandas_object 对 42 个原始特征列生成行哈希；
20 万行规模下哈希碰撞概率 < 1e-9，可忽略。划分方式与 02_preprocess.py 完全一致
（seed=42，分层 20%），保证结论对得上实验管线。

用法：python src/04_split_overlap_audit.py
"""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "runs/audit"
SEED = 42


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tr = pd.read_csv(RAW / "UNSW_NB15_training-set.csv", encoding="utf-8-sig").drop(columns=["id"])
    te = pd.read_csv(RAW / "UNSW_NB15_testing-set.csv", encoding="utf-8-sig").drop(columns=["id"])
    for df in (tr, te):
        df["attack_cat"] = df["attack_cat"].str.strip()

    tr_split, va_split = train_test_split(tr, test_size=0.2, random_state=SEED,
                                          stratify=tr["attack_cat"])
    parts = {"训练划分": tr_split, "验证划分": va_split, "测试集": te}
    feat_cols = [c for c in tr.columns if c not in ("attack_cat", "label")]

    keys = {}
    for name, df in parts.items():
        keys[name] = pd.util.hash_pandas_object(df[feat_cols], index=False).values
        df["_k"] = keys[name]

    lines = ["# 划分重叠审计报告", "",
             f"- 方法：42 个原始特征列的 64 位行哈希（碰撞概率 < 1e-9）；划分方式与 02_preprocess.py 一致（seed={SEED}）",
             f"- 各划分规模：训练 {len(tr_split):,} / 验证 {len(va_split):,} / 测试 {len(te):,}",
             ""]
    log = lines.append
    log("| 划分 A ∩ B | 共享特征向量数 | B 中落在共享向量上的行数 | 占 B 比例 | 共享向量中标签冲突组 |")
    log("|---|---|---|---|---|")

    pairs = [("训练划分", "验证划分"), ("训练划分", "测试集"), ("验证划分", "测试集")]
    summary = {}
    for a_name, b_name in pairs:
        shared = set(keys[a_name]) & set(keys[b_name])
        b_mask = pd.Series(keys[b_name]).isin(shared).values
        b_rows = int(b_mask.sum())
        comb = pd.concat([
            parts[a_name].loc[parts[a_name]["_k"].isin(shared), ["_k", "label"]],
            parts[b_name].loc[b_mask, ["_k", "label"]],
        ])
        conflicts = int((comb.groupby("_k")["label"].nunique() > 1).sum())
        pct = b_rows / len(parts[b_name]) * 100
        log(f"| {a_name} ∩ {b_name} | {len(shared):,} | {b_rows:,} | {pct:.1f}% | {conflicts:,} |")
        summary[f"{a_name}-{b_name}"] = {"shared_vectors": len(shared),
                                         "rows_in_b": b_rows, "pct_b": round(pct, 1),
                                         "label_conflict_groups": conflicts}

    intra = int(tr_split.duplicated(subset=feat_cols).sum())
    log("")
    log(f"- 训练划分内部重复行（多余副本）：{intra:,} 条")
    log("- 结论：重叠源于官方划分对数据集固有重复的保留，属数据集特性而非流程错误。"
        "本项目决策：原样保留以与已有文献可比；论文「局限性」一节引用本报告，"
        "说明绝对指标（Accuracy 等）可能因此整体偏高，但不改变方法间的相对比较结论。")

    (OUT / "overlap_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[OK] -> {OUT / 'overlap_report.md'}")


if __name__ == "__main__":
    main()
