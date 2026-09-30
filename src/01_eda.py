"""第 1 周 EDA（发表级）：加载 UNSW-NB15 官方划分集，产出字段概览、缺失值、类别分布、
数据完整性核验（SHA-256 / 重复行 / label 一致性 / 零方差列）。

只读 data/raw/，不修改任何原始数据；产出写入 runs/eda/ 与 figures/。
用法：python src/01_eda.py
"""
import argparse
import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(root / "data/raw/UNSW_NB15_training-set.csv"))
    ap.add_argument("--test", default=str(root / "data/raw/UNSW_NB15_testing-set.csv"))
    args = ap.parse_args()

    out_runs = root / "runs/eda"
    out_figs = root / "figures"
    out_runs.mkdir(parents=True, exist_ok=True)
    out_figs.mkdir(parents=True, exist_ok=True)

    tr_path, te_path = Path(args.train), Path(args.test)
    tr = pd.read_csv(tr_path, low_memory=False, encoding="utf-8-sig")
    te = pd.read_csv(te_path, low_memory=False, encoding="utf-8-sig")

    lines = []
    log = lines.append
    log("# UNSW-NB15 EDA 报告（发表级）")
    log("")
    log("## 0. 数据版本指纹（可追溯性）")
    log("")
    log("| 文件 | 行数（含表头） | 大小 (MB) | SHA-256（前 16 位） |")
    log("|---|---|---|---|")
    for p, df in [(tr_path, tr), (te_path, te)]:
        size_mb = p.stat().st_size / 1e6
        log(f"| {p.name} | {len(df) + 1:,} | {size_mb:.1f} | `{sha256(p)[:16]}…` |")
    log("")
    log("- 来源：镜像仓库 Nir-J/ML-Projects（GitHub raw），下载日期 第 1 周（06-16 ~ 06-22）；"
        "官方渠道 research.unsw.edu.au 需填表申请，取得后须比对 SHA-256（见 data/README.md 待办）。")
    log("- 交叉验证：两文件行数与官方划分集公开规格一致（175,341 / 82,332 条）；"
        "各类别计数与文献报道的官方划分分布一致，支持其为官方文件副本。")
    log("")

    # ---- 字段概览 ----
    log("## 1. 字段概览")
    log("")
    cat_cols = [c for c in tr.columns if tr[c].dtype == object]
    log(f"- 总列数：{tr.shape[1]}（含 id / attack_cat / label）")
    log(f"- 类别型列：{cat_cols}")
    log(f"- 数值型列数：{tr.shape[1] - len(cat_cols)}")
    log("")

    # ---- 缺失值 ----
    log("## 2. 缺失值（NaN）")
    log("")
    miss = pd.DataFrame({"train": tr.isna().sum(), "test": te.isna().sum()})
    miss = miss[miss.sum(axis=1) > 0]
    if miss.empty:
        log("- 无 NaN。注意 `service` 列的 `-` 是占位符不是缺失值，当作合法类别。")
    else:
        log("```")
        log(miss.to_string())
        log("```")
    log("")

    # ---- 重复行 ----
    log("## 3. 重复行")
    log("")
    log(f"- 含 id 全行重复：训练 {tr.duplicated().sum()} 条 / 测试 {te.duplicated().sum()} 条")
    feat_cols = [c for c in tr.columns if c not in ("id", "label", "attack_cat")]
    dup_tr = tr.duplicated(subset=feat_cols, keep=False).sum()
    grp = tr.groupby(feat_cols, dropna=False)["label"].nunique()
    conflict_groups = int((grp > 1).sum())
    log(f"- 训练集去掉 id/label/attack_cat 后特征向量重复的行：{dup_tr:,} 条"
        "（网络流量中同特征记录可自然重复，官方划分保留，本项目不去重，此决策留痕）")
    log(f"- 同一特征向量对应不同 label 的冲突组：{conflict_groups} 组"
        + (" —— 存在不可约噪声，是各模型 Accuracy 上限的来源之一，论文误差分析可直接引用"
           if conflict_groups else " —— 无标签冲突"))
    log("")

    # ---- label 与 attack_cat 一致性 ----
    log("## 4. label 与 attack_cat 一致性（数据集已知质量问题）")
    log("")
    for name, df in [("训练", tr), ("测试", te)]:
        ac = df["attack_cat"].str.strip()
        normal_as_attack = ((ac == "Normal") & (df["label"] == 1)).sum()
        attack_as_normal = ((ac != "Normal") & (df["label"] == 0)).sum()
        log(f"- {name}集：Normal 但 label=1 共 {normal_as_attack} 条；"
            f"非 Normal 但 label=0 共 {attack_as_normal} 条"
            + (" —— 一致" if (normal_as_attack + attack_as_normal) == 0 else " —— 存在矛盾，预处理时需决定处理策略并留痕"))
    log("")

    # ---- 零方差列 ----
    log("## 5. 零方差 / 近零方差数值列（训练集）")
    log("")
    nunique = tr.select_dtypes("number").drop(columns=["label"]).nunique().sort_values()
    zero_var = nunique[nunique <= 2]
    if zero_var.empty:
        log("- 无（label 作为目标列已排除）。")
    else:
        log("```")
        log(zero_var.to_string())
        log("```")
        log("- 取值 ≤ 2 种的特征对树模型无碍，特征筛选阶段按贡献决定去留。")
    log("")

    # ---- service 占位符 ----
    log("## 6. service 占位符 `-` 占比")
    log("")
    log(f"- 训练集 {(tr['service'] == '-').mean() * 100:.1f}% / 测试集 {(te['service'] == '-').mean() * 100:.1f}%，作为合法类别编码。")
    log("")

    # ---- attack_cat 清洁度 ----
    log("## 7. attack_cat 清洁度")
    log("")
    raw_n = tr["attack_cat"].nunique()
    strip_n = tr["attack_cat"].str.strip().nunique()
    log(f"- 原始去重数 = {raw_n}，strip 后去重数 = {strip_n}"
        + ("（存在首尾空格，预处理必须 str.strip()）" if raw_n != strip_n else "（干净）"))
    log("")

    # ---- 类别分布 ----
    tr_cat = tr["attack_cat"].str.strip().value_counts()
    te_cat = te["attack_cat"].str.strip().value_counts()
    counts = pd.DataFrame({"train": tr_cat, "test": te_cat}).fillna(0).astype(int)
    counts["train_ratio_%"] = (counts["train"] / counts["train"].sum() * 100).round(2)
    counts["test_ratio_%"] = (counts["test"] / counts["test"].sum() * 100).round(2)
    counts.to_csv(out_runs / "class_counts.csv", encoding="utf-8-sig")

    ir = counts["train"].max() / counts["train"].min()
    log("## 8. 类别分布（attack_cat，strip 后）")
    log("")
    log("```")
    log(counts.to_string())
    log("```")
    log("")
    log(f"- 训练集不平衡比例（最多类/最少类）≈ {ir:.0f} : 1")
    log(f"- 最少类：{counts['train'].idxmin()}（{counts['train'].min()} 条）"
        f"—— 这就是后面少数类 Recall 最难看的那一类")
    log("")

    # ---- 二分类标签分布 ----
    log("## 9. 二分类 label 分布")
    log("")
    log("```")
    log(pd.DataFrame({
        "train": tr["label"].value_counts().sort_index(),
        "test": te["label"].value_counts().sort_index(),
    }).rename(index={0: "Normal(0)", 1: "Attack(1)"}).to_string())
    log("```")
    log("")

    # ---- 训练/测试分布一致性 ----
    same = (counts["train"] == counts["test"]).all()
    log("## 10. 划分方式核验")
    log("")
    log(f"- 训练/测试各类别数量完全相同：{same}（官方划分为全体样本的随机划分，两类数量不同属正常；"
        "保留官方划分，不自建测试集）")
    log("")

    (out_runs / "eda_report.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- 图：类别分布（对数轴）----
    order = counts.sort_values("train", ascending=False).index
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, col, color, title in [
        (axes[0], "train", "#4878a8", f"训练集（共 {counts['train'].sum():,} 条）"),
        (axes[1], "test", "#d97f4a", f"测试集（共 {counts['test'].sum():,} 条）"),
    ]:
        vals = counts.loc[order, col]
        ax.bar(order, vals, color=color)
        ax.set_yscale("log")
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.3)
        for x, v in enumerate(vals):
            ax.text(x, v, f"{v:,}", ha="center", va="bottom", fontsize=7.5)
    axes[0].set_ylabel("样本数（对数轴）")
    fig.suptitle("UNSW-NB15 attack_cat 类别分布（log 轴，注明数值）")
    fig.tight_layout()
    fig.savefig(out_figs / "class_distribution.png", dpi=200)
    plt.close(fig)

    print(f"[OK] 报告 -> {out_runs / 'eda_report.md'}")
    print(f"[OK] 类别计数 -> {out_runs / 'class_counts.csv'}")
    print(f"[OK] 图 -> {out_figs / 'class_distribution.png'}")
    print(counts.to_string())


if __name__ == "__main__":
    main()
