# 证据链索引（EVIDENCE CHAIN）

> 本文件是论文《面向类别不平衡的网络入侵检测方法比较与轻量化改进研究》的**证据链总索引**：
> 论文中每一个可检验主张，都能沿"主张 → 报告 → 底层数据(CSV) → 生成脚本"四层溯源。
> 治理记录（三轮独立对抗审计）见 `reports/redteam/`。

## 溯源原则

1. **先冻结、后运行**：全部超参与协议在看到任何结果之前冻结
   （`configs/experiment_hyperparams.yaml`、各脚本 docstring 内预注册、
   `reports/week6/preregistration_rank_stability.md`）。
2. **脚本单一来源**：每个数字由 `src/` 中唯一脚本生成，落盘 CSV 后由报告引用；
   报告中的数字均可从对应 CSV 重算复原（已由独立审计逐格验证）。
3. **runs/ 不入 git，reports/ 入库**：原始运行产物保存在本地 `runs/`（体积大），
   其全部关键 CSV/报告副本入版本库 `reports/`；两者内容一致。
4. **官方测试集冻结**：`data/raw/UNSW_NB15_testing-set.csv` 全程只做 transform，
   不参与任何拟合、选型、调参（脚本层断言）。

## 证据链映射表

| # | 论文主张（章节） | 报告（入库） | 底层数据（入库） | 生成脚本 |
|---|---|---|---|---|
| E1 | 数据真实性指纹；类别分布 431:1（§3.1-3.3） | `reports/week1/eda_report.md`、`SHA256SUMS.txt`、`class_counts.csv` | `class_counts.csv` | `src/01_eda.py` |
| E2 | 防泄漏预处理与划分（§4.2） | `reports/week2/preprocess_report.md`、`preprocess_config.json` | —（划分产物 data/processed/） | `src/02_preprocess.py` |
| E3 | LR/XGBoost 基线（§4.2） | `reports/week2/baseline_metrics.csv`、`baseline_config.json` | 同左 | `src/03_baseline.py` |
| E4 | 划分重叠审计：验证集 47.0%/测试集 9.9%（§3.5） | `reports/week2/overlap_report.md` | —（哈希审计，报告含全表） | `src/04_split_overlap_audit.py` |
| E5 | 36 组主实验：表 5-1/5-2/5-3/5-4 全部数字 | `reports/week3/stability_macroF1.csv`、`stability_balanced_acc.csv`、`recall_per_class_mean.csv`、`stability_cost.csv`、`summary_full.csv`、`run_log.txt` | 同左（即底层） | `src/05_run_experiments.py` + `src/06_analyze_week3.py` |
| E6 | 误差归因 83–84%/7.3–8.6%/8.0–9.3%（§6.2，表 6-1） | `reports/week4/error_summary.md`、`error_cases.csv.gz`（逐条含行哈希）、`selection.json` | `error_cases.csv.gz` | `src/07_error_analysis.py` |
| E7 | 3 种子归因区间（表 6-1 括号） | `reports/week6/attribution_3seeds.md`、`attribution_3seeds.csv` | 同左 | `src/14_attribution_summary.py` |
| E8 | 轻量化 v1：K*=32、2.52×、体积+2%（§5.6） | `reports/week5/sweep.csv`、`final_metrics.csv`、`recall_summary.csv`、`feature_importance.csv`、`report.md` | 同左 | `src/08_lightweight.py` |
| E9 | 预注册 τ 检验：LR +1.0 / XGB −1.0 / MLP +0.333（§5.2） | `reports/week6/preregistration_rank_stability.md`、`rank_stability.md`、`rank_stability.csv` | 同左 CSV | `src/09_rank_stability.py` |
| E10 | 阈值移动 v1：0.5483/0.5295（§5.5） | `reports/week6/threshold_moving.md`、`threshold_results.csv` | 同左 CSV | `src/10_threshold_moving.py` |
| E11 | SMOTE 取整敏感性：MF1 差 0.002、DoS −0.05（§5.7） | `reports/week6/smote_rounding.md`、`smote_rounding_results.csv` | 同左 CSV | `src/11_smote_rounding.py` |
| E12 | none 重叠行对照：44.2% = 整体 1.9×（§6.3） | `reports/week6/none_overlap_control.md`（数字自足） | — | `src/12_none_overlap_control.py` |
| E13 | 不平衡衰减 v1：p=0.25 降幅 <0.02（§5.7） | `reports/week6/imbalance_decay.md`、`decay_results.csv` | 同左 CSV | `src/13_imbalance_decay.py` |
| E14 | **方差补测 v2**：阈值移动 0.5436±0.0063（最差种子 0.5367）；衰减 p≥0.25 稳健、p=0.10 不稳健（§5.5-5.7 v2 口径） | `reports/week6/threshold_moving_v2.md`、`imbalance_decay_v2.md`、`reports/week5/variance_recheck.md` | `reports/week6/threshold_results_v2.csv`、`decay_results_v2.csv`、`reports/week5_v2/final_metrics_v2.csv`、`recall_per_class_per_seed_v2.csv`、`ranking_overlap.csv`、`feature_importance_seed{0,1,2}.csv` | `src/resplit.py` + `src/08/10/13 --v2` |
| E15 | SMOTE 衰减曲线（T14 补测，§5.7） | `reports/week6/imbalance_decay_v2.md`（SMOTE 列） | `decay_results_v2.csv`（smote 12 格） | `src/13_imbalance_decay.py --v2` |

## 治理记录（独立对抗审计）

三轮红队 + 一次专项复攻，全部问题闭环留痕于 `reports/redteam/`：

- `W4-W5_红队一二轮台账.md`：第一/二轮（S1-S10、K1-K8、R1-R3）
- `W7-W8_红队三轮与v2复攻台账.md`：第三轮（T1-T14）+ v2 复攻
  + v2 复攻记录。
- 关键战果：数字张冠李戴、测试集选型违规、"稳健"过度概括、确定性配置种子坍缩、
  阈值移动游离于研究问题叙事外——全部修复并经复攻验证。

## 复现指南

```bash
# 环境：Windows 11 / Python 3.13.15（完整锁定见 requirements.lock.txt）
.venv\Scripts\activate
python src/01_eda.py                      # E1
python src/02_preprocess.py               # E2
python src/03_baseline.py                 # E3
python src/04_split_overlap_audit.py      # E4
python src/05_run_experiments.py          # E5（36 组，幂等可续跑）
python src/06_analyze_week3.py            # E5 汇总
python src/07_error_analysis.py           # E6（v2 口径）
python src/08_lightweight.py              # E8
python src/09_rank_stability.py           # E9
python src/10_threshold_moving.py         # E10
python src/11_smote_rounding.py           # E11
python src/12_none_overlap_control.py     # E12
python src/13_imbalance_decay.py          # E13
python src/14_attribution_summary.py      # E7
# 方差补测（不覆盖 v1 产物，写 *_v2 目录）
python src/08_lightweight.py --v2         # E14
python src/10_threshold_moving.py --v2    # E14
python src/13_imbalance_decay.py --v2     # E14+E15
```

数据获取：UNSW-NB15 官方划分集（`data/raw/`，核验与指纹见 E1）。
