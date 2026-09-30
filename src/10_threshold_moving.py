"""第 6 周 B 项：阈值移动对照（红队 S7 补全）——零重训练开销的少数类挽救路线。

协议（本 docstring 即预注册，运行前冻结）：
- 对象：XGBoost 的 none 与 class_weight 两配置（超参取 configs/experiment_hyperparams.yaml，
  与第 3 周完全同参，make_model 从 05 导入保证单一协议来源），seeds [0,1,2]。
- 方法：预测概率 P(k|x) 上做每类乘性权重 w_k，预测改为 argmax_k w_k·P(k|x)；
  权重网格 {0.5, 0.6, …, 2.5}，坐标上升（类顺序固定，2 轮），**只在验证集上搜索**。
- 双目标分别搜索并分别报告（不得混选）：目标 a = 验证集 Macro-F1；
  目标 b = 验证集少数类宏 Recall（少数类 = Analysis/Backdoor/Shellcode/Worms，
  与预注册 rank_stability 同一定义）。
- 测试集：每个「配置 × 种子 × 目标」只用调好的权重评估一次；同时报告未移动的基线
  测试指标作为对照。
- 期望回应的问题（红队 S7）：阈值移动这一零重采样开销路线，能否达到类别权重的
  少数类挽救效果——直接决定 RQ3「性价比」结论的对照完整性。

产出：runs/threshold_moving/threshold_results.csv、reports/week6/threshold_moving.md
用法：python src/10_threshold_moving.py

--v2 方差补测（第 8 周，红队三轮 A1-3/用户决策 T4；v1 行为与产物不变）：
- 数据：resplit.make_splits(seed) 每种子重切官方训练池（80/20 分层），编码器与
  标准化器逐种子仅 fit 各自训练划分；官方测试集冻结只 transform。
- 动机：XGBoost none/类别权重确定性 + 固定切分 → v1 三种子完全相同（A1-3）。
  per-seed 重切使「阈值搜索所用的验证集」与「训练集」都随种子变化，从而暴露
  阈值选择敏感性的真实方差——0.5483（全项目最高 Macro-F1）换一个验证集还成不
  成立，由本补测直接回答。
- 其余协议（网格/坐标上升/双目标/测试集每设置只评一次）与 v1 逐字一致。
- 产出：runs/threshold_moving_v2/、reports/week6/threshold_moving_v2.md；v1 目录不写。
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (balanced_accuracy_score, f1_score, recall_score)
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
RUNS = ROOT / "runs/threshold_moving"
OUT = ROOT / "reports/week6"
SEEDS = [0, 1, 2]
GRID = [round(0.1 * i, 1) for i in range(5, 26)]  # 0.5 .. 2.5
MINORITY = ["Analysis", "Backdoor", "Shellcode", "Worms"]


def load_module05():
    spec = importlib.util.spec_from_file_location(
        "exp05", ROOT / "src/05_run_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_w(proba, w):
    return np.argmax(proba * w[None, :], axis=1)


def coord_ascent(proba, y, n_classes, objective, passes=2):
    w = np.ones(n_classes)

    def score(wv):
        return objective(apply_w(proba, wv), y)

    best = score(w)
    for _ in range(passes):
        for k in range(n_classes):
            cand_best, cand_w = best, w[k]
            for g in GRID:
                w[k] = g
                s = score(w)
                if s > best + 1e-12:
                    best, cand_w = s, g
            w[k] = cand_w
    return w, best


def metrics(y_true, pred, classes):
    return {
        "macro_f1": round(float(f1_score(y_true, pred, average="macro")), 4),
        "balanced_acc": round(float(balanced_accuracy_score(y_true, pred)), 4),
        "minority_recall": round(float(np.mean(
            recall_score(y_true, pred, average=None, labels=range(len(classes)),
                         zero_division=0)[[classes.index(c) for c in MINORITY]])), 4),
    }


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    mod = load_module05()

    Xs, ys = {}, {}
    for split in ("train", "valid", "test"):
        df = pd.read_parquet(PROC / f"{split}.parquet")
        Xs[split] = df.drop(columns=["attack_cat", "label"])
        ys[split] = df["attack_cat"]
    classes = sorted(ys["train"].unique())
    code = {c: i for i, c in enumerate(classes)}
    ys_enc = {k: v.map(code).astype(int) for k, v in ys.items()}
    minority_idx = [classes.index(c) for c in MINORITY]

    def obj_macro(y_true, pred):
        return f1_score(y_true, pred, average="macro")

    def obj_minority(y_true, pred):
        r = recall_score(y_true, pred, average=None, labels=range(len(classes)),
                         zero_division=0)
        return float(np.mean(r[minority_idx]))

    rows = []
    for config in ("none", "class_weight"):
        for seed in SEEDS:
            model = mod.make_model("XGBoost", seed, config)
            kw = {}
            if config == "class_weight":
                kw["sample_weight"] = compute_sample_weight("balanced", ys_enc["train"])
            model.fit(Xs["train"], ys_enc["train"], **kw)
            proba_valid = model.predict_proba(Xs["valid"])
            proba_test = model.predict_proba(Xs["test"])
            base_valid_pred = np.argmax(proba_valid, axis=1)
            base_test_pred = np.argmax(proba_test, axis=1)

            for obj_name, obj in [("macro_f1", obj_macro), ("minority_recall", obj_minority)]:
                w, valid_obj = coord_ascent(proba_valid, ys_enc["valid"].values,
                                            len(classes), obj)
                moved_test_pred = apply_w(proba_test, w)
                base_m = metrics(ys_enc["test"], base_test_pred, classes)
                moved_m = metrics(ys_enc["test"], moved_test_pred, classes)
                rows.append({
                    "config": config, "seed": seed, "objective": obj_name,
                    "n_weights_changed": int((w != 1).sum()),
                    "valid_obj_tuned": round(float(valid_obj), 4),
                    "valid_obj_baseline": round(float(obj(ys_enc["valid"], base_valid_pred)), 4),
                    "test_macro_f1_base": base_m["macro_f1"],
                    "test_macro_f1_moved": moved_m["macro_f1"],
                    "test_balanced_acc_base": base_m["balanced_acc"],
                    "test_balanced_acc_moved": moved_m["balanced_acc"],
                    "test_minority_recall_base": base_m["minority_recall"],
                    "test_minority_recall_moved": moved_m["minority_recall"],
                    "weights": json.dumps([round(float(x), 2) for x in w]),
                })
                print(f"[done] {config} seed{seed} {obj_name}: "
                      f"mF1 {base_m['macro_f1']}→{moved_m['macro_f1']} "
                      f"minR {base_m['minority_recall']}→{moved_m['minority_recall']}",
                      flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(RUNS / "threshold_results.csv", index=False, encoding="utf-8-sig")

    agg = res.groupby(["config", "objective"])[
        ["test_macro_f1_base", "test_macro_f1_moved",
         "test_minority_recall_base", "test_minority_recall_moved",
         "test_balanced_acc_base", "test_balanced_acc_moved"]].mean().round(4)

    lines = ["# 阈值移动对照（红队 S7 补全）", "",
             "- 协议：XGBoost none/类别权重两配置（同参），验证集每类乘性权重坐标上升"
             "（网格 0.5–2.5，2 轮），双目标分别搜索；测试集每个设置只评估一次；3 种子。",
             "- 诚实预注：本脚本 docstring 即预注册，运行前冻结；测试集基线指标为同批"
             "重训模型的一次评估，用于与移动后对照。", "",
             "## 测试集对照（3 种子均值）", "", "```", agg.to_string(), "```", "",
             "## 逐配置×种子明细", "", "```", res.to_string(index=False), "```", "",
             "- 零重训练开销：阈值移动不重训模型（复用已训模型的后处理），推理阶段仅"
             "增加一次逐类乘法。"]
    (OUT / "threshold_moving.md").write_text("\n".join(lines), encoding="utf-8")
    print(agg.to_string())
    print(f"\n[OK] -> {RUNS} 与 {OUT / 'threshold_moving.md'}")


def run_v2():
    """v2 方差补测：per-seed 重切验证集，其余协议与 v1 逐字一致。"""
    import resplit  # noqa: 与本脚本同目录

    run_dir = ROOT / "runs/threshold_moving_v2"
    run_dir.mkdir(parents=True, exist_ok=True)
    mod = load_module05()

    rows = []
    classes = None
    code = None
    minority_idx = None

    def obj_macro(y_true, pred):
        return f1_score(y_true, pred, average="macro")

    def obj_minority(y_true, pred):
        r = recall_score(y_true, pred, average=None, labels=range(len(classes)),
                         zero_division=0)
        return float(np.mean(r[minority_idx]))

    for seed in SEEDS:
        splits = resplit.make_splits(seed)
        Xs = {k: splits[k].drop(columns=["attack_cat", "label"]) for k in splits}
        ys_raw = {k: splits[k]["attack_cat"] for k in splits}
        if classes is None:
            classes = sorted(ys_raw["train"].unique())
            code = {c: i for i, c in enumerate(classes)}
            minority_idx = [classes.index(c) for c in MINORITY]
        ys_enc = {k: v.map(code).astype(int) for k, v in ys_raw.items()}

        for config in ("none", "class_weight"):
            model = mod.make_model("XGBoost", seed, config)
            kw = {}
            if config == "class_weight":
                kw["sample_weight"] = compute_sample_weight("balanced", ys_enc["train"])
            model.fit(Xs["train"], ys_enc["train"], **kw)
            proba_valid = model.predict_proba(Xs["valid"])
            proba_test = model.predict_proba(Xs["test"])
            base_valid_pred = np.argmax(proba_valid, axis=1)
            base_test_pred = np.argmax(proba_test, axis=1)

            for obj_name, obj in [("macro_f1", obj_macro), ("minority_recall", obj_minority)]:
                w, valid_obj = coord_ascent(proba_valid, ys_enc["valid"].values,
                                            len(classes), obj)
                moved_test_pred = apply_w(proba_test, w)
                base_m = metrics(ys_enc["test"], base_test_pred, classes)
                moved_m = metrics(ys_enc["test"], moved_test_pred, classes)
                rows.append({
                    "config": config, "seed": seed, "objective": obj_name,
                    "n_weights_changed": int((w != 1).sum()),
                    "valid_obj_tuned": round(float(valid_obj), 4),
                    "valid_obj_baseline": round(float(obj(ys_enc["valid"], base_valid_pred)), 4),
                    "test_macro_f1_base": base_m["macro_f1"],
                    "test_macro_f1_moved": moved_m["macro_f1"],
                    "test_balanced_acc_base": base_m["balanced_acc"],
                    "test_balanced_acc_moved": moved_m["balanced_acc"],
                    "test_minority_recall_base": base_m["minority_recall"],
                    "test_minority_recall_moved": moved_m["minority_recall"],
                    "weights": json.dumps([round(float(x), 2) for x in w]),
                })
                print(f"[v2 done] {config} seed{seed} {obj_name}: "
                      f"mF1 {base_m['macro_f1']}→{moved_m['macro_f1']} "
                      f"minR {base_m['minority_recall']}→{moved_m['minority_recall']}",
                      flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(run_dir / "threshold_results_v2.csv", index=False, encoding="utf-8-sig")

    agg = res.groupby(["config", "objective"])[
        ["test_macro_f1_base", "test_macro_f1_moved",
         "test_minority_recall_base", "test_minority_recall_moved",
         "test_balanced_acc_base", "test_balanced_acc_moved"]].mean().round(4)
    std_moved = res.groupby(["config", "objective"]).test_macro_f1_moved.std().round(4)

    # v1 对照（直接读 v1 CSV，不手填）
    v1_path = ROOT / "runs/threshold_moving/threshold_results.csv"
    v1_note = ""
    if v1_path.exists():
        v1 = pd.read_csv(v1_path)
        v1_none = v1[(v1.config == "none") & (v1.objective == "macro_f1")]
        v1_note = (f"- v1（固定 seed 42 切分）对照：none+macro_f1 目标 test_macro_f1_moved "
                   f"={v1_none.test_macro_f1_moved.iloc[0]}（3 种子完全相同，std=0）；"
                   f"v2 同格 3 种子 std={std_moved.get(('none', 'macro_f1'), 'NA')}——"
                   "差异即切分敏感性的真实度量")

    lines = ["# 阈值移动对照 v2（方差补测，第 8 周）", "",
             "- 协议：与 v1 逐字一致（网格 0.5–2.5、坐标上升 2 轮、双目标分别搜索、"
             "测试集每设置只评估一次）；唯一变更 = resplit.make_splits(seed) 每种子重切"
             "官方训练池（编码器/标准化器逐种子仅 fit 训练划分，官方测试集冻结只 transform）。",
             "- 动机（红队三轮 A1-3）：确定性模型 + 固定切分使 v1 三种子坍缩；v2 暴露"
             "阈值选择对验证集切分的真实敏感性——0.5483 的结论稳健性由此直接检验。", "",
             "## 测试集对照（3 种子均值）", "", "```", agg.to_string(), "```", "",
             "## 逐配置×种子明细", "", "```", res.to_string(index=False), "```", "",
             v1_note or "- （v1 CSV 缺失，未附对照）",
             "- 零重训练开销结论不变：阈值移动不重训模型，推理阶段仅增加一次逐类乘法。", ""]
    (ROOT / "reports/week6/threshold_moving_v2.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(agg.to_string())
    print(f"\n[OK v2] -> {run_dir} 与 reports/week6/threshold_moving_v2.md")


if __name__ == "__main__":
    if "--v2" in sys.argv:
        run_v2()
    else:
        main()
