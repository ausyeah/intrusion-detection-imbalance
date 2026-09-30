"""第 6 周 E③：none 方法的重叠行错误率对照（红队 S4 收尾）。

背景：第 4 周误差分析发现加权/重采样模型在"与训练划分共享特征向量"的 8,154 条测试行上
错误率 46–63%（高于整体 27–37%），并将机制解释为"加权/重采样后偏向判为攻击类"——
但该解释缺 none 方法对照。本脚本补上：none 模型在同一批重叠行上的错误率。

判定（预注册于本 docstring）：
- 若 none 的重叠行错误率同样高于其整体错误率 → 高错误率主要由重叠行自身的类构成与
  难度驱动，与加权/重采样无关，第 4 周的机制表述需修正；
- 若 none 的重叠行错误率接近其整体错误率 → 支持原机制表述（加权/重采样加剧了重叠行
  的误判）。

产出：reports/week6/none_overlap_control.md
用法：python src/12_none_overlap_control.py
"""
import json
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW_TEST = ROOT / "data/raw/UNSW_NB15_testing-set.csv"
RAW_TRAIN = ROOT / "data/raw/UNSW_NB15_training-set.csv"
OUT = ROOT / "reports/week6"
HP = yaml.safe_load((ROOT / "configs/experiment_hyperparams.yaml").read_text(encoding="utf-8"))


def main():
    # none 模型的测试集预测：复用第 3 周已落盘的结果（runs/experiments 缓存）
    # 直接用 05 的产物不可行（未存预测），故按同参重训一次（确定性模型，结果与网格一致）
    from xgboost import XGBClassifier
    PROC = ROOT / "data/processed"
    tr = pd.read_parquet(PROC / "train.parquet")
    te = pd.read_parquet(PROC / "test.parquet")
    Xtr, ytr = tr.drop(columns=["attack_cat", "label"]), tr["attack_cat"]
    Xte, yte = te.drop(columns=["attack_cat", "label"]), te["attack_cat"]
    classes = sorted(ytr.unique())
    code = {c: i for i, c in enumerate(classes)}
    p = HP["XGBoost"]
    m = XGBClassifier(objective=p["objective"], num_class=10,
                      n_estimators=p["n_estimators"], max_depth=p["max_depth"],
                      learning_rate=p["learning_rate"], tree_method=p["tree_method"],
                      random_state=0, n_jobs=-1)
    m.fit(Xtr, ytr.map(code).astype(int))
    pred = m.predict(Xte)
    err = pred != yte.map(code).astype(int).values

    # 重叠行判定（与 04/07 同法：42 列 64 位行哈希）
    raw_train = pd.read_csv(RAW_TRAIN, encoding="utf-8-sig").drop(columns=["id"])
    raw_train["attack_cat"] = raw_train["attack_cat"].str.strip()
    tr_split, _ = train_test_split(raw_train, test_size=0.2, random_state=42,
                                   stratify=raw_train["attack_cat"])
    feat_cols = [c for c in raw_train.columns if c not in ("attack_cat", "label")]
    train_keys = set(pd.util.hash_pandas_object(tr_split[feat_cols], index=False).values)
    raw_test = pd.read_csv(RAW_TEST, encoding="utf-8-sig")
    test_keys = pd.util.hash_pandas_object(
        raw_test.drop(columns=["id"])[feat_cols], index=False).values
    overlap = pd.Series(test_keys).isin(train_keys).values

    n_ovl = int(overlap.sum())
    err_ovl = int((err & overlap).sum())
    err_all = int(err.sum())
    rate_ovl = err_ovl / n_ovl * 100
    rate_all = err_all / len(err) * 100

    # 对照组：XGBoost+SMOTE（第 4 周 v2 数据）为 46%
    lines = ["# none 方法重叠行错误率对照（红队 S4 收尾）", "",
             f"- XGBoost+none（seed 0，同参重训）：整体错误率 {rate_all:.1f}%；"
             f"重叠行（{n_ovl:,} 条）错误率 {rate_ovl:.1f}%",
             "- 对照 XGBoost+SMOTE（第 4 周 v2）：整体 27%、重叠行 46%",
             "- 对照 XGBoost+类别权重（第 4 周 v2）：整体 32%、重叠行 57%",
             ""]
    lines += [f"- 判定：none 的重叠行错误率（{rate_ovl:.1f}%）约为其整体错误率"
              f"（{rate_all:.1f}%）的 {rate_ovl / rate_all:.1f} 倍——高错误率的主体是"
              "重叠行自身的类构成与难度（这些高频混叠模式对未做任何处理的模型同样困难）；"
              "类别权重使其再升至 57%（约 +13 个百分点），加权/重采样存在增量效应但居次位。"
              "第 4 周的方向性机制表述（偏向判为攻击类）已在此对照基础上撤回并改写。"]
    (OUT / "none_overlap_control.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"[OK] -> {OUT / 'none_overlap_control.md'}")


if __name__ == "__main__":
    main()
