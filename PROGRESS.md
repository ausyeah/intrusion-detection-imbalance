# 面向类别不平衡的网络入侵检测方法比较与轻量化改进研究

本科毕业设计 · 基于 UNSW-NB15 的实验型研究。诚实定位：**不是新算法，是统一实验协议下的系统比较 + 轻量化改进**。

## 三个研究问题

1. 类别不平衡会让哪些攻击类别被漏检？
2. class weight、随机过采样和 SMOTE 哪种方法更有效？
3. 检测性能、少数类 Recall 和推理时间如何权衡？

## 目录结构

```
毕设论文/
├── data/
│   ├── raw/          # 原始数据，只读不改，不入 git
│   └── processed/    # 清洗后的数据，可再生成，不入 git
├── src/              # 按编号执行的脚本：01_eda.py, 02_preprocess.py, ...
├── configs/          # 实验配置（路径、种子、超参数）
├── runs/             # 每次实验的报告/日志/指标，本地保存，关键结论手动入库
├── figures/          # 论文用图，入 git
├── paper/            # 论文、流程文档
└── README.md
```

## 环境

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 数据

UNSW-NB15 官方划分集（来源、许可证与引用要求见 [data/README.md](data/README.md)）。
  
下载后放到 `data/raw/`：

- `UNSW_NB15_training-set.csv`（175,341 行）
- `UNSW_NB15_testing-set.csv`（82,332 行）

## 第 1 周检查清单（06-16 ~ 06-22 完成，审计修复后）

- [x] 项目目录 + Git 仓库
- [x] Python 虚拟环境 + 依赖清单（精确版本锁定 requirements.lock.txt）
- [x] 数据集来源和许可证记录（data/README.md，含官方渠道核对待办）
- [x] 下载 UNSW-NB15 划分集到 data/raw/（行数 + SHA-256 指纹核验，见 reports/week1/）
- [x] `python src/01_eda.py` → 字段说明、类别分布图、不平衡比例（约 431:1）、完整性检查
- [x] 原始数据确认未做任何修改

## 第 2 周检查清单（06-23 ~ 06-29 完成）

- [x] 02_preprocess.py：先划分（140,272/35,069/82,332）后拟合，编码器与标准化器仅训练划分 fit
- [x] 03_baseline.py：LR / XGBoost / XGBoost+类别权重（测试集 Macro-F1 0.339 / 0.510 / 0.512）
- [x] 第一张混淆矩阵 figures/confusion_matrix_baseline.png
- [x] 实验表格 runs/baseline/metrics.csv（单种子基线，第 3 周扩 3 种子 × 4 方法）
- [x] 证据入库：reports/week2/（基线指标与配置、预处理报告、划分重叠审计）
- [x] 04_split_overlap_audit.py：训练/验证/测试特征向量重叠与标签冲突量化（论文局限性素材）

## 第 3 周检查清单（06-30 ~ 07-06 完成）

- [x] 05_run_experiments.py：3 模型 × 4 方法 × 3 种子 = 36 组，全部成功（0 失败）
- [x] 06_analyze_week3.py：稳定性表（均值±标准差）、每类 Recall 表、方法对比图
- [x] 证据入库 reports/week3/（稳定性×3（含验证集）、每类 Recall、开销表、汇总表、报告、运行日志）
- [x] 复审修复：ROS 模型体积口径披露（含采样索引）、SMOTE 训练后规模修正（≈448,000）、36 格 config 协议一致性审计通过
- [x] 关键发现（红队复审后修订）：Balanced Acc 口径下类别权重在 XGB（0.6549）与 MLP（0.6089）最优，LR 上 SMOTE 最优（0.5637，类别权重 0.5534）；Macro-F1 口径下 LR 最优 SMOTE、MLP 最优 ROS、XGB 最优类别权重。SMOTE 对 XGB 的 Macro-F1 最低（0.5041）但其 Balanced Acc（0.6035）与 DoS Recall（0.4878 对类别权重 0.171）更高——结论依赖指标口径，不可单口径概括

## 第 4 周检查清单（07-07 ~ 07-13 完成，v2 红队两轮复审后）

- [x] 07_error_analysis.py v2：按验证集选型（三模型一致 SMOTE——测试集不参与选型）+ 最优配置混淆矩阵 figures/confusion_matrix_best.png
- [x] 错误案例导出 reports/week4/error_cases.csv.gz（81,387 条，含行哈希与噪声归因）
- [x] 确定性一致性校验：三模型全部错误行「测试预测==训练副本预测」不一致数 = 0
- [x] 纯模型体积（v2 选型口径）：LR+SMOTE 0.02MB / MLP+SMOTE 0.43MB / XGB+SMOTE 8.59MB
- [x] 三个研究问题的数据支撑回答 reports/week4/研究问题回答.md（v2，红队两轮复审后）
- [x] 红队两轮：首轮 3 critical（数字张冠李戴/过度概括/测试集选型）+ 复攻与方法审稿人二轮 11 项（v1 残留清理、MLP 单种子限制披露、开销倍数修正），台账 reports/redteam/

## 第 5 周检查清单（07-14 ~ 07-20 完成）

- [x] 08_lightweight.py：类别权重 XGBoost + 增益重要性筛选，验证集选 K*=32（测试集不进入扫描阶段）
- [x] 终评（测试集，3 种子）：Macro-F1 0.5087 vs 0.5123、Balanced Acc 0.6605 vs 0.6549（BA 口径精简版更高；主指标 Macro-F1 微降，std=0 为确定性（3 种子坍缩），差异显著性无法评估——按「权衡」而非「改进」表述，红队三轮 T3）、训练加速 2.52×
- [x] 关键发现：Analysis Recall 翻倍（0.058→0.120）、Worms +0.045、DoS +0.026，Backdoor -0.057；体积不降反增 2%（XGBoost 体积由树结构主导——负结果如实报告）
- [x] 证据入库 reports/week5/（K 扫描、终评、每类 Recall、特征重要性、报告）
- [x] 方差补测 v2（第 8 周，红队三轮后用户决策）：per-seed 重切验证集 + 逐种子重排序——top32 0.5081±0.0055 对 full194 0.5103±0.0028（主指标差异 −0.0022 在切分方差内，「权衡」表述获得方差证据）；特征排序 top-32 Jaccard 0.83–0.94（「单次排序未检验」局限闭环）；加速 2.67×（fit 为 wall-clock 口径、批间约 2% 波动）、体积仍增（负结果复现）；报告 reports/week5/variance_recheck.md

## 第 6 周计划（07-21 ~ 07-27：结论稳健性周）

- [x] A 预注册 τ 检验（回溯性预注册已声明）：三组平均 τ = 0.111 / 0.278 / 0.111 均低于预注册 2/3 稳定线（n=4 描述性检验，无 p 值宣称）；但异质性显著——LR 选型分割 τ=+1.0 完全稳定、XGB τ=-1.0 完全反转、MLP +0.333 弱正，结论应表述为「排序稳定性高度依赖模型」，而非「全部排序不稳定」（红队三轮 A2-3 修订）
- [x] B 阈值移动对照（S7 已闭环）：none+阈值移动(Macro-F1 目标)达 0.5483/少数类 0.483——为全项目最高 Macro-F1，超过全部 12 个模型×方法格的 3 种子均值（最高 XGBoost+类别权重 0.5123）与全部 36 个单次运行值（最高 XGBoost+ROS seed0 0.5146；cw+阈值移动 3 种子均值 0.5295），零重训练；阈值移动是验证集调参的后处理，与训练期不平衡处理机制不同，比较时须声明（RQ 回答 v3 已纳入）；诚实记录 cw 以少数类为目标调阈值的迁移失败案例（测试 0.672→0.452）
- [x] C 哑变量取整敏感性：SMOTE 合成样本 one-hot 列取整，XGB 格子 3 种子，检验插值伪影是否翻转结论
- [x] D 不平衡比例敏感性：少数类降采样 50%/25%/10%，none 与类别权重（XGBoost）衰减曲线；Macro-F1 仅在 p≥0.25 口径判稳健（p=0.10 none 降幅 0.0417 已超 <0.02 准则），少数类宏 Recall 大幅流失（p=0.25：cw 0.672→0.535；p=0.10：cw 0.355、none 0.160）——「稳健」仅限 Macro-F1 口径，不覆盖少数类召回与 SMOTE（红队三轮 A1-1 修订）
- [x] E① 05 脚本改读 configs/experiment_hyperparams.yaml（36/36 缓存命中、结果逐格一致）
- [x] E② 误差归因 3 种子区间版（K5 闭环：novel 82.8–84.4%/conflict 7.3–8.6%/overlap 8.0–9.3%，种子间最大波动 0.6pp）
- [x] E③ none 重叠行错误率对照（S4 闭环：44.2% 为整体 1.9 倍——高错误率主体是重叠行自身难度，类别权重增量居次）
- [x] ④ 第三轮复攻抽查（第 7 周：3 独立攻击者 + 交叉审视，14 项裁决→12 项文档修复，台账 reports/redteam/W7-W8_红队三轮与v2复攻台账.md；K1/K3/K4 复攻一并闭环）
- [x] ⑤ 封板后方差补测 T4/T14（第 8 周用户决策，v2 协议 src/resplit.py：每种子重切官方训练池、编码器/标准化器逐种子仅 fit 训练划分、官方测试集冻结只 transform、降采样 RNG 随种子）——36/36 成功 0 回退：衰减 Macro-F1 在 p≥0.25 的稳健性于真实方差下成立（none 降 0.0065、cw 降 0.0084），p=0.10 不稳健（降 0.028–0.054）；SMOTE 衰减曲线补齐（T14，少数类宏 Recall 恒介于 none 与 cw 之间）；阈值移动 v2 none+macro_f1 moved **0.5436±0.0063**（最差种子 0.5367 仍超全部格点均值 0.5123 与单次运行最高 0.5146）；轻量化 v2 top32−full=−0.0022，在切分方差 ±0.005 内。报告 reports/week6/{imbalance_decay_v2,threshold_moving_v2}.md、reports/week5/variance_recheck.md、figures/imbalance_decay_v2.png
- [ ] 可选：CIC-IDS2017 外部验证（仅最优组合迁移，A–E 完成且时间富余才启动）
- [x] 第 6 周实验全部封板（外部验证未做，按砍项原则放弃；封板后仅按用户决策补 T4/T14 方差补测，v1 产物未动）→ 第 9-11 周论文写作

## 硬性纪律（每周都适用）

1. **先划分，后处理**：SMOTE/过采样/标准化只允许拟合训练集，测试集只做 transform。
2. 测试集不参与任何调参。
3. 主指标：Macro-F1、Balanced Accuracy、每类 Recall、混淆矩阵、推理时间、模型大小；Accuracy 只作辅助。
4. 正式实验至少 3 个随机种子（seeds = 0, 1, 2）。
5. 每次实验保存配置和日志到 runs/。
6. 不把"类别权重 + SMOTE"包装成原创算法。
