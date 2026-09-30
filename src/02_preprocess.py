"""第 2 周预处理（防泄漏顺序固定）：划分 → 仅在训练划分上拟合编码器与标准化器 → 转换 → 落盘。

顺序即纪律：OneHotEncoder / StandardScaler 只 fit 训练划分，valid/test 只 transform；
SMOTE 等重采样不在此处做（属于第 3 周实验内部，且只作用于训练数据）。

用法：python src/02_preprocess.py
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROC = ROOT / "data/processed"
RUNS = ROOT / "runs/preprocess"
SEED = 42
DROP_COLS = ["id"]
CAT_COLS = ["proto", "service", "state"]
TARGETS = ["attack_cat", "label"]


def main():
    PROC.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    tr = pd.read_csv(RAW / "UNSW_NB15_training-set.csv", encoding="utf-8-sig")
    te = pd.read_csv(RAW / "UNSW_NB15_testing-set.csv", encoding="utf-8-sig")
    for df in (tr, te):
        df.drop(columns=DROP_COLS, inplace=True, errors="ignore")
        df["attack_cat"] = df["attack_cat"].str.strip()

    # ---- 第 1 步：先划分（官方测试集冻结；验证集从官方训练集分层划出 20%）----
    tr_split, va_split = train_test_split(
        tr, test_size=0.2, random_state=SEED, stratify=tr["attack_cat"])
    feature_cols = [c for c in tr_split.columns if c not in CAT_COLS + TARGETS]

    # ---- 第 2 步：仅在训练划分上拟合编码器与标准化器 ----
    enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    enc.fit(tr_split[CAT_COLS])
    scaler = StandardScaler()
    scaler.fit(tr_split[feature_cols])

    def transform(df: pd.DataFrame) -> pd.DataFrame:
        cat_part = enc.transform(df[CAT_COLS])
        cat_names = list(enc.get_feature_names_out(CAT_COLS))
        num_part = scaler.transform(df[feature_cols])
        out = pd.DataFrame(num_part, columns=feature_cols, index=df.index)
        for i, name in enumerate(cat_names):
            out[name] = cat_part[:, i]
        out["attack_cat"] = df["attack_cat"].values
        out["label"] = df["label"].values
        return out

    splits = {
        "train": transform(tr_split),
        "valid": transform(va_split),
        "test": transform(te),
    }

    # ---- 第 3 步：落盘与留痕 ----
    lines = ["# 预处理报告", "", f"- 随机种子：{SEED}（仅用于训练集内部划分验证集）",
             f"- 划分：官方训练集 -> 训练 {len(splits['train']):,} / 验证 {len(splits['valid']):,}（分层 20%）；官方测试集 {len(splits['test']):,} 冻结不动",
             f"- 处理顺序：先划分，再拟合编码/标准化（仅训练划分 fit），无缺失值需填充（EDA 第 2 节）",
             f"- attack_cat 已 str.strip；id 已丢弃；{CAT_COLS} one-hot 后总特征数 = {splits['train'].shape[1] - 2}",
             ""]
    log = lines.append
    log("## 各划分类别分布（attack_cat）")
    log("")
    log("```")
    dist = pd.DataFrame({
        "train": splits["train"]["attack_cat"].value_counts(),
        "valid": splits["valid"]["attack_cat"].value_counts(),
        "test": splits["test"]["attack_cat"].value_counts(),
    }).fillna(0).astype(int)
    log(dist.to_string())
    log("```")
    (RUNS / "report.md").write_text("\n".join(lines), encoding="utf-8")

    meta = {
        "seed": SEED,
        "drop_cols": DROP_COLS,
        "cat_cols": CAT_COLS,
        "n_features_after_encode": splits["train"].shape[1] - 2,
        "sizes": {k: int(len(v)) for k, v in splits.items()},
        "leakage_discipline": "encoders fitted on train split only; resampling deferred to experiment-time on train only",
    }
    (RUNS / "config.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    for name, df in splits.items():
        df.to_parquet(PROC / f"{name}.parquet", index=False)
    joblib.dump({"encoder": enc, "scaler": scaler,
                 "cat_cols": CAT_COLS, "feature_cols": feature_cols},
                PROC / "artifacts.joblib")

    print(f"[OK] 三份划分 -> {PROC}/(train|valid|test).parquet")
    print(f"[OK] 编码器/标准化器 -> {PROC}/artifacts.joblib")
    print(f"[OK] 报告 -> {RUNS / 'report.md'}")
    print(dist.to_string())


if __name__ == "__main__":
    main()
