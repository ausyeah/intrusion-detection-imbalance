# UNSW-NB15 EDA 报告（发表级）

## 0. 数据版本指纹（可追溯性）

| 文件 | 行数（含表头） | 大小 (MB) | SHA-256（前 16 位） |
|---|---|---|---|
| UNSW_NB15_training-set.csv | 175,342 | 32.3 | `bec7dd5ec88dc2a0…` |
| UNSW_NB15_testing-set.csv | 82,333 | 15.4 | `734fe6642edf758f…` |

- 来源：镜像仓库 Nir-J/ML-Projects（GitHub raw），下载日期 第 1 周（06-16 ~ 06-22）；官方渠道 research.unsw.edu.au 需填表申请，取得后须比对 SHA-256（见 data/README.md 待办）。
- 交叉验证：两文件行数与官方划分集公开规格一致（175,341 / 82,332 条）；各类别计数与文献报道的官方划分分布一致，支持其为官方文件副本。

## 1. 字段概览

- 总列数：45（含 id / attack_cat / label）
- 类别型列：[]
- 数值型列数：45

## 2. 缺失值（NaN）

- 无 NaN。注意 `service` 列的 `-` 是占位符不是缺失值，当作合法类别。

## 3. 重复行

- 含 id 全行重复：训练 0 条 / 测试 0 条
- 训练集去掉 id/label/attack_cat 后特征向量重复的行：84,049 条（网络流量中同特征记录可自然重复，官方划分保留，本项目不去重，此决策留痕）
- 同一特征向量对应不同 label 的冲突组：229 组 —— 存在不可约噪声，是各模型 Accuracy 上限的来源之一，论文误差分析可直接引用

## 4. label 与 attack_cat 一致性（数据集已知质量问题）

- 训练集：Normal 但 label=1 共 0 条；非 Normal 但 label=0 共 0 条 —— 一致
- 测试集：Normal 但 label=1 共 0 条；非 Normal 但 label=0 共 0 条 —— 一致

## 5. 零方差 / 近零方差数值列（训练集）

```
is_sm_ips_ports    2
```
- 取值 ≤ 2 种的特征对树模型无碍，特征筛选阶段按贡献决定去留。

## 6. service 占位符 `-` 占比

- 训练集 53.7% / 测试集 57.3%，作为合法类别编码。

## 7. attack_cat 清洁度

- 原始去重数 = 10，strip 后去重数 = 10（干净）

## 8. 类别分布（attack_cat，strip 后）

```
                train   test  train_ratio_%  test_ratio_%
attack_cat                                               
Normal          56000  37000          31.94         44.94
Generic         40000  18871          22.81         22.92
Exploits        33393  11132          19.04         13.52
Fuzzers         18184   6062          10.37          7.36
DoS             12264   4089           6.99          4.97
Reconnaissance  10491   3496           5.98          4.25
Analysis         2000    677           1.14          0.82
Backdoor         1746    583           1.00          0.71
Shellcode        1133    378           0.65          0.46
Worms             130     44           0.07          0.05
```

- 训练集不平衡比例（最多类/最少类）≈ 431 : 1
- 最少类：Worms（130 条）—— 这就是后面少数类 Recall 最难看的那一类

## 9. 二分类 label 分布

```
            train   test
label                   
Normal(0)   56000  37000
Attack(1)  119341  45332
```

## 10. 划分方式核验

- 训练/测试各类别数量完全相同：False（官方划分为全体样本的随机划分，两类数量不同属正常；保留官方划分，不自建测试集）
