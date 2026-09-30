# 数据集：UNSW-NB15

## 来源

- 官方页面：<https://research.unsw.edu.au/projects/unsw-nb15-dataset>（UNSW Canberra Cyber）
- 本项目使用**官方划分集**（作者已分好训练/测试）：
  - `UNSW_NB15_training-set.csv` — 175,341 行 × 45 列
  - `UNSW_NB15_testing-set.csv` — 82,332 行 × 45 列
- **实际下载渠道**：镜像仓库 [Nir-J/ML-Projects](https://github.com/Nir-J/ML-Projects)（GitHub raw），下载日期 **第 1 周（06-16 ~ 06-22）**。镜像文件与官方划分集公开规格逐项一致（行数、45 列列名、各类别计数与文献报道分布吻合，见 `reports/week1/eda_report.md` 第 0 节与第 10 节）。

## 版本核验（可追溯性）

| 文件 | SHA-256 |
|---|---|
| `UNSW_NB15_training-set.csv` | `bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa` |
| `UNSW_NB15_testing-set.csv` | `734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559` |

完整校验和见 [`reports/week1/SHA256SUMS.txt`](../reports/week1/SHA256SUMS.txt)。

**待办（低优先级，第 6 周前完成即可）**：从官方页面填表申请正式下载渠道的副本，与上表 SHA-256 比对。一致则在论文中可直接引用官方来源；不一致则需换用官方文件并重跑（所有实验脚本可一键复现，成本可控）。

## 字段表说明

本项目 `data/README.md` 中的 45 列字段说明为自行整理；官方数据包内附带 `UNSW-NB15_features.csv`（逐特征类型与描述），论文写作阶段以官方表为准并核对一遍。

## 下载位置

放到本目录（`data/raw/`），文件名保持上表不变。`data/raw/` 已加入 `.gitignore`，**原始数据不入 git、不做任何修改**。

## 许可与引用

数据集公开供研究使用，使用必须引用原作者论文：

1. Moustafa, N., & Slay, J. (2015). *UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set)*. 2015 Military Communications and Information Systems Conference (MilCIS), IEEE.
2. Moustafa, N., & Slay, J. (2016). *The evaluation of Network Anomaly Detection Systems: Statistical analysis of the UNSW-NB15 data set and the comparison with the KDD99 data set*. Information Security Journal: A Global Perspective.

论文写作时上述两条都要进参考文献。

## 字段速览（45 列）

| 列 | 含义 |
|---|---|
| `id` | 行号（无信息量，预处理时丢弃） |
| `dur` | 连接时长（秒） |
| `proto` | 传输层协议（类别型：tcp/udp/...） |
| `service` | 目标服务（类别型：http/ftp/-，`-` 表示无） |
| `state` | 连接状态（类别型：FIN/SYN/...） |
| `spkts`/`dpkts` | 源→目的 / 目的→源 的包数 |
| `sbytes`/`dbytes` | 源→目的 / 目的→源 的字节数 |
| `rate` | 每秒包速率 |
| `sttl`/`dttl` | 源→目的 / 目的→源 的 TTL |
| `sload`/`dload` | 源/目的 端比特率 |
| `sloss`/`dloss` | 源/目的 端重传或丢包数 |
| `sinpkt`/`dinpkt` | 源/目的 端包间隔（ms） |
| `sjit`/`djit` | 源/目的 端抖动（ms） |
| `swin`/`stcpb`/`dtcpb`/`dwin` | TCP 窗口大小与序列号 |
| `tcprtt`/`synack`/`ackdat` | TCP 握手往返/各段时延 |
| `smean`/`dmean` | 源/目的 端平均包大小 |
| `trans_depth` | HTTP 事务深度 |
| `response_body_len` | HTTP 响应体长度 |
| `ct_srv_src`/`ct_state_ttl`/`ct_dst_ltm`/`ct_src_dport_ltm`/`ct_dst_sport_ltm`/`ct_dst_src_ltm` | 连接计数类特征（时间窗口内同源同目/同服务/同状态等连接数） |
| `is_ftp_login`/`ct_ftp_cmd` | FTP 登录次数 / FTP 命令数 |
| `ct_flw_http_mthd` | HTTP 方法计数 |
| `ct_src_ltm`/`ct_srv_dst` | 同源 / 同目-同服务 连接计数 |
| `is_sm_ips_ports` | 源目 IP 与端口是否完全相同（1/0） |
| `attack_cat` | **10 类攻击类别标签**（多分类目标）：Normal, Generic, Exploits, Fuzzers, DoS, Reconnaissance, Analysis, Backdoor, Shellcode, Worms |
| `label` | **二分类标签**：0 = Normal，1 = Attack |

完整官方字段表见数据包内 `UNSW-NB15_features.csv`（含每个特征的类型与描述）。

## 已知数据注意点

- 镜像下载的 CSV 带 UTF-8 BOM，`pd.read_csv` 需指定 `encoding="utf-8-sig"`，否则首列名会变成 `\ufeffid`。
- `attack_cat` 在部分版本里带首尾空格（如 `" Fuzzers"`），预处理必须 `str.strip()`。
- `service` 列的 `-` 是"无服务"占位符，不是缺失值，当作一个合法类别处理。
- `ct_ftp_cmd` 在 CSV 里可能被读成字符串/浮点，预处理时统一为数值。
- 官方划分集训练（175,341 条）与测试（82,332 条）是作者对全体样本的随机划分，各类别占比接近但不相等（如 Normal：训练 56,000 / 测试 37,000）。这是官方给定划分，必须原样保留，不要自己重新打乱或重划测试集，否则无法和已有文献对比。
