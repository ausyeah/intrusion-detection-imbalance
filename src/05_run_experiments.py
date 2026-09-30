"""第 3 周不平衡实验矩阵：3 模型 × 4 方法 × 3 种子 = 36 组。

协议（在看到任何结果之前固定，全部留痕于各 run 的 config.json）：
- 数据：data/processed/*.parquet（02_preprocess.py 产物，编码与标准化仅训练划分拟合）
- 划分：训练 / 验证（调参观察用）/ 测试（评估用），同第 2 周
- 种子：seeds = [0, 1, 2]，同时作用于模型 random_state 与重采样器 random_state
- 方法：
    none         原样训练
    class_weight LR: class_weight="balanced"；XGBoost/MLP: fit(sample_weight=balanced)
    ROS          imblearn Pipeline 内 RandomOverSampler，仅重采样训练数据
    SMOTE        imblearn Pipeline 内 SMOTE(k=5)，仅重采样训练数据
- 模型固定超参：LR(max_iter=1000)；XGB(300 树/depth 6/lr 0.1/hist)；MLP(64,64/
  max_iter=100/early_stopping/batch 1024)
- 已知披露：SMOTE 在 one-hot 编码空间插值会生成非 0/1 的合成哑变量取值，
  属该协议的已知局限（多数文献同款做法），记入报告与论文局限性。

幂等性：metrics.json 已存在的 run 自动跳过，脚本可反复执行以续跑。
单格异常不中断全局，状态记入 summary（失败实验可见，不静默丢弃）。

用法：python src/05_run_experiments.py
"""
import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from imblearn.over_sampling import RandomOverSampler, SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             f1_score, recall_score)
from sklearn.neural_network import MLPClassifier
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
HP = yaml.safe_load((ROOT / "configs/experiment_hyperparams.yaml").read_text(encoding="utf-8"))
PROC = ROOT / "data/processed"
RUNS = ROOT / "runs/experiments"
SEEDS = [0, 1, 2]
MODELS = ["LR", "XGBoost", "MLP"]
METHODS = ["none", "class_weight", "ROS", "SMOTE"]


def make_model(name, seed, method):
    p = HP[name]
    if name == "LR":
        kw = {"max_iter": p["max_iter"], "random_state": seed}
        if method == "class_weight":
            kw["class_weight"] = "balanced"
        return LogisticRegression(**kw)
    if name == "XGBoost":
        return XGBClassifier(objective=p["objective"], num_class=10,
                             n_estimators=p["n_estimators"], max_depth=p["max_depth"],
                             learning_rate=p["learning_rate"], tree_method=p["tree_method"],
                             random_state=seed, n_jobs=-1)
    if name == "MLP":
        return MLPClassifier(hidden_layer_sizes=tuple(p["hidden_layer_sizes"]),
                             max_iter=p["max_iter"], early_stopping=p["early_stopping"],
                             n_iter_no_change=p["n_iter_no_change"],
                             batch_size=p["batch_size"], random_state=seed)
    raise ValueError(name)


def run_one(model_name, method, seed, Xs, ys, classes):
    run_id = f"{model_name}__{method}__seed{seed}"
    out_dir = RUNS / run_id
    metrics_path = out_dir / "metrics.json"
    if metrics_path.exists():
        return run_id, "cached", json.loads(metrics_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = {"model": model_name, "method": method, "seed": seed,
           "hyperparams_source": "configs/experiment_hyperparams.yaml",
           "hyperparams": HP[model_name],
           "smote_k_neighbors": HP["SMOTE"]["k_neighbors"] if method == "SMOTE" else None,
           "data": "data/processed/*.parquet (02_preprocess.py, seed 42)"}
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False),
                                         encoding="utf-8")

    model = make_model(model_name, seed, method)
    if method == "ROS":
        pipe = ImbPipeline([("sampler", RandomOverSampler(random_state=seed)), ("model", model)])
    elif method == "SMOTE":
        pipe = ImbPipeline([("sampler", SMOTE(random_state=seed)), ("model", model)])
    else:
        pipe = ImbPipeline([("model", model)])

    fit_kw = {}
    if method == "class_weight":
        w = compute_sample_weight("balanced", ys["train"])
        fit_kw["model__sample_weight"] = w

    t0 = time.perf_counter()
    pipe.fit(Xs["train"], ys["train"], **fit_kw)
    fit_s = time.perf_counter() - t0
    n_train_after = None
    if method in ("ROS", "SMOTE"):
        sampler = pipe.named_steps["sampler"]
        idx = getattr(sampler, "sample_indices_", None)
        if idx is not None:
            n_train_after = int(len(idx))
        else:
            # SMOTE 不暴露 sample_indices_：auto 策略将每个少数类补至多数类规模
            n_train_after = int(len(classes) * np.bincount(ys["train"]).max())

    t0 = time.perf_counter()
    pred_test = pipe.predict(Xs["test"])
    infer_s = time.perf_counter() - t0
    pred_valid = pipe.predict(Xs["valid"])

    model_bytes = len(pickle.dumps(pipe))

    metrics = {
        "run_id": run_id,
        "valid": {
            "macro_f1": round(float(f1_score(ys["valid"], pred_valid, average="macro")), 4),
            "balanced_acc": round(float(balanced_accuracy_score(ys["valid"], pred_valid)), 4),
            "accuracy": round(float(accuracy_score(ys["valid"], pred_valid)), 4),
        },
        "test": {
            "macro_f1": round(float(f1_score(ys["test"], pred_test, average="macro")), 4),
            "balanced_acc": round(float(balanced_accuracy_score(ys["test"], pred_test)), 4),
            "accuracy": round(float(accuracy_score(ys["test"], pred_test)), 4),
        },
        "test_recall_per_class": {cls: round(float(r), 4) for cls, r in zip(
            classes, recall_score(ys["test"], pred_test, average=None,
                                  labels=range(len(classes)), zero_division=0))},
        "fit_s": round(fit_s, 1),
        "infer_test_s": round(infer_s, 3),
        "model_pickle_bytes": model_bytes,
        "n_train_after_resample": n_train_after if n_train_after is not None else int(len(Xs["train"])),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_id, "ok", metrics


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    Xs, ys = {}, {}
    for split in ("train", "valid", "test"):
        df = pd.read_parquet(PROC / f"{split}.parquet")
        Xs[split] = df.drop(columns=["attack_cat", "label"])
        ys[split] = df["attack_cat"]
    classes = sorted(ys["train"].unique())
    code = {c: i for i, c in enumerate(classes)}
    ys = {k: v.map(code).astype(int) for k, v in ys.items()}

    rows = []
    for model_name in MODELS:
        for method in METHODS:
            for seed in SEEDS:
                run_id = f"{model_name}__{method}__seed{seed}"
                try:
                    _, status, m = run_one(model_name, method, seed, Xs, ys, classes)
                    rows.append({"run_id": run_id, "status": status,
                                 "test_macro_f1": m["test"]["macro_f1"],
                                 "test_balanced_acc": m["test"]["balanced_acc"],
                                 "test_accuracy": m["test"]["accuracy"],
                                 "fit_s": m["fit_s"], "model_pickle_bytes": m["model_pickle_bytes"]})
                    print(f"[{status}] {run_id}: macroF1={m['test']['macro_f1']} "
                          f"balAcc={m['test']['balanced_acc']} fit={m['fit_s']}s", flush=True)
                except Exception as exc:  # 单格失败不拖垮全局，留痕不静默
                    rows.append({"run_id": run_id, "status": f"FAILED: {exc}",
                                 "test_macro_f1": None, "test_balanced_acc": None,
                                 "test_accuracy": None, "fit_s": None,
                                 "model_pickle_bytes": None})
                    print(f"[FAILED] {run_id}: {exc}", flush=True)
                pd.DataFrame(rows).to_csv(RUNS / "summary_progress.csv",
                                          index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(rows)
    summary.to_csv(RUNS / "summary.csv", index=False, encoding="utf-8-sig")
    ok = summary[summary.status.isin(["ok", "cached"])]
    print(f"\n完成 {len(ok)}/{len(summary)} 组；失败 {len(summary) - len(ok)} 组")
    pivot = ok.assign(model=ok.run_id.str.split("__").str[0],
                      method=ok.run_id.str.split("__").str[1]) \
        .groupby(["model", "method"]).test_macro_f1.mean().unstack().round(4)
    print("\n测试集 Macro-F1 均值（3 种子）：")
    print(pivot.to_string())


if __name__ == "__main__":
    main()
