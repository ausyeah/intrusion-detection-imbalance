# 第 5 周轻量化报告（类别权重 XGBoost + 特征筛选）

- 协议：增益重要性排序（训练划分、seed 42 单次拟合——排序稳定性未做多种子检验，列入局限）；验证集选 K（并列取更小）；测试集仅终评
- K 扫描：[194, 128, 64, 32, 16, 8]；**选型 K* = 32**（验证 Macro-F1 0.6125）

## K 扫描（seed 42，验证集）

```
   tag  valid_macro_f1 test_macro_f1  fit_s  model_only_mb
top194          0.6094          None   29.2           7.65
top128          0.6120          None   24.2           7.84
 top64          0.6089          None   15.4           7.92
 top32          0.6125          None   11.3           7.82
 top16          0.5483          None    9.1           7.46
  top8          0.3111          None    7.0           4.48
```

## 终评（测试集，3 种子均值±标准差）

```
         macro_f1_mean  macro_f1_std  bal_acc_mean  fit_s_mean  size_mb_mean
tag                                                                         
full194         0.5123           0.0        0.6549     29.2667          7.67
top32           0.5087           0.0        0.6605     11.6000          7.82
```

- 确定性披露（红队三轮 A1-2）：XGBoost+类别权重为确定性算法，3 种子结果完全相同（std=0）——std=0 表示可复现性而非稳健性；full194 与 top32 的 Macro-F1 差异（0.0036）与 Balanced Acc 差异（0.0056）的显著性无法由本实验评估，结论按「权衡」而非「改进」表述。
- 训练加速比（全量/精简）≈ **2.52×**；模型体积不降反增 2.0%——XGBoost 体积由树结构主导，特征筛选不减小其体积（负结果，如实报告）
- Balanced Accuracy：top32 0.6605 对全量 0.6549
- 每类 Recall 变化（top32 对全量，均值，按增量排序）：
```
         class  topK_recall  full_recall  delta
      Analysis        0.120        0.058  0.062
         Worms        0.864        0.818  0.045
           DoS        0.198        0.171  0.026
       Generic        0.972        0.970  0.003
Reconnaissance        0.849        0.850 -0.000
        Normal        0.604        0.607 -0.002
      Exploits        0.597        0.600 -0.003
     Shellcode        0.966        0.971 -0.005
       Fuzzers        0.650        0.662 -0.012
      Backdoor        0.786        0.842 -0.057
```

- 注（红队三轮 A1-4 口径说明）：delta 由 4 位小数 per-seed Recall 的均值先相减再舍入（08_lightweight.py 生成），与表中 3 位小数列直接相减可能相差 0.001（舍入次序差异，非数据不一致）。

- 结论限定：以上比较在所测协议内成立（单一数据集、one-hot 编码、固定超参、单次特征排序）；体积为纯模型 pickle 口径。
