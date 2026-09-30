# 预处理报告

- 随机种子：42（仅用于训练集内部划分验证集）
- 划分：官方训练集 -> 训练 140,272 / 验证 35,069（分层 20%）；官方测试集 82,332 冻结不动
- 处理顺序：先划分，再拟合编码/标准化（仅训练划分 fit），无缺失值需填充（EDA 第 2 节）
- attack_cat 已 str.strip；id 已丢弃；['proto', 'service', 'state'] one-hot 后总特征数 = 194

## 各划分类别分布（attack_cat）

```
                train  valid   test
attack_cat                         
Normal          44800  11200  37000
Generic         32000   8000  18871
Exploits        26714   6679  11132
Fuzzers         14547   3637   6062
DoS              9811   2453   4089
Reconnaissance   8393   2098   3496
Analysis         1600    400    677
Backdoor         1397    349    583
Shellcode         906    227    378
Worms             104     26     44
```