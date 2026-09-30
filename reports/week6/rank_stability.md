# 方法排序稳定性（预注册 τ 检验结果）

- 口径与判定标准见 preregistration_rank_stability.md（回溯性预注册，冻结于计算前）；n=4 方法的 τ 取值离散，结论以「τ + 完整排序」共同呈现。

## 选型分割间（平均 τ = 0.111 → 不一致）

```
group   model                   comparison    tau                           order_a                           order_b note
选型分割间      LR 验证集 Macro-F1 vs 测试集 Macro-F1  1.000 SMOTE > ROS > class_weight > none SMOTE > ROS > class_weight > none     
选型分割间 XGBoost 验证集 Macro-F1 vs 测试集 Macro-F1 -1.000 SMOTE > none > ROS > class_weight class_weight > ROS > none > SMOTE     
选型分割间     MLP 验证集 Macro-F1 vs 测试集 Macro-F1  0.333 SMOTE > ROS > none > class_weight ROS > none > SMOTE > class_weight     
```

## 指标间（平均 τ = 0.278 → 不一致）

```
group   model                   comparison    tau                           order_a                           order_b note
  指标间      LR                    mf1 vs ba  1.000 SMOTE > ROS > class_weight > none SMOTE > ROS > class_weight > none     
  指标间 XGBoost                    mf1 vs ba  0.667 class_weight > ROS > none > SMOTE class_weight > ROS > SMOTE > none     
  指标间     MLP                    mf1 vs ba -0.333 ROS > none > SMOTE > class_weight class_weight > ROS > SMOTE > none     
  指标间      LR mf1 vs minority_macro_recall  0.000 SMOTE > ROS > class_weight > none class_weight > ROS > SMOTE > none     
  指标间 XGBoost mf1 vs minority_macro_recall  0.667 class_weight > ROS > none > SMOTE class_weight > ROS > SMOTE > none     
  指标间     MLP mf1 vs minority_macro_recall -0.333 ROS > none > SMOTE > class_weight class_weight > ROS > SMOTE > none     
```

## 模型间（平均 τ = 0.111 → 不一致）

```
group          model            comparison    tau                           order_a                           order_b note
  模型间  LR vs XGBoost     测试 Macro-F1 下方法排序 -0.333 SMOTE > ROS > class_weight > none class_weight > ROS > none > SMOTE     
  模型间 XGBoost vs MLP     测试 Macro-F1 下方法排序  0.000 class_weight > ROS > none > SMOTE ROS > none > SMOTE > class_weight     
  模型间      LR vs MLP     测试 Macro-F1 下方法排序  0.000 SMOTE > ROS > class_weight > none ROS > none > SMOTE > class_weight     
  模型间  LR vs XGBoost 测试 Balanced Acc 下方法排序  0.000 SMOTE > ROS > class_weight > none class_weight > ROS > SMOTE > none     
  模型间 XGBoost vs MLP 测试 Balanced Acc 下方法排序  1.000 class_weight > ROS > SMOTE > none class_weight > ROS > SMOTE > none     
  模型间      LR vs MLP 测试 Balanced Acc 下方法排序  0.000 SMOTE > ROS > class_weight > none class_weight > ROS > SMOTE > none     
```

## 预注册判定回顾

- H1 选型分割：平均 τ = 0.111 < 2/3 → 支持（排序不稳定）
- H2 指标口径：平均 τ = 0.278 < 2/3 → 支持（排序不稳定）
- H3 模型：平均 τ = 0.111 < 2/3 → 支持（排序不稳定）

- 限定：n=4 描述性检验，无 p 值宣称；τ 与排序表共同阅读。
- 数据源：runs/experiments/summary_full.csv（3 种子均值），与第 3 周稳定性表同源。