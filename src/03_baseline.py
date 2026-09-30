"""第 2 周基线：Logistic Regression、XGBoost、XGBoost+类别权重，在验证/测试集上评估。

主指标：Macro-F1、Balanced Accuracy、每类 Recall；Accuracy 仅辅助。
每个模型输出混淆矩阵，拼成第一张混淆矩阵图。种子 42（单种子基线；第 3 周起 3 种子）。

用法：python src/03_baseline.py
"""
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, recall_score)
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
RUNS = ROOT / "runs/baseline"
FIGS = ROOT / "figures"
SEED = 42

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load(name):
    df = pd.read_parquet(PROC / f"{name}.parquet")
    X = df.drop(columns=["attack_cat", "label"])
    return X, df["attack_cat"]


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    Xs, ys = {}, {}
    for split in ("train", "valid", "test"):
        Xs[split], ys[split] = load(split)
    classes = sorted(ys["train"].unique())
    # XGBoost 要求整数类别标签：统一编码为 0..9，报告时用 classes 映射回类名
    code = {c: i for i, c in enumerate(classes)}
    ys = {k: v.map(code).astype(int) for k, v in ys.items()}

    models = {
        "LR": LogisticRegression(max_iter=1000, random_state=SEED),
        "XGBoost": XGBClassifier(objective="multi:softprob", num_class=len(classes),
                                 n_estimators=300, max_depth=6, learning_rate=0.1,
                                 tree_method="hist", random_state=SEED, n_jobs=-1),
        "XGBoost+W": XGBClassifier(objective="multi:softprob", num_class=len(classes),
                                   n_estimators=300, max_depth=6, learning_rate=0.1,
                                   tree_method="hist", random_state=SEED, n_jobs=-1),
    }
    weights = compute_sample_weight("balanced", ys["train"])

    all_rows, cms = [], {}
    for name, model in models.items():
        if name == "XGBoost+W":
            t0 = time.perf_counter(); model.fit(Xs["train"], ys["train"], sample_weight=weights); fit_s = time.perf_counter() - t0
        else:
            t0 = time.perf_counter(); model.fit(Xs["train"], ys["train"]); fit_s = time.perf_counter() - t0
        pred_valid = model.predict(Xs["valid"])
        t0 = time.perf_counter(); pred_test = model.predict(Xs["test"]); infer_s = time.perf_counter() - t0
        for split, y_true, y_hat in [("valid", ys["valid"], pred_valid), ("test", ys["test"], pred_test)]:
            all_rows.append({
                "model": name, "split": split,
                "macro_f1": round(f1_score(y_true, y_hat, average="macro"), 4),
                "balanced_acc": round(balanced_accuracy_score(y_true, y_hat), 4),
                "accuracy": round(accuracy_score(y_true, y_hat), 4),
                "fit_s": round(fit_s, 1), "infer_test_s": round(infer_s, 3),
            })
        recalls = recall_score(ys["test"], pred_test, average=None,
                               labels=range(len(classes)), zero_division=0)
        for cls, r in zip(classes, recalls):
            all_rows.append({"model": name, "split": f"recall[{cls}]", "recall": round(float(r), 4)})
        cms[name] = confusion_matrix(ys["test"], pred_test, labels=range(len(classes)))

    df_metrics = pd.DataFrame(all_rows)
    df_metrics.to_csv(RUNS / "metrics.csv", index=False, encoding="utf-8-sig")
    (RUNS / "config.json").write_text(json.dumps({
        "seed": SEED, "n_estimators": 300, "max_depth": 6, "learning_rate": 0.1,
        "LR": {"max_iter": 1000},
        "data": "data/processed/*.parquet (02_preprocess.py, seed 42)",
        "note": "单种子基线；正式多方法矩阵自第 3 周起跑 seeds [0,1,2]",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- 第一张混淆矩阵图 ----
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.6))
    for ax, (name, cm) in zip(axes, cms.items()):
        cm_norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
        im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(len(classes)), labels=classes, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(classes)), labels=classes, fontsize=8)
        for i in range(len(classes)):
            for j in range(len(classes)):
                if cm[i, j]:
                    ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                            fontsize=6.5, color="black" if cm_norm[i, j] < 0.6 else "white")
        row = df_metrics[(df_metrics.model == name) & (df_metrics.split == "test")].iloc[0]
        ax.set_title(f"{name}（测试集 Accuracy={row['accuracy']:.3f}, Macro-F1={row['macro_f1']:.3f}）", fontsize=10)
        ax.set_xlabel("预测类别", fontsize=9); ax.set_ylabel("真实类别", fontsize=9)
    fig.colorbar(im, ax=axes, fraction=0.018, label="行归一化比例")
    fig.suptitle("第一张混淆矩阵：UNSW-NB15 基线（对角线=召回，行归一化着色，格内为样本数）")
    fig.savefig(FIGS / "confusion_matrix_baseline.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(df_metrics[~df_metrics.split.str.startswith("recall")].to_string(index=False))
    print("\n每类 Recall（测试集）：")
    print(df_metrics[df_metrics.split.str.startswith("recall")]
          .pivot(index="split", columns="model", values="recall").to_string())
    print(f"\n[OK] 指标 -> {RUNS / 'metrics.csv'}")
    print(f"[OK] 混淆矩阵 -> {FIGS / 'confusion_matrix_baseline.png'}")


if __name__ == "__main__":
    main()
