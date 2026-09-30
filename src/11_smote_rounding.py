"""第 6 周 C 项：SMOTE 哑变量取整敏感性——检验 one-hot 插值伪影是否翻转结论。

协议（docstring 即预注册，运行前冻结）：
- 对象：XGBoost + SMOTE（第 3 周网格中对 XGB 的 Macro-F1 最差、但 DoS Recall 最好的
  格子——伪影嫌疑最大的格子），超参取 configs/experiment_hyperparams.yaml，seeds [0,1,2]。
- 变体：SMOTE 重采样后，对合成行的 one-hot 哑变量列（proto_/service_/state_ 前缀）
  取整为合法 0/1（每列 round 后 clip 到 [0,1]；不做按行归一化，仅最小干预），
  其余数值列保持插值原值；邻居计算仍用原始 SMOTE（干预仅作用于生成后的样本）。
- 对照：同一 SMOTE（不取整）与 none 基线。测试集只在评估时使用；3 种子。
- 判定：若取整版与不取整版的测试 Macro-F1 / DoS Recall 差异量级与第 3 周方法间差距
  （≥0.01）相当，则插值伪影实质性影响结论；若差异 << 0.01，则结论对伪影稳健。

产出：runs/smote_rounding/rounding_results.csv、reports/week6/smote_rounding.md
用法：python src/11_smote_rounding.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from imblearn.over_sampling import SMOTE
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
OUT = ROOT / "runs/smote_rounding"
REPORT = ROOT / "reports/week6"
HP = yaml.safe_load((ROOT / "configs/experiment_hyperparams.yaml").read_text(encoding="utf-8"))
SEEDS = [0, 1, 2]
DUMMY_PREFIX = ("proto_", "service_", "state_")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    Xs, ys = {}, {}
    for split in ("train", "valid", "test"):
        df = pd.read_parquet(PROC / f"{split}.parquet")
        Xs[split] = df.drop(columns=["attack_cat", "label"])
        ys[split] = df["attack_cat"]
    classes = sorted(ys["train"].unique())
    code = {c: i for i, c in enumerate(classes)}
    ys_enc = {k: v.map(code).astype(int) for k, v in ys.items()}
    dummy_cols = [c for c in Xs["train"].columns if c.startswith(DUMMY_PREFIX)]
    p = HP["XGBoost"]

    def make_model(seed):
        return XGBClassifier(objective=p["objective"], num_class=10,
                             n_estimators=p["n_estimators"], max_depth=p["max_depth"],
                             learning_rate=p["learning_rate"], tree_method=p["tree_method"],
                             random_state=seed, n_jobs=-1)

    rows = []
    for seed in SEEDS:
        # none 基线（每次种子循环重算一次，保证同模型可比）
        m = make_model(seed)
        m.fit(Xs["train"], ys_enc["train"])
        pred = m.predict(Xs["test"])
        rows.append({"variant": "none", "seed": seed,
                     "test_macro_f1": round(float(f1_score(ys_enc["test"], pred, average="macro")), 4),
                     "test_balanced_acc": round(float(balanced_accuracy_score(ys_enc["test"], pred)), 4),
                     "test_dos_recall": round(float(recall_score(
                         ys_enc["test"], pred, labels=[code["DoS"]], average=None,
                         zero_division=0)[0]), 4)})

        sm = SMOTE(random_state=seed)
        X_res, y_res = sm.fit_resample(Xs["train"], ys_enc["train"])
        n_syn = len(X_res) - len(Xs["train"])
        for variant, do_round in [("smote", False), ("smote_rounded", True)]:
            Xr = X_res.copy()
            if do_round:
                Xr[dummy_cols] = Xr[dummy_cols].round().clip(0, 1)
            m = make_model(seed)
            m.fit(Xr, y_res)
            pred = m.predict(Xs["test"])
            rows.append({"variant": variant, "seed": seed,
                         "test_macro_f1": round(float(f1_score(ys_enc["test"], pred, average="macro")), 4),
                         "test_balanced_acc": round(float(balanced_accuracy_score(ys_enc["test"], pred)), 4),
                         "test_dos_recall": round(float(recall_score(
                             ys_enc["test"], pred, labels=[code["DoS"]], average=None,
                             zero_division=0)[0]), 4),
                         "n_synthetic_rounded": int(n_syn) if do_round else 0})
        print(f"[done] seed {seed}", flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "rounding_results.csv", index=False, encoding="utf-8-sig")
    agg = res.groupby("variant")[["test_macro_f1", "test_balanced_acc", "test_dos_recall"]].agg(
        ["mean", "std"]).round(4)

    smote_mean = res[res.variant == "smote"].test_macro_f1.mean()
    rounded_mean = res[res.variant == "smote_rounded"].test_macro_f1.mean()
    dos_diff = (res[res.variant == "smote"].test_dos_recall.mean()
                - res[res.variant == "smote_rounded"].test_dos_recall.mean())
    verdict = ("插值伪影对结论影响可忽略（差异 << 方法间差距 0.01）"
               if abs(smote_mean - rounded_mean) < 0.01
               else "插值伪影实质性影响结果——原结论需限定")

    lines = ["# SMOTE 哑变量取整敏感性（红队 S6 折中检验）", "",
             f"- 协议：SMOTE(random_state=seed) 重采样后，对合成行的 {len(dummy_cols)} 个"
             " one-hot 哑变量列取整（最小干预），XGBoost 同参 3 种子；对照 none 与不取整 SMOTE。",
             f"- 测试 Macro-F1 均值：none {res[res.variant=='none'].test_macro_f1.mean():.4f} / "
             f"SMOTE {smote_mean:.4f} / SMOTE取整 {rounded_mean:.4f}",
             f"- DoS Recall 均值：SMOTE {res[res.variant=='smote'].test_dos_recall.mean():.4f} / "
             f"取整 {res[res.variant=='smote_rounded'].test_dos_recall.mean():.4f}"
             f"（差 {dos_diff:+.4f}）",
             f"- **判定：{verdict}**", "",
             "## 汇总（3 种子均值/标准差）", "", "```", agg.to_string(), "```", "",
             "## 明细", "", "```", res.to_string(index=False), "```", "",
             "- 限定：取整为最小干预近似（未做按行独热归一化、未改邻居计算），"
             "结论仅在此口径内成立。"]
    (REPORT / "smote_rounding.md").write_text("\n".join(lines), encoding="utf-8")
    print(agg.to_string())
    print(f"\n判定：{verdict}")
    print(f"[OK] -> {OUT} 与 {REPORT / 'smote_rounding.md'}")


if __name__ == "__main__":
    main()
