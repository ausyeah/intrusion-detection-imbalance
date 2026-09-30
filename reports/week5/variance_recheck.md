# 轻量化方差补测 v2（第 8 周，红队三轮 A1-2/A1-3）

- 协议 v2：resplit.make_splits(seed) 每种子重切官方训练池（编码器/标准化器逐种子仅 fit 训练划分，官方测试集冻结只 transform）；特征排序逐种子重做（排序模型 fit 各自训练划分）；K* 不重新选型——
  K* = 32（来源：v1 sweep.csv（runs/lightweight/sweep.csv，验证集选型封板决策））。
- v1 已披露局限「单次特征排序（seed 42）未做稳定性检验」由排名重合度直接检验：

## 终评（测试集，3 种子均值±标准差，真实切分+排序方差）

```
         macro_f1_mean  macro_f1_std  bal_acc_mean  bal_acc_std  fit_s_mean  size_mb_mean
tag                                                                                      
full194         0.5103        0.0028        0.6522       0.0016     25.5333          7.61
top32           0.5081        0.0055        0.6581       0.0033      9.5667          7.83
```

- 训练加速比（全量/精简）≈ **2.67×**（v1 为 2.52×，口径：per-seed 重切后重训）

## 每类 Recall 增量（topK* − 全量，均值±标准差[ddof=1]，按增量排序）

```
         class  topK_recall  full_recall  delta_mean  delta_std
      Analysis        0.266        0.169       0.096      0.166
         Worms        0.856        0.795       0.061      0.035
           DoS        0.204        0.181       0.024      0.012
Reconnaissance        0.851        0.849       0.002      0.001
        Generic        0.973        0.970       0.002      0.001
         Normal        0.605        0.607      -0.001      0.002
      Shellcode        0.961        0.964      -0.003      0.010
       Exploits        0.599        0.602      -0.003      0.004
        Fuzzers        0.657        0.663      -0.006      0.010
       Backdoor        0.608        0.722      -0.113      0.193
```

- 口径统一声明（复攻 V2 修正）：本文件全部标准差为样本标准差 ddof=1，与 imbalance_decay_v2/threshold_moving_v2/终评表一致；delta_std 可由 recall_per_class_per_seed_v2.csv 逐种子重算复现。
- fit 时间为 wall-clock 口径（批间约 2% 波动，加速比 25.5333/9.5667≈2.67）；实验指标为确定性，复跑逐位复现（复攻 V1 修正披露）。

## 特征排序重合度（top-K 集合 Jaccard）

```
    comparison  n_overlap  jaccard
   seed0_vs_v1         29    0.829
   seed1_vs_v1         30    0.882
   seed2_vs_v1         30    0.882
seed0_vs_seed1         31    0.939
seed0_vs_seed2         30    0.882
seed1_vs_seed2         31    0.939
```

- 结论限定：v2 方差含「切分敏感性 + 排序敏感性」两个来源，与 v1 的确定性口径（std=0）不可直接混读；v1 封板产物与结论保持原样，v2 为其方差注脚。
- 体积负结果（不降反增）在 v2 下逐种子复核见 final_metrics_v2.csv。
