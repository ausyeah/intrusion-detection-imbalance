"""v2 方差补测协议（第 8 周，红队三轮 A1-3 / 用户决策 T4）：每种子重切验证集。

背景：XGBoost（none/class_weight）与 LR 为确定性算法，在 02_preprocess.py 的固定
切分（seed 42）下重跑任意次结果完全相同，"3 种子"退化为单条件重复（std=0 是
可复现性而非稳健性）。本模块为封板后的方差补测提供数据层：让每个种子对应一次
独立的验证集切分，从而暴露真实的切分敏感性方差。

协议（先划分后拟合纪律逐种子成立）：
- 官方测试集（UNSW_NB15_testing-set.csv）冻结不动，永远只做 transform，不参与
  任何拟合/选型/调参；原始 CSV 与 v1 的 test.parquet 是同一份官方数据。
- 官方训练池（UNSW_NB15_training-set.csv，175,341 行）：按种子 s 分层重切
  80/20 → train_s / valid_s（train_test_split(random_state=s, stratify=attack_cat)）。
- StandardScaler 仅在 train_s 上 fit（统计量逐种子独立）。
- OneHotEncoder 类别表固定沿用 v1 封板 schema（data/processed/artifacts.joblib 中
  encoder.categories_，194 列，与封板主矩阵逐列一致）：某类别未出现在某种子训练
  划分时该列恒 0（与 handle_unknown="ignore" 语义一致）。理由：v2 的目的是同一
  流水线的方差分解，固定特征 schema 可隔离「切分敏感性」这一个变量源，并与 v1
  保持列级可比；类别表是字段取值域的元数据，不是拟合统计量。实测有 3 个稀有
  类别（state_URN/state_PAR/proto_rtp）仅在部分切分的训练侧出现，故必须固定。

用法（脚本内）：
    import resplit
    splits_s = resplit.make_splits(seed)   # {"train": df, "valid": df, "test": df}

v1 固定切分产物（data/processed/*.parquet）原样保留，v2 不写 data/processed。
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROC_V1 = ROOT / "data/processed"
DROP_COLS = ["id"]
CAT_COLS = ["proto", "service", "state"]
TARGETS = ["attack_cat", "label"]
TEST_SIZE = 0.2


def _v1_schema():
    """v1 封板 schema：one-hot 类别表（固定）+ 数值特征列顺序 + 全列顺序。"""
    art = joblib.load(PROC_V1 / "artifacts.joblib")
    cats = [list(c) for c in art["encoder"].categories_]
    feature_cols = list(art["feature_cols"])
    ref_cols = list(pd.read_parquet(PROC_V1 / "train.parquet").columns)
    return cats, feature_cols, ref_cols


def _load_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.drop(columns=DROP_COLS, inplace=True, errors="ignore")
    df["attack_cat"] = df["attack_cat"].str.strip()
    return df


def make_splits(seed: int) -> dict:
    """按给定种子重切官方训练池并完成防泄漏预处理，返回三个 processed DataFrame。

    断言：输出列与 v1 产物逐列一致（one-hot 固定 schema + 数值列顺序）。
    """
    cats, feature_cols, ref_cols = _v1_schema()
    pool = _load_clean(RAW / "UNSW_NB15_training-set.csv")
    test_raw = _load_clean(RAW / "UNSW_NB15_testing-set.csv")

    tr_split, va_split = train_test_split(
        pool, test_size=TEST_SIZE, random_state=seed, stratify=pool["attack_cat"])

    enc = OneHotEncoder(categories=cats, handle_unknown="ignore", sparse_output=False)
    enc.fit(tr_split[CAT_COLS])
    scaler = StandardScaler()
    scaler.fit(tr_split[feature_cols])

    def transform(df: pd.DataFrame) -> pd.DataFrame:
        num_part = scaler.transform(df[feature_cols])
        cat_part = enc.transform(df[CAT_COLS])
        out = pd.DataFrame(
            np.hstack([num_part, cat_part]),
            columns=feature_cols + list(enc.get_feature_names_out(CAT_COLS)),
            index=df.index,
        )
        out["attack_cat"] = df["attack_cat"].values
        out["label"] = df["label"].values
        return out

    splits = {
        "train": transform(tr_split),
        "valid": transform(va_split),
        "test": transform(test_raw),
    }
    got_cols = list(splits["train"].columns)
    if got_cols != ref_cols:
        raise AssertionError(
            f"v2 特征 schema 与 v1 不一致：缺失 {set(ref_cols) - set(got_cols)}，"
            f"多出 {set(got_cols) - set(ref_cols)}——禁止静默继续")
    return splits


if __name__ == "__main__":
    # 自检：三种子的 schema 一致性与划分尺寸
    for s in (0, 1, 2):
        sp = make_splits(s)
        print(f"[ok] seed={s}: train {len(sp['train']):,} / valid {len(sp['valid']):,} "
              f"/ test {len(sp['test']):,} | features {sp['train'].shape[1] - 2}")
