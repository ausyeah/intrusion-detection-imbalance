# 第 4 周误差分析（v2，红队复审后）

- 选型依据（各模型 3 种子平均验证集 Macro-F1 最高，遵守测试集不参与选型纪律；种子 0 重训）：LR → SMOTE（验证 0.4189，对应测试 0.3672）；XGBoost → SMOTE（验证 0.6277，对应测试 0.5041）；MLP → SMOTE（验证 0.5337，对应测试 0.4192）
- 错误归因口径：novel = 训练划分未见该特征向量（正常泛化错误）；conflict = 训练见过但出现过多种 attack_cat 标注（数据集固有冲突，不可约噪声；v2 起按 10 类 attack_cat 计，v1 仅按二分类 label 计导致低估）；overlap_clean = 训练见过且 attack_cat 一致（模型对该向量的拟合极限，非流程错误）。
- 内部校验（硬性）：模型是特征的确定性函数，逐格验证全部错误行满足「测试行预测 == 训练副本行预测」，不一致数必须 = 0。

## LR + SMOTE

- 错误共 30,660 条，归因：novel 25,558（83.4%）、conflict 2,261（7.4%）、overlap_clean 2,841（9.3%）
- 内部校验：30,660 个错误行「测试预测 == 训练副本预测」不一致数 = 0（哈希与行对齐正确）。
- 测试集与训练划分共享特征向量的行共 8,154 条，其中错误 5,102 条（63%，整体错误率 37%）。
- 重叠行错误的真实类别构成（实测，v2 修正 v1 的未经验证描述）：Exploits 1,700 条（33%）、DoS 1,493 条（29%）、Reconnaissance 1,010 条（20%）。
- 主要混淆对：
```
true            pred          
Normal          Fuzzers           9106
                Shellcode         2286
                Analysis          2025
                Reconnaissance    1637
Exploits        Analysis          1525
DoS             Analysis          1228
Exploits        Backdoor          1217
Reconnaissance  Shellcode         1154
```

## XGBoost + SMOTE

- 错误共 22,088 条，归因：novel 18,361（83.1%）、conflict 1,848（8.4%）、overlap_clean 1,879（8.5%）
- 内部校验：22,088 个错误行「测试预测 == 训练副本预测」不一致数 = 0（哈希与行对齐正确）。
- 测试集与训练划分共享特征向量的行共 8,154 条，其中错误 3,727 条（46%，整体错误率 27%）。
- 重叠行错误的真实类别构成（实测，v2 修正 v1 的未经验证描述）：Exploits 1,670 条（45%）、DoS 933 条（25%）、Normal 511 条（14%）。
- 主要混淆对：
```
true      pred    
Normal    Fuzzers     8421
Exploits  DoS         2133
Normal    Analysis    1483
Fuzzers   DoS          858
Exploits  Backdoor     854
DoS       Exploits     826
          Backdoor     797
Fuzzers   Normal       644
```

## MLP + SMOTE

- 错误共 28,639 条，归因：novel 24,131（84.3%）、conflict 2,188（7.6%）、overlap_clean 2,320（8.1%）
- 内部校验：28,639 个错误行「测试预测 == 训练副本预测」不一致数 = 0（哈希与行对齐正确）。
- 测试集与训练划分共享特征向量的行共 8,154 条，其中错误 4,508 条（55%，整体错误率 35%）。
- 重叠行错误的真实类别构成（实测，v2 修正 v1 的未经验证描述）：Exploits 1,702 条（38%）、DoS 1,662 条（37%）、Normal 544 条（12%）。
- 主要混淆对：
```
true      pred     
Normal    Fuzzers      11016
          Analysis      1989
Exploits  Backdoor      1719
DoS       Backdoor      1446
Exploits  DoS           1363
Normal    Shellcode      966
Exploits  Analysis       777
DoS       Analysis       746
```

## 跨模型重叠错误核验（红队 S9）

- |LR∩XGB| = 499（LR 682 / XGB 510）；|XGB∩MLP| = 501（XGB 510 / MLP 530）；|LR∩MLP| = 522
- 若两模型重叠错误计数相同但交集远小于自身，则计数相同为巧合；交集≈自身则说明两模型在同一批难例向量上犯同样的错。

## 纯模型体积（选型配置，seed 0，pickle 计）

```
  model method  model_only_mb  pipeline_mb
     LR  SMOTE           0.02         0.18
XGBoost  SMOTE           8.59         8.75
    MLP  SMOTE           0.43         0.59
```

- 与第 3 周 pipeline 口径的区别：不含采样器的 sample_indices_ 索引。

- 全部错误案例见 error_cases.csv（含 row_hash、error_type），结论表述以第 3 周 3 种子均值为准，本文件为代表性单次运行。