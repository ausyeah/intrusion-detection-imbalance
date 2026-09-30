# 红队台账 2026-09-14 submission

## 本轮面板

- `skeptic-reviewer`：攻击方法有效性、阈值校准和结论外推；verdict：`fail`。
- `stats-auditor`：攻击数据独立性、数字/成本证据和数据版本；verdict：`fail`。
- `defense-examiner`：模拟答辩追问，检查结论是否可定义、可证伪、可解释；verdict：`revise`。
- `integrity-redteam`（主代理只读交叉审计）：攻击来源、公开版本和引用/披露一致性；verdict：`revise`。

证据溯源：本台账只登记能在仓库文件中定位的攻击。没有做新实验；未验证的外部事实标为 `UNKNOWN` 或 `UNVERIFIED`。

## 问题裁决

| ID | 来源 | 严重度 | 问题摘要 | 证据 | 裁决 | 状态 | 修复/回应证据 |
|---|---|---:|---|---|---|---|---|
| S1 | skeptic / stats / defense | critical | 阈值校准在同一验证集上对 10 类权重做 0.5--2.5 网格、两轮坐标搜索；v2 只是重切验证集，仍没有独立校准集或嵌套验证，因此 `0.5436±0.0063` 存在选择乐观偏差，不能直接解释为可迁移的全局最优。 | `src/10_threshold_moving.py` 协议与 `paper/chapters/05_实验结果.md` §5.5；v2 报告中的验证集搜索结果 | RISK + TODO | open | 将结论限定为“在本数据集、该阈值搜索协议和已测组合内”；若要宣称泛化，补独立校准/嵌套验证。 |
| S2 | skeptic / stats | major | 36 组主矩阵使用同一固定 seed=42 划分；LR/XGBoost 的确定性格子三种子逐位相同，主矩阵均值±std 不表示切分不确定性，不能支持亚 0.003 差异的稳健优劣。v2 重切只覆盖阈值、衰减、轻量化。 | `paper/chapters/04_方法与实验设置.md` §4.5、`reports/week3/summary_full.csv`、`reports/week3/stability_macroF1.csv` | RISK + TODO | open | 主矩阵补做 per-seed 重切/组划分或 bootstrap；在此之前把主矩阵排序标为固定划分上的描述性结果。 |
| S3 | stats / skeptic | major | 训练-验证共享特征向量占验证行 47.0%，训练-测试共享占测试行 9.9%，且有冲突标签；没有去重/组划分反事实或按方法分层结果，论文“对所有方法对称、不改变相对比较”的句子是未经验证的假设。 | `paper/chapters/03_数据集与问题定义.md` §3.5、`reports/week2/overlap_report.md`、`paper/chapters/06_误差分析.md` §6.3、`paper/chapters/07_局限性.md` §7.1 | FIX（措辞） + TODO（实验） | open | 删除或改写“对称、不改变相对比较”；将排序明确限定为“含官方重复的固定协议”，去重/组划分列入实验计划。 |
| S4 | stats | major | `reports/week3/summary_full.csv` 的全部 SMOTE 行把 `n_train_after_resample` 记为 140272，实际训练规模约为 448000；成本表脚注虽披露缺陷，但证据链仍声称数字可由 CSV 复算。 | `reports/week3/summary_full.csv`；`paper/chapters/05_实验结果.md` §5.4；`reports/week3/stability_cost.csv` | FIX | open | 重新生成 SMOTE 行及下游汇总，或明确旧 CSV 不可作为复现实验输入，并加采样后规模断言。 |
| S5 | stats | major | 实际数据下载自 `Nir-J/ML-Projects` GitHub 镜像；官方副本 SHA 比对仍是待办，却在论文和证据索引中称“官方划分集”。行数/类别计数吻合不能证明逐字节等价。 | `data/README.md` §来源/版本核验；`reports/week1/eda_report.md` §0 | FIX 或 RISK | open | 获取官方副本并逐文件 SHA 比对；否则全文改称“该 GitHub 镜像版本”，并限定结论适用域。 |
| S6 | skeptic | major | 仅在 XGBoost 上做 SMOTE one-hot 取整改动；该敏感性结果不能覆盖 LR/MLP 的 SMOTE 排序和结论。 | `src/11_smote_rounding.py`；`paper/chapters/04_方法与实验设置.md` §4.4/§4.7；`paper/chapters/05_实验结果.md` §5.7 | RISK + TODO | open | 补 LR/MLP 取整或 SMOTENC 对照；否则明确“伪影稳健性仅在 XGBoost 配置上检验”。 |
| S7 | skeptic | major | 阈值移动只覆盖 XGBoost 的 none/class_weight，却在摘要和结论中使用“全项目最高 Macro-F1”；未测其余模型/处理方法与阈值组合，不能排除未测组合。 | `src/10_threshold_moving.py`；`paper/chapters/05_实验结果.md` §5.5；`paper/chapters/07_局限性.md` §7.3 | FIX（措辞） + TODO（实验） | open | 改为“在已测 XGBoost none/class_weight 与 36 个训练期格中最高”；或补齐组合。 |
| S8 | skeptic | major | “模型容量对本任务的影响大于不平衡处理方法选择”是因果/解释性表述，但三模型只有单组冻结超参，MLP 还有 max_iter=100 未收敛格，未对齐调参预算。 | `paper/chapters/04_方法与实验设置.md` §4.3；`configs/experiment_hyperparams.yaml`；`paper/chapters/05_实验结果.md` §5.1 | FIX（措辞） + TODO（实验） | open | 删除因果归因，改成“在本固定配置下模型间差异更大”；补方法×超参/收敛敏感性后再讨论容量。 |
| D1 | defense-examiner | major | “DoS 有效挽救/恢复”没有事前阈值：0.488 被称有效，而 0.267/0.177 的边界没有定义，属于不可证伪表述。 | `paper/chapters/05_实验结果.md` §5.3；`paper/chapters/08_结论.md` §8.1 | FIX | open | 改为报告相对 none/cw 的定量增幅、绝对 Recall 和代价，不使用未定义的“有效挽救”。 |
| D2 | defense-examiner | major | Kendall τ 的 n=4、三种子、固定划分和回溯性预注册使“高度依赖模型”只能是探索性描述；没有显著性或效应量。 | `reports/week6/preregistration_rank_stability.md`、`reports/week6/rank_stability.csv`、`paper/chapters/05_实验结果.md` §5.2 | RISK | open | 在结论中加“探索性/描述性”限定；未来补 bootstrap/效应量，不作统计显著性推断。 |
| D3 | defense-examiner | major | 单一 UNSW-NB15 且测试集 9.9% 重叠，不能否定跨数据集的“普适最优”；当前结论必须限于该协议。 | `paper/chapters/07_局限性.md` §7.1；`paper/chapters/05_实验结果.md` §5.2 | FIX（措辞） | open | 在摘要、结论、贡献和 README 统一加入“本数据集/本协议内”，撤回跨数据集暗示。 |
| I1 | integrity-redteam | major | 公开产物版本不一致：`paper/preprint/ChinaXiv预印本_第一版.md` 仍写“提交号 T202609.00118、DOI 待分配”，而 README/提交清单写已发布 DOI `10.12074/202609.00078`。读者无法确定哪个版本对应公开预印本和数字。 | `paper/preprint/ChinaXiv预印本_第一版.md` 文件头；`README.md` 成果公开段；`paper/preprint/ChinaXiv提交清单.md` | FIX | open | 统一提交号、DOI、发布日期和 PDF/MD 对应关系；若 MD 是历史版本，显式标注“未公开旧稿”，避免把它作为当前论文正文。 |
| I2 | integrity-redteam | major | 论文把“全部 17 条参考文献均已核对”和“据作者所知此前尚无……”作为强断言，但仓库只有核对记录/概述，没有逐条可审计的检索链接或系统检索范围；新颖性否定式表述不可由现有证据直接推出。 | `paper/参考文献核对记录.md`；`paper/chapters/02_相关工作.md` §2.3 | RISK + FIX（措辞） | open | 为每条引用保留可访问出处/检索日期；将“据作者所知尚无”改为限定性综述结论并说明检索范围。 |
| I3 | integrity-redteam | major | 数据许可证/官方来源表述超出当前证据：`data/README.md` 写“许可与引用”，但实际镜像来源、官方渠道待申请和许可证条款没有官方文件佐证。 | `data/README.md` §来源、版本核验、许可与引用；`reports/week1/eda_report.md` §0 | RISK | open | 核验官方数据页和镜像许可/再分发条件；在核验前避免把“引用要求”写成已确认的“许可义务”。 |

## 答辩追问清单

1. 阈值权重为何使用 0.5--2.5、为何两轮坐标上升；搜索自由度是多少，为什么没有独立校准集？
2. 验证集 47% 与训练共享特征向量时，如何证明方法排序没有被重复样本改变？
3. `0.5436±0.0063` 的标准差代表什么随机源；为什么不能把它解释为主矩阵的稳健性？
4. DoS Recall 何种绝对值或相对增幅才称“有效挽救”；这个阈值是否在看结果前冻结？
5. 为什么 SMOTE 取整只测 XGBoost，却可以支持 LR/MLP 的 SMOTE 结论？
6. `summary_full.csv` 的 SMOTE 训练规模为什么是 140272，而报告说约 448000？复现实验应以哪个为准？
7. 论文初稿的 T202609.00118 与 README 的 10.12074/202609.00078 分别是什么版本？
8. “模型容量影响更大”如何排除超参数和 MLP 未收敛造成的解释混淆？

## 复攻记录

- 本轮尚未修复任何 FIX 项，因此未进行针对性复攻。
- 复攻顺序建议：先统一公开版本/数据来源和 SMOTE CSV，再收窄阈值、重叠、容量、DoS、τ 等结论；若补实验，复攻必须只验证对应 FIX 项。

## 未决事项（TODO）

- 主矩阵的独立切分/组划分方差与重叠敏感性。
- 阈值校准的独立确认集或嵌套验证。
- SMOTE 训练规模 CSV 修复及全链路重算核对。
- 官方数据副本 SHA-256 与许可证/来源核验。
- LR/MLP 的 SMOTE 伪影敏感性及模型×方法超参敏感性。
