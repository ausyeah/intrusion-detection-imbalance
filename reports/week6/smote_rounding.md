# SMOTE 哑变量取整敏感性（红队 S6 折中检验）

- 协议：SMOTE(random_state=seed) 重采样后，对合成行的 155 个 one-hot 哑变量列取整（最小干预），XGBoost 同参 3 种子；对照 none 与不取整 SMOTE。
- 测试 Macro-F1 均值：none 0.5097 / SMOTE 0.5041 / SMOTE取整 0.5021
- DoS Recall 均值：SMOTE 0.4878 / 取整 0.4378（差 +0.0500）
- **判定（红队三轮 A1-5/A2-4 修订，分指标口径）**：Macro-F1 差 0.002、Balanced Acc 差 0.002，相对方法间差距（SMOTE 与 none 的 Macro-F1 差 0.006）影响可忽略；但 DoS Recall 系统性下降 0.05（3/3 种子方向一致：0.5004/0.4808/0.4823 → 0.4407/0.4387/0.4341），单类结论需谨慎。「方向不变」定义：取整后 SMOTE 的 DoS Recall（0.438）仍远高于 none（0.098），SMOTE ≫ none 的方法排序不变。

## 汇总（3 种子均值/标准差）

```
              test_macro_f1         test_balanced_acc         test_dos_recall        
                       mean     std              mean     std            mean     std
variant                                                                              
none                 0.5097  0.0000            0.5497  0.0000          0.0981  0.0000
smote                0.5041  0.0014            0.6035  0.0057          0.4878  0.0109
smote_rounded        0.5021  0.0011            0.6053  0.0033          0.4378  0.0034
```

## 明细

```
      variant  seed  test_macro_f1  test_balanced_acc  test_dos_recall  n_synthetic_rounded
         none     0         0.5097             0.5497           0.0981                  NaN
        smote     0         0.5057             0.6098           0.5004                  0.0
smote_rounded     0         0.5014             0.6078           0.4407             307728.0
         none     1         0.5097             0.5497           0.0981                  NaN
        smote     1         0.5036             0.5987           0.4808                  0.0
smote_rounded     1         0.5034             0.6016           0.4387             307728.0
         none     2         0.5097             0.5497           0.0981                  NaN
        smote     2         0.5031             0.6021           0.4823                  0.0
smote_rounded     2         0.5016             0.6065           0.4341             307728.0
```

- 限定：取整为最小干预近似（未做按行独热归一化、未改邻居计算），结论仅在此口径内成立。