// 《毕设论文流程与实验执行手册》生成脚本（docx-js）
// 结构：封面（R4/GO-1）→ 目录（罗马页码）→ 正文（阿拉伯页码从 1 起）
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  Header, Footer, PageNumber, NumberFormat, SectionType, TableOfContents,
  LevelFormat, TableLayoutType,
} = require("docx");
const fs = require("fs");

// ── 调色板 GO-1（Graphite Orange，方案/计划类文档）──
const P = {
  bg: "1A2330", accent: "D4875A", primary: "1A2330",
  cover: { titleColor: "FFFFFF", subtitleColor: "B0B8C0", metaColor: "3A4553", footerColor: "909090" },
  table: { headerBg: "D4875A", headerText: "FFFFFF", innerLine: "DDD0C8", surface: "F8F0EB" },
};
const F_BODY = { ascii: "Times New Roman", eastAsia: "SimSun" };
const F_HEAD = { ascii: "Times New Roman", eastAsia: "SimHei" };
const F_CODE = { ascii: "Consolas", eastAsia: "Microsoft YaHei" };

const NB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NB, bottom: NB, left: NB, right: NB };
const allNoBorders = { top: NB, bottom: NB, left: NB, right: NB, insideHorizontal: NB, insideVertical: NB };
const emptyPara = () => new Paragraph({ children: [] });

// ── 封面标题布局函数（design-system 标准实现）──
function splitTitleLines(title, charsPerLine) {
  if (title.length <= charsPerLine) return [title];
  const breakAfter = new Set([..."，。、；：！？", ..."的与和及之在于为", ..."-_—–·/", ..." \t"]);
  const lines = [];
  let remaining = title;
  while (remaining.length > charsPerLine) {
    let breakAt = -1;
    for (let i = charsPerLine; i >= Math.floor(charsPerLine * 0.6); i--) {
      if (i < remaining.length && breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
    }
    if (breakAt === -1) {
      const limit = Math.min(remaining.length, Math.ceil(charsPerLine * 1.3));
      for (let i = charsPerLine + 1; i < limit; i++) {
        if (breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
      }
    }
    if (breakAt === -1) {
      breakAt = charsPerLine;
      const prevChar = remaining[breakAt - 1], nextChar = remaining[breakAt];
      if (prevChar && nextChar && !breakAfter.has(prevChar) && !breakAfter.has(nextChar) &&
          /[\u4e00-\u9fff]/.test(prevChar) && /[\u4e00-\u9fff]/.test(nextChar)) breakAt -= 1;
    }
    lines.push(remaining.slice(0, breakAt).trim());
    remaining = remaining.slice(breakAt).trim();
  }
  if (remaining) lines.push(remaining);
  if (lines.length > 1 && lines[lines.length - 1].length <= 2) {
    const last = lines.pop();
    lines[lines.length - 1] += last;
  }
  return lines;
}
function calcTitleLayout(title, maxWidthTwips, preferredPt = 40, minPt = 24) {
  const charWidth = (pt) => pt * 20;
  const charsPerLine = (pt) => Math.floor(maxWidthTwips / charWidth(pt));
  let titlePt = preferredPt, lines;
  while (titlePt >= minPt) {
    const cpl = charsPerLine(titlePt);
    if (cpl < 2) { titlePt -= 2; continue; }
    lines = splitTitleLines(title, cpl);
    if (lines.length <= 3 && lines.every(l => l.length <= cpl)) break;
    titlePt -= 2;
  }
  if (!lines || lines.length > 3) { lines = splitTitleLines(title, charsPerLine(minPt)); titlePt = minPt; }
  return { titlePt, titleLines: lines };
}

// ── 封面 Recipe R4（Top Color Block）──
function buildCoverR4(config) {
  const C = config.palette;
  const padL = 1200, padR = 800;
  const availableWidth = 11906 - padL - padR;
  const { titlePt, titleLines } = calcTitleLayout(config.title, availableWidth, 36, 26);
  const titleSize = titlePt * 2;

  const titleBlockHeight = titleLines.length * (titlePt * 23 + 200);
  const englishLabelH = config.englishLabel ? (9 * 23 + 500) : 0;
  const subtitleH = config.subtitle ? (12 * 23 + 200) : 0;
  const UPPER_H = Math.max(7500, englishLabelH + titleBlockHeight + subtitleH + 1500 + 800);
  const DIVIDER_H = 60;
  const spacerIntrinsic = 280;
  const topSpacing = Math.max(UPPER_H - englishLabelH - titleBlockHeight - subtitleH - spacerIntrinsic - 800, 400);

  const upperBlock = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: UPPER_H, rule: "exact" },
      children: [new TableCell({
        shading: { type: ShadingType.CLEAR, fill: C.bg }, borders: noBorders,
        verticalAlign: "top",
        margins: { left: padL, right: padR },
        children: [
          new Paragraph({ spacing: { before: topSpacing } }),
          config.englishLabel ? new Paragraph({
            spacing: { after: 500 },
            children: [new TextRun({ text: config.englishLabel.split("").join(" "),
              size: 18, color: C.accent, font: { ascii: "Calibri" }, characterSpacing: 60 })],
          }) : null,
          ...titleLines.map((line, i) => new Paragraph({
            spacing: { after: i < titleLines.length - 1 ? 100 : 200, line: Math.ceil(titlePt * 23), lineRule: "atLeast" },
            children: [new TextRun({ text: line, size: titleSize, bold: true,
              color: C.cover.titleColor, font: { eastAsia: "SimHei", ascii: "Arial" } })],
          })),
          config.subtitle ? new Paragraph({
            spacing: { after: 100, line: 340, lineRule: "atLeast" },
            children: [new TextRun({ text: config.subtitle, size: 24, color: C.cover.subtitleColor,
              font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
          }) : null,
        ].filter(Boolean),
      })],
    })],
  });

  const divider = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: DIVIDER_H, rule: "exact" },
      children: [new TableCell({ borders: noBorders,
        shading: { type: ShadingType.CLEAR, fill: C.accent }, children: [emptyPara()] })],
    })],
  });

  const lowerContent = [
    new Paragraph({ spacing: { before: 800 } }),
    ...(config.metaLines || []).map(line => new Paragraph({
      indent: { left: padL }, spacing: { after: 120 },
      children: [new TextRun({ text: line, size: 28, color: C.cover.metaColor,
        font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    })),
    new Paragraph({ spacing: { before: 2000 } }),
    new Paragraph({
      indent: { left: padL },
      children: [
        new TextRun({ text: config.footerLeft || "", size: 22, color: C.cover.footerColor }),
        new TextRun({ text: "          " }),
        new TextRun({ text: config.footerRight || "", size: 22, color: C.cover.footerColor }),
      ],
    }),
  ];

  return [new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: 16838, rule: "exact" },
      children: [new TableCell({
        shading: { type: ShadingType.CLEAR, fill: "FFFFFF" }, borders: noBorders,
        verticalAlign: "top",
        children: [upperBlock, divider, ...lowerContent],
      })],
    })],
  })];
}

// ── 正文组件 ──
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    keepNext: true,
    spacing: { before: 360, after: 160, line: 380, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, color: P.primary, font: F_HEAD })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    keepNext: true,
    spacing: { before: 260, after: 120, line: 340, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, color: P.primary, font: F_HEAD })],
  });
}
function runs(spec) {
  if (typeof spec === "string") return [new TextRun({ text: spec, size: 24, color: "000000", font: F_BODY })];
  return spec.map(r => new TextRun({ text: r.t, bold: !!r.b, size: 24, color: r.c || "000000", font: F_BODY }));
}
function p(spec, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 480 },
    spacing: { line: 312, after: opts.after || 0 },
    children: runs(spec),
  });
}
function cmd(text) {
  return new Paragraph({
    shading: { type: ShadingType.CLEAR, fill: "F5F2ED" },
    indent: { left: 480 },
    spacing: { line: 300, before: 40, after: 40 },
    children: [new TextRun({ text, size: 20, color: "333333", font: F_CODE })],
  });
}
function warn(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 480, right: 240 },
    spacing: { line: 312, before: 80, after: 80 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: P.accent, space: 10 } },
    children: [new TextRun({ text, bold: true, size: 24, color: "7A4A22", font: F_BODY })],
  });
}
function numbered(ref, spec) {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 312, after: 40 },
    children: runs(spec),
  });
}
function tableTitle(text) {
  return new Paragraph({
    keepNext: true,
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, size: 21, color: P.primary, font: F_HEAD })],
  });
}
function tbl(headers, rows, widths) {
  const mk = (text, bold, fill, color) => new TableCell({
    shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
    width: undefined,
    children: [new Paragraph({
      spacing: { line: 280 },
      children: [new TextRun({ text, bold: !!bold, size: 21, color: color || "000000",
        font: bold ? F_HEAD : F_BODY })],
    })],
  });
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: P.accent },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: P.accent },
      left: NB, right: NB,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: P.table.innerLine },
      insideVertical: NB,
    },
    rows: [
      new TableRow({
        tableHeader: true, cantSplit: true,
        children: headers.map((t, i) => {
          const c = mk(t, true, P.table.headerBg, P.table.headerText);
          c.options = undefined;
          return new TableCell({
            shading: { type: ShadingType.CLEAR, fill: P.table.headerBg },
            margins: { top: 60, bottom: 60, left: 120, right: 120 },
            width: { size: widths[i], type: WidthType.PERCENTAGE },
            children: [new Paragraph({
              spacing: { line: 280 },
              children: [new TextRun({ text: t, bold: true, size: 21, color: P.table.headerText, font: F_HEAD })],
            })],
          });
        }),
      }),
      ...rows.map((r, ri) => new TableRow({
        cantSplit: true,
        children: r.map((t, i) => new TableCell({
          shading: ri % 2 === 0 ? { type: ShadingType.CLEAR, fill: "FFFFFF" }
                                 : { type: ShadingType.CLEAR, fill: P.table.surface },
          margins: { top: 60, bottom: 60, left: 120, right: 120 },
          width: { size: widths[i], type: WidthType.PERCENTAGE },
          children: [new Paragraph({
            spacing: { line: 280 },
            children: [new TextRun({ text: String(t), size: 21, color: "000000", font: F_BODY })],
          })],
        })),
      })),
    ],
  });
}
const step = (ref, s) => numbered(ref, s);

// ── 页脚 ──
const pageFooter = () => new Footer({
  children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" })],
  })],
});
const pageHeader = () => new Header({
  children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC", space: 4 } },
    children: [new TextRun({ text: "毕设论文流程与实验执行手册", size: 18, color: "888888", font: F_BODY })],
  })],
});

// ── 正文内容 ──
const body = [];

// 第一章
body.push(h1("第一章 项目总览"));
body.push(h2("1.1 研究定位"));
body.push(p("本课题题目为「面向类别不平衡的网络入侵检测方法比较与轻量化改进研究」，基于 UNSW-NB15 数据集开展。课题诚实定位为实验研究与轻量化改进：不声称提出全新算法，贡献在于建立统一的类别不平衡实验协议、在统一协议下系统比较多种模型与不平衡处理方法、并提出一个轻量化组合方案并分析其适用边界。"));
body.push(p("课题围绕三个研究问题展开：第一，类别不平衡会让哪些攻击类别被漏检；第二，类别权重（class weight）、随机过采样（RandomOverSampler）与 SMOTE 三种方法哪种更有效；第三，检测性能、少数类 Recall 与推理时间之间如何权衡。"));
body.push(p([{ t: "明确不做的事：", b: true }, { t: "不做 1D-CNN、Transformer、图神经网络等复杂模型；不把「类别权重 + SMOTE」包装成原创算法；不追求堆砌数据集数量。8 周内完成一篇有真实实验、代码可运行、数据处理无泄漏的论文即为合格，这也是冲击优秀毕设的基础。" }]));
body.push(h2("1.2 仓库与目录结构"));
body.push(p("代码与文档统一托管在 GitHub 私有仓库 graduate-article（如需在复试或评优时展示，可在完成前改为公开）。本地目录如下，各目录的用途与入库规则见表 1-1。"));
body.push(tableTitle("表 1-1 目录结构与入库规则"));
body.push(tbl(["路径", "用途", "是否入 Git"],
  [["data/raw/", "原始数据，只读、永不修改", "否（.gitignore）"],
   ["data/processed/", "清洗与划分后的数据，可由脚本再生成", "否（体积大）"],
   ["src/", "按编号执行的脚本：01_eda.py、02_preprocess.py、03_run_experiments.py 等", "是"],
   ["configs/", "实验配置：路径、随机种子、超参数", "是"],
   ["runs/", "每次实验自动保存的配置、日志与指标", "本地保存，关键结论手动入库"],
   ["figures/", "论文用图（类别分布、混淆矩阵等）", "是"],
   ["reports/", "阶段性证据存档：EDA 报告、数据校验和、环境版本", "是（week1 起）"],
   ["paper/", "论文稿、流程手册等文档", "是"]],
  [22, 56, 22]));
body.push(h2("1.3 当前进度（截至 2026 年 9 月 6 日，含周内自查修正）"));
body.push(tableTitle("表 1-2 第 1 至 2 周任务完成情况"));
body.push(tbl(["事项", "状态", "说明"],
  [["Git 仓库与项目目录", "已完成", "仓库 graduate-article，本地路径 D:\\ZCode-work\\毕设论文"],
   ["Python 虚拟环境与依赖", "已完成", "Python 3.13 + 依赖精确版本锁定 requirements.lock.txt（115 个包）"],
   ["数据集来源与许可记录", "已完成", "data/README.md：镜像来源与日期、两条必引文献、官方渠道核对待办"],
   ["UNSW-NB15 下载与核验", "已完成", "行数达标并留存 SHA-256 指纹（reports/week1/SHA256SUMS.txt）"],
   ["发表级 EDA", "已完成", "不平衡度约 431:1；训练集 48% 行涉及特征重复；229 组同特征不同标签冲突"],
   ["训练/验证/测试划分", "已完成", "02_preprocess.py：140,272 / 35,069 / 82,332，仅训练划分拟合编码与标准化"],
   ["LR 与 XGBoost 基线", "已完成", "03_baseline.py：LR、XGBoost、XGBoost+类别权重三组"],
   ["第一张混淆矩阵", "已完成", "figures/confusion_matrix_baseline.png（三模型并排，行归一化）"],
   ["实验表格", "已启动", "runs/baseline/metrics.csv，第 3 周扩为 36 组矩阵"]],
  [30, 20, 50]));

// 第二章
body.push(h1("第二章 环境与 Git 操作"));
body.push(h2("2.1 环境搭建（已完成）"));
body.push(p("以下命令已在第 1 周（06-16 ~ 06-22）执行完毕，记录在此供重装或换机时复现。"));
body.push(cmd("git clone https://github.com/ausyeah/graduate-article.git D:\\ZCode-work\\毕设论文"));
body.push(cmd("cd D:\\ZCode-work\\毕设论文"));
body.push(cmd("python -m venv .venv"));
body.push(cmd(".venv\\Scripts\\activate"));
body.push(cmd("pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"));
body.push(p("依赖清单（requirements.txt）：pandas、numpy、scikit-learn、imbalanced-learn、xgboost、matplotlib、seaborn、jupyter、pyarrow。精确版本锁定在 requirements.lock.txt（115 个包），换机复现时先装 requirements.txt 再用 lock 文件核对版本。环境全量记录见 reports/week1/environment-versions.txt。"));
body.push(h2("2.2 日常 Git 工作流"));
body.push(p("每完成一个脚本或一节论文就提交一次，保证任何时刻都能回退到可用状态。提交信息采用「前缀: 内容」格式，前缀约定：docs（文档）、feat（新脚本或新功能）、exp（实验结果更新）、fix（修复）、data（数据处理脚本变更）。常用命令如下。"));
body.push(cmd("git status && git add ."));
body.push(cmd("git commit -m \"feat: 新增 EDA 脚本 01_eda.py\""));
body.push(cmd("git push origin main"));
body.push(h2("2.3 网络与镜像"));
body.push(p("pip 统一使用清华镜像（命令见 2.1）。访问 GitHub 不稳定时，为本条命令临时挂本机代理（Clash 默认端口 7897），不要改全局配置："));
body.push(cmd("git -c http.proxy=http://127.0.0.1:7897 push origin main"));
body.push(cmd("curl -x http://127.0.0.1:7897 -L -O <下载地址>"));

// 第三章
body.push(h1("第三章 数据集获取与核验"));
body.push(h2("3.1 来源与许可"));
body.push(p("数据集为 UNSW-NB15，由澳大利亚堪培拉新南威尔士大学网络空间安全中心发布，官方页面为 research.unsw.edu.au/projects/unsw-nb15-dataset。数据集公开供研究使用，使用时必须引用原作者两篇论文：其一为 Moustafa 与 Slay 2015 年发表于 MilCIS 会议的「UNSW-NB15: a comprehensive data set for network intrusion detection systems」；其二为两人 2016 年发表于 Information Security Journal 的网络异常检测系统评估论文。论文写作时两条都要列入参考文献，此为许可义务，不可省略。"));
body.push(h2("3.2 下载与核验"));
body.push(p("本项目使用官方划分集（作者已按类别分好训练与测试），共两个文件，放入 data/raw/ 目录。若官方渠道下载困难，可使用镜像仓库 Nir-J/ML-Projects（GitHub）。下载命令："));
body.push(cmd("curl -L -o data/raw/UNSW_NB15_training-set.csv https://raw.githubusercontent.com/Nir-J/ML-Projects/master/UNSW-Network_Packet_Classification/UNSW_NB15_training-set.csv"));
body.push(cmd("curl -L -o data/raw/UNSW_NB15_testing-set.csv https://raw.githubusercontent.com/Nir-J/ML-Projects/master/UNSW-Network_Packet_Classification/UNSW_NB15_testing-set.csv"));
body.push(p("下载完成后必须核验，不达标的文件不得进入实验。核验标准见表 3-1；此外对每个数据文件计算 SHA-256 并存入 reports/week1/SHA256SUMS.txt，作为「用的是哪一版数据」的指纹证据，EDA 报告第 0 节同步记录。"));
body.push(tableTitle("表 3-1 数据核验标准"));
body.push(tbl(["文件", "期望行数（含表头）", "期望列数", "核验方法"],
  [["UNSW_NB15_training-set.csv", "175,342 行（175,341 条样本 + 表头）", "45", "wc -l 与 head -1"],
   ["UNSW_NB15_testing-set.csv", "82,333 行（82,332 条样本 + 表头）", "45", "同上"]],
  [40, 30, 12, 18]));
body.push(p("行数不符说明文件截断，需带断点续传参数重新下载（curl -C - -L）。列头应从 id, dur, proto, service, state 开始，至 attack_cat, label 结束。"));
body.push(h2("3.3 数据注意点"));
body.push(p("以下四点来自数据集的已知问题，预处理阶段必须逐一处理，EDA 报告也会自动核验第一点。"));
body.push(step("st-data", [{ t: "attack_cat 列在部分版本中带首尾空格（例如 「 Fuzzers」），读取后必须执行 str.strip()，否则同一类别会被拆成两个。" }]));
body.push(step("st-data", "service 列的短横线是「无服务」占位符而非缺失值，应作为一个合法类别参与编码。"));
body.push(step("st-data", "ct_ftp_cmd 等列可能被 CSV 读取器解析为字符串或浮点，预处理时统一转为数值。"));
body.push(step("st-data", "官方划分集训练（175,341 条）与测试（82,332 条）是作者对全体样本的随机划分，各类别占比接近但不相等（如 Normal：训练 56,000 / 测试 37,000）。这是官方给定划分，必须原样保留，不得自行重划测试集，否则无法与已有文献对比。"));
body.push(step("st-data", "数据完整性实测（第 1 周）：训练集 84,049 行（48%）存在同特征向量重复，其中 229 组重复特征对应不同 label——在保留官方划分、不去重的前提下属于数据集固有噪声，是各模型准确率上限的来源之一；按 attack_cat 冲突口径错误归因中 conflict 占 7.3–8.6%（v1 二分类 label 口径 0.6–0.7% 系统性低估），去重可移除此类噪声。本项目决策：保留官方划分、不做去重，此决策与依据记入 EDA 报告第 3 节，论文误差分析直接引用。"));
body.push(step("st-data", "划分重叠实测（04_split_overlap_audit.py，见 reports/week2/overlap_report.md）：训练划分与验证划分共享 5,721 个特征向量（验证集 47.0% 的行受影响，126 组标签冲突）；与测试集共享 1,207 个（测试集 9.9% 的行受影响，244 组冲突）。重叠源于官方划分保留了数据集固有重复，属数据集特性而非流程错误；绝对指标可能因此整体偏高，但不改变方法间相对比较结论——论文「局限性」一节必须引用本条。"));

// 第四章
body.push(h1("第四章 八周执行计划"));
body.push(p("总原则：先完成一个可信闭环，再考虑扩展。每周交付物见表 4-1，各周详细步骤见 4.1 至 4.8 节。"));
body.push(tableTitle("表 4-1 八周计划总览"));
body.push(tbl(["周", "主题", "关键交付物", "验收标准"],
  [["1", "环境与数据", "仓库、环境、数据核验、EDA 报告与类别分布图", "eda_report.md 产出且行数核验通过"],
   ["2", "预处理与基线", "02_preprocess.py、LR 与 XGBoost 基线、第一张混淆矩阵", "基线指标合理且无泄漏"],
   ["3", "不平衡实验", "3 模型 × 4 方法 × 3 种子全部跑完", "runs/ 下 36 组结果齐全"],
   ["4", "主要结果", "每类 Recall、混淆矩阵、耗时与模型大小、稳定性", "能回答三个研究问题"],
   ["5", "轻量化改进", "单一方向的改进方案与对比表", "给出性能-开销权衡结论"],
   ["6", "结论稳健性（修订）", "预注册 τ 检验、阈值移动对照、哑变量取整敏感性、不平衡比例衰减、补充修复清单（含 3 种子归因与 none 对照）", "方法排序结论以 τ 与全排序正式化；RQ3 获得阈值移动对照"],
   ["7", "论文初稿", "按学校模板的完整初稿", "导师可审阅的完整文稿"],
   ["8", "修改与答辩", "终稿、答辩 PPT、代码与 README 整理", "达到评优提交标准"]],
  [8, 20, 42, 30]));

body.push(h2("4.1 第 1 周：环境与数据（已完成，含审计修复）"));
body.push(p("目标：搭好环境、拿到数据、看清类别不平衡到底有多严重。步骤："));
body.push(step("st-w1", "建仓库与目录（已完成，见第一章）。"));
body.push(step("st-w1", "下载并核验 UNSW-NB15 划分集（见第三章）。"));
body.push(step("st-w1", "统计每个类别样本数量，生成第一张类别分布图。"));
body.push(p("执行命令："));
body.push(cmd(".venv\\Scripts\\activate"));
body.push(cmd("python src/01_eda.py"));
body.push(p("产出位置：报告在 runs/eda/eda_report.md，类别计数在 runs/eda/class_counts.csv，分布图在 figures/class_distribution.png。验收标准：报告能直接读出最多类与最少类的样本数及不平衡比例、数据版本 SHA-256 指纹与完整性结论（已全部达成，报告副本入 reports/week1/ 留痕）。"));

body.push(h2("4.2 第 2 周：预处理与基线"));
body.push(p("目标：完成可复现的预处理流水线，跑通 Logistic Regression 与 XGBoost 两个基线。预处理脚本 02_preprocess.py 按以下顺序实现："));
body.push(step("st-w2", "丢弃 id 列；attack_cat 执行 str.strip()。"));
body.push(step("st-w2", "缺失值处理：确认各列缺失情况后填充或剔除，处理策略写入脚本注释。"));
body.push(step("st-w2", "类别特征编码：proto、service、state 用 one-hot 编码，编码类别表只在训练集上拟合（handle_unknown=ignore 的思路），测试集只做转换。"));
body.push(step("st-w2", "数值特征标准化：StandardScaler 只在训练集上 fit，训练集 transform，测试集仅 transform。"));
body.push(step("st-w2", "划分策略：官方测试集冻结不动；验证集从官方训练集内部再划出（分层抽样 20%），用于调参与模型选择。"));
body.push(step("st-w2", "产出 data/processed/ 下的训练、验证、测试三个文件（parquet 格式），并打印各文件形状与类别分布留档。"));
body.push(p("随后 03_baseline.py 训练两个基线：Logistic Regression（max_iter 放大至收敛）与 XGBoost（多分类，objective=multi:softprob）。输出第一张混淆矩阵图到 figures/confusion_matrix_baseline.png，指标表到 runs/baseline/。"));
body.push(p([{ t: "完成情况（第 2 周，06-23 ~ 06-29）：", b: true }, { t: "预处理与三个基线（LR、XGBoost、XGBoost+类别权重）均已跑通并入库（测试集：LR Macro-F1 0.339；XGBoost 0.510；XGBoost+W 0.512）。类别权重使 Balanced Accuracy 从 0.550 升至 0.655，Backdoor Recall 0.139 升至 0.842、Worms 0.432 升至 0.818，代价是 Accuracy 从 0.769 降至 0.681——这正是研究问题三要量化的权衡。LR 在 Worms、Shellcode、Backdoor 三类 Recall 为 0（完全不预测）；Analysis 类三种模型 Recall 均低于 0.06，加权后主要被误判为 Backdoor，是第 4 周误差分析的重点对象。验证集 Macro-F1 普遍高于测试集约 0.1，说明官方测试集难度更高，论文中报告时以测试集为准并记录该差异。全部指标、配置与划分重叠审计报告的副本入库 reports/week2/，作为第二周证据存档。" }]));
body.push(warn("防泄漏红线：先划分、后处理。SMOTE、过采样、标准化的拟合只允许接触训练集；测试集自始至终只做 transform；测试集不参与任何调参。违反任何一条，全部实验作废重跑。"));

body.push(h2("4.3 第 3 周：不平衡实验矩阵"));
body.push(p("目标：跑完 3 模型 × 4 方法组合，每个组合至少 3 个随机种子（0、1、2），共 36 组实验。矩阵见表 4-2。"));
body.push(tableTitle("表 4-2 不平衡处理方法实验矩阵"));
body.push(tbl(["模型", "无处理", "类别权重", "随机过采样", "SMOTE"],
  [["Logistic Regression", "√", "√", "√", "√"],
   ["XGBoost", "√", "√", "√", "√"],
   ["MLP", "√", "√", "√", "√"]],
  [28, 18, 18, 18, 18]));
body.push(p("实现要点：05_run_experiments.py 用 imblearn Pipeline 封装「重采样只作用于训练数据」，类别权重按模型原生实现（LR 的 class_weight、XGBoost 与 MLP 的 sample_weight），每次运行在 runs/experiments/ 下自动创建「模型_方法_种子」目录，写入 config.json 与 metrics.json；汇总表与稳定性分析由 06_analyze_week3.py 产出。MLP 超参在实验开始前锁定：隐藏层 64×64、max_iter=100、早停、batch 1024。"));
body.push(p([{ t: "完成情况（第 3 周，06-30 ~ 07-06）：36/36 组全部完成、0 失败（证据入库 reports/week3/，含运行日志）。", b: true }, { t: "测试集 Macro-F1（3 种子均值±标准差）：LR 最优 SMOTE 0.3672±0.0007；MLP 最优 ROS 0.4313±0.0037；XGBoost 最优类别权重 0.5123±0.0000。Balanced Accuracy 口径下类别权重在 XGBoost（0.6549）与 MLP（0.6089）上最优，但 LR 上 SMOTE 最优（0.5637，类别权重仅 0.5534）——「类别权重全面占优」的说法不成立（红队复审修正）；两种指标排序不一致本身就是性能权衡的直接证据。SMOTE 对 XGBoost 的 Macro-F1 最低（0.5041，差距仅 0.006 且无显著性检验），但其 Balanced Accuracy（0.6035 对无处理 0.5497）与 DoS Recall（0.4878 对 0.098）反而更高——任何「SMOTE 有害/合成样本引入噪声」的机制论断在本协议下无证据支持，结论必须按指标口径分别陈述。两点披露：LR 与 XGBoost 的 none、class_weight 格子因算法确定性三种种子完全相同（标准差 0，如实记录而非回避）；MLP+ROS 有 1 格触达 max_iter=100 未完全收敛（ConvergenceWarning 1 次），协议统一不放宽以保持 36 格一致，记入局限性。" }]));

body.push(h2("4.4 第 4 周：主要结果与误差分析"));
body.push(p("目标：把 36 组实验汇总成论文主表，回答三个研究问题。补充产出：每个少数类别的 Recall 明细；混淆矩阵图（07_error_analysis.py 按第 3 周均值自动选每模型最优配置重训，输出最优配置混淆矩阵与错误案例导出）；训练时间与推理时间；模型文件大小；3 种子下的均值加减标准差以评估稳定性。"));
body.push(p([{ t: "完成情况（第 4 周，07-07 ~ 07-13，v2 红队复审后）：", b: true }, { t: "选型改按验证集 Macro-F1（遵守第 5.1 节测试集不参与选型的纪律），三模型一致选 SMOTE（验证集 0.4189 / 0.6277 / 0.5337），最优配置混淆矩阵与错误案例（逐条含行哈希与噪声归因）入库 reports/week4/。错误归因（v2，按 attack_cat 冲突口径）：novel 83–84%、conflict 7.4–8.4%（v1 仅按二分类 label 计为 0.6–0.7%，系统性低估约 10 倍，红队 S5）、overlap_clean 8–9%。确定性一致性校验通过：三模型全部错误行「测试预测与训练副本预测」不一致数为 0。与训练划分共享特征向量的测试行（8,154 条）错误率 46–63%，高于整体（27–37%）；重叠行错误的真实类别构成以 Exploits 与 DoS 为主（错分方向的结论仅 XGBoost+SMOTE 的 Exploits→DoS 2,133 条可直接支撑），最大混淆对 Normal→Fuzzers（8,421–11,016 条）。纯模型体积：LR+SMOTE 0.02MB、MLP+SMOTE 0.43MB、XGBoost+SMOTE 8.59MB。研究问题一回答（v2）见 reports/week4/研究问题回答.md：漏检格局是类与方法的强交互且随选型口径变化——验证集选出的三配置（均 SMOTE）DoS Recall 为 0.177/0.488/0.267，而已作废的测试集选型口径下为 0.177/0.171/0.150（LR 两种选型口径下均为 0.177，仅 XGBoost 0.488→0.171 与 MLP 0.267→0.150 改变）；Analysis 在 XGBoost+SMOTE 下 0.053，LR+类别权重下达 0.582；最大混淆对 Normal→Fuzzers。不确定性声明：MLP 为种子方差最大模型且其 SMOTE 格种子 0 为三种子验证最低，MLP 相关百分比为单种子代表性运行。" }]));
body.push(p("本章结束时应当能给出三句话结论：哪些类被漏检（结合混淆矩阵点名列，如 Worms、Shellcode）；三种不平衡方法在 Macro-F1 与少数类 Recall 上的排序及其代价（推理时间、对多数类精确率的影响）；性能与开销的权衡点在哪里。"));

body.push(h2("4.5 第 5 周：轻量化改进"));
body.push(p("目标：只做一个方向，做深做透。推荐「类别权重 + 特征筛选组合」：用互信息或树模型特征重要性筛出前 K 个特征（K 从全量开始减半探索），在精简特征集上重训带类别权重的 XGBoost，与全量特征版本对比 Macro-F1、少数类 Recall、推理时间与模型大小四个维度，给出加速比与体积缩减比例。08_lightweight.py 落实，结果写入 runs/lightweight/。"));
body.push(p([{ t: "完成情况（第 5 周，07-14 ~ 07-20）：", b: true }, { t: "08_lightweight.py 完成「类别权重 XGBoost + 增益重要性特征筛选」（红队 S10 后协议，超参见 configs/experiment_hyperparams.yaml）。筛选排序与选 K 只用训练/验证划分（测试集不进入扫描阶段），K 扫描 [194,128,64,32,16,8] 选出 K*=32（验证 Macro-F1 0.6125，并列取更小 K）。终评（测试集，3 种子）：Macro-F1 0.5087 对全量 0.5123（-0.004）；Balanced Accuracy 0.6605 对 0.6549（+0.006，精简版反而更高）；训练加速 2.52 倍；少数类 Recall 再平衡——Analysis 翻倍（0.058→0.120）、Worms +0.045、DoS +0.026，Backdoor -0.057。诚实负结果：模型体积不降反增 2%（7.82MB 对 7.67MB）——XGBoost 体积由树结构主导，特征筛选不减小树模型体积，「特征筛选能压缩模型」的直觉在本协议下不成立。结论：特征筛选买到的是训练加速与少数类召回的再平衡，买不到体积；轻量化叙事必须按部署目标分述。局限：单次特征排序（seed 42）未做稳定性检验——已由第 8 周方差补测 v2 闭环（per-seed 重切验证集+逐种子重排序：top32−full Macro-F1 差 −0.0022 在切分方差 ±0.005 内，top-32 集合 Jaccard 0.83–0.94；加速 2.67×（fit 为 wall-clock 口径、批间约 2% 波动）、体积负结果复现；每类 Recall 高波动类 Analysis/Backdoor 须附区间表述；见 reports/week5/variance_recheck.md）。结论限定所测协议。" }]));

body.push(h2("4.6 第 6 周：结论稳健性周（07-21 ~ 07-27 修订）"));
body.push(p("原第 6 周仅含多种子与不平衡比例敏感性。红队两轮审计后，第 6 周重定义为「结论稳健性周」：把研究问题二中最有价值的发现（指标口径与选型分割会翻转方法结论）做成可证伪的正式结果，并补齐红队 S7 指出的缺失对照。砍项原则不变：进度落后时先砍外部验证，其余四项为核心交付。"));
body.push(tableTitle("表 4-3 第 6 周任务与预算（修订版）"));
body.push(tbl(["项", "内容", "交付物", "预算"],
  [["A 预注册 τ 检验", "先写预注册文档（假设、统计量、判定标准）再计算：三组 Kendall τ（模型间/指标间/选型分割间的方法排序一致性）+ 完整排序表；如实声明 n=4 方法的小样本局限，τ 与全排序方向一并报告", "reports/week6/rank_stability.md + 预注册文档", "半天"],
   ["B 阈值移动对照（S7 补全）", "none 与类别权重 XGBoost 同参重训，验证集上做每类决策阈值网格搜索（分别以验证 Macro-F1 与少数类宏 Recall 为双目标报告），测试集只终评一次，3 种子；防泄漏纪律原样沿用", "reports/week6/threshold_moving.*", "半天"],
   ["C 哑变量取整敏感性", "SMOTE 合成样本的 one-hot 哑变量列取整（近似约束插值），仅跑 XGBoost 格子 3 种子，检验 one-hot 插值伪影是否翻转主要结论", "reports/week6/smote_rounding.md", "2–3 小时"],
   ["D 不平衡比例敏感性（原计划保留）", "训练集少数类随机降采样至 50%/25%/10%，绘制类别权重与 SMOTE 的性能衰减曲线", "衰减曲线图 + CSV", "一天"],
   ["E 补充修复清单（已完成部分的单列补充，随本周一并执行）", "① 05 脚本改为读取 configs/experiment_hyperparams.yaml，消除超参双源漂移（复攻 TODO#6）；② 误差归因升级 3 种子区间版（K5 TODO#7）；③ 补 none 方法的重叠行错误率对照（S4 TODO#3）；④ 第三轮复攻 sub-agent 抽查 K1/K3/K4 修复句", "各自入 reports/week6/", "半天"]],
  [16, 44, 22, 18]));
body.push(p("外部验证 CIC-IDS2017 仍为可选：仅做最优组合迁移、不重跑全矩阵，且只在 A–E 完成且写作时间富余时启动。第 6 周结束即实验封板，转入第 7 周写作；写作素材新增本表 A、B 两项产出（rank_stability 与阈值移动对照直接进研究问题二、三的正文）。"));
body.push(p([{ t: "完成情况（第 6 周，07-21 ~ 07-27）：A–E 全部完成、0 失败，外部验证按砍项原则放弃，实验封板。", b: true }, { t: "A（τ 检验）：三组平均 τ = 0.111 / 0.278 / 0.111，全部低于预注册 2/3 稳定线（n=4 描述性检验，无 p 值宣称）；异质性显著——LR 选型分割 τ=+1.0 完全稳定、XGBoost τ=-1.0 完全反转、MLP +0.333 弱正，结论应表述为「排序稳定性高度依赖模型」而非「全部排序不稳定」。B（阈值移动）：none+阈值移动以零重训练成本达到 Macro-F1 0.5483、少数类宏 Recall 0.483，为全项目最高 Macro-F1、超过全部 12 个模型×方法格的 3 种子均值（最高 XGBoost+类别权重 0.5123）与全部 36 个单次运行值（最高 XGBoost+ROS seed0 0.5146；类别权重+阈值移动 3 种子均值 0.5295）；阈值移动为验证集调参的后处理，与训练期不平衡处理机制不同；同时诚实记录以少数类为目标调阈值的迁移失败案例（测试 0.672→0.452）。C（取整敏感性）：Macro-F1/Balanced Acc 对插值伪影稳健（差 0.002，相对方法间差距可忽略），DoS Recall 中度敏感（-0.05，3/3 种子方向一致；但 SMOTE 取整 0.438 仍远高于 none 0.098，方法排序不变）。D（比例衰减）：Macro-F1 仅在 p≥0.25 口径稳健（降幅 <0.02；p=0.10 none 降幅 0.0417 已超准则），少数类宏 Recall 持续流失（p=0.25：cw 0.672→0.535；p=0.10：cw 0.355、none 0.160）。方差补测 v2（第 8 周，用户决策 T4/T14）：per-seed 重切验证集下 p≥0.25 的 Macro-F1 稳健性在真实 std（0.003–0.009）中成立、p=0.10 不稳健（降幅 0.028–0.054）；新增 SMOTE 衰减曲线，其少数类宏 Recall 恒介于 none 与 cw 之间（reports/week6/imbalance_decay_v2.md）。阈值移动 v2：none+macro_f1 moved 0.5436±0.0063，最差种子 0.5367 仍超全部格点均值 0.5123 与单次运行最高 0.5146——头部结论获得方差背书（reports/week6/threshold_moving_v2.md）。E：① 05 读 configs（36/36 缓存一致）② 归因 3 种子区间（novel 82.8–84.4%、conflict 7.3–8.6%、overlap 8.0–9.3%，最大波动 0.6pp——第 4 周归因为稳定结论）③ none 重叠行对照（44.2% 为整体 1.9 倍，高错误率主体是重叠行自身难度）。全部证据入 reports/week6/。" }]));

body.push(h2("4.7 第 7 周：论文初稿"));
body.push(p("按学校模板写作，结构共八节：引言、相关工作、数据集与问题定义、方法与实验设置、实验结果、误差分析、局限性、结论。写作顺序上先写实验设置与实验结果（素材最全），再写方法与数据集，然后相关工作，最后写引言与结论——引言里的贡献点要等实验定型后才能精确表述。图表要求：每张图与表配自明图注，正文引用编号一致；混淆矩阵图统一配色与字号。"));

body.push(h2("4.8 第 8 周：修改、评优对齐与答辩准备"));
body.push(step("st-w8", "请导师或师兄审阅初稿，按意见修正图表与结论表述。"));
body.push(step("st-w8", "与导师对齐评优三件事：本院优秀比例与往届标准、推荐流程时间点、论文格式与查重要求。"));
body.push(step("st-w8", "整理代码仓库：README 补齐复现步骤，固定随机种子，保证一键跑通。"));
body.push(step("st-w8", "制作答辩 PPT：按三个研究问题组织，每个问题一句话结论配一张图。"));
body.push(step("st-w8", "可选：挂 ChinaXiv 预印本（无门槛）；arXiv cs.CR 需要已有发表人 endorsement，可请导师协助。预印本服务于复试展示，不是评优的必要条件。"));

// 第五章
body.push(h1("第五章 质量红线与每周自查"));
body.push(h2("5.1 防泄漏三原则"));
body.push(p("第一，任何重采样（SMOTE、随机过采样）与任何拟合（标准化、编码表、特征筛选）只允许在训练集上执行；第二，验证集只用于调参与模型选择，测试集只在最终评估时使用一次；第三，官方测试集冻结，不得因结果不好而更换或重划。"));
body.push(h2("5.2 每周自查清单"));
body.push(tableTitle("表 5-1 高危错误自查表（每周五过一遍）"));
body.push(tbl(["序号", "自查项", "不合格后果"],
  [["1", "SMOTE 或过采样是否接触了测试/验证集", "数据泄漏，全部实验作废"],
   ["2", "测试集是否参与了调参", "结果虚高，论文不可信"],
   ["3", "是否只报告了 Accuracy", "结论无效，需换主指标重写"],
   ["4", "是否只运行了一个随机种子", "结论不稳，需补 3 种子"],
   ["5", "是否把「类别权重 + SMOTE」称为原创算法", "学术定位失实，必须改正"],
   ["6", "是否报告了失败案例与误差分析", "论文深度不足"],
   ["7", "每次实验是否保存了配置与日志", "结果无法复现"],
   ["8", "attack_cat 是否做了 strip", "类别统计错乱"],
   ["9", "原始数据文件是否被修改过", "违反只读纪律，重新下载"],
   ["10", "主指标是否齐全（Macro-F1、Balanced Accuracy、每类 Recall）", "实验设置章节要重写"]],
  [8, 52, 40]));
body.push(h2("5.3 指标规范"));
body.push(p("主指标为 Macro-F1、Balanced Accuracy、每个少数类别的 Recall、混淆矩阵、推理时间与模型文件大小；Accuracy 只作辅助指标，任何结论不得单独依赖 Accuracy。多数类占绝对多数时，Accuracy 接近恒高，不具备区分度。"));
body.push(h2("5.4 红队对抗面板（paper-red-team）"));
body.push(p("为防止作者自我审查的盲区，本项目引入独立 sub-agent 对抗面板：每个攻击者是完全独立的子代理，只接收攻击简报与证据文件路径（不接收作者的推理过程），只读不改，结构化返回问题清单（每条附文件与数字出处）；主代理逐条裁决为 FIX（立即修复）、RISK（转为局限性表述）、REFUTED（附反驳证据保留）、TODO（转入实验计划），台账随仓库提交至 reports/redteam/。攻击者简报含反讨好条款：至少给出 3 个带出处的问题，否则视为无效审稿重派。"));
body.push(p([{ t: "首轮战果（第 4-5 周，evidence 模式，统计审查员）：", b: true }, { t: "3 条 critical、5 条 major、2 条 minor。critical 均为真问题并已修复——其一，「类别权重 Balanced Accuracy 全面最优」系数字张冠李戴（LR 上 SMOTE 0.5637 高于类别权重 0.5534，该结论对 LR 不成立）；其二，「DoS 是所有方法都救不了的类」过度概括（XGBoost+SMOTE 的 DoS Recall 实为 0.4878，是被忽略网格格子的近 3 倍）；其三，第 4 周选型误用了测试集 Macro-F1（违反本手册第 5.1 节纪律），已改为验证集选型并重跑全部误差分析。统计审查员同时确认了 5 项检查干净项（36 组指标可从 metrics.json 逐一重算复原、防泄漏纪律属实、确定性校验为真实硬约束等）。攻击者与作者分离的价值在本轮得到直接验证：三处关键错误全部是主代理自查多轮未发现的。" }]));

// 第六章
body.push(h1("第六章 AI 协作分工"));
body.push(p("AI 可承担全部机械执行工作，但实验设计判断、结果可信度审查与论文最终表述必须自己掌握，否则复试被追问细节时无法应对。分工上限见表 6-1。"));
body.push(tableTitle("表 6-1 AI 分工上限表"));
body.push(tbl(["任务", "可交 AI 比例", "说明"],
  [["环境、目录、Git、依赖", "约 100%", "纯机械劳动，可放心委托"],
   ["数据清洗、编码、划分脚本", "80%–90%", "泄漏检查逻辑必须自己能复述"],
   ["实验跑批、多种子、日志", "约 90%", "先人工跑通最小版本，再批量扩展"],
   ["图表与表格", "约 90%", "注意图注自明与统一风格"],
   ["论文初稿", "60%–70%", "引言、结论、误差分析的归因必须自己重写"],
   ["相关工作综述", "约 50%", "AI 会编造文献，每条引用必须核对原文"],
   ["实验设计决策与异常判断", "20% 以下", "必须自己主导"]],
  [30, 18, 52]));
body.push(p("推荐工作循环：让 AI 产出候选方案与代码，人工审查并亲手跑最小验证，确认无误后再交还 AI 批量扩展。凡是答辩中可能被追问的环节（数据如何划分、指标为何这样选、某个数字怎么来的），必须自己至少完整做一遍。"));

// 第七章
body.push(h1("第七章 进度记录"));
body.push(p("每次完成阶段性工作后在表 7-1 追加一行，作为周报与论文「工作过程」素材。"));
body.push(tableTitle("表 7-1 进度记录"));
body.push(tbl(["日期", "完成事项", "产出与备注"],
  [["第 1 周 06-16", "仓库初始化、目录骨架、虚拟环境与依赖、数据集许可记录、EDA 脚本、本手册", "首个提交：README、requirements.txt、src/01_eda.py"],
   ["第 1 周 06-18", "数据下载与核验（训练集曾截断，断点续传后达标）、发表级 EDA 补强", "行数 175,342/82,333；EDA 新增 SHA-256 指纹、重复行与标签冲突检查"],
   ["第 1 周 06-21", "第 1 周审计修复：留痕目录、数据版本指纹、环境锁定、官方核对待办", "reports/week1/（报告+SHA256SUMS.txt+环境版本）、requirements.lock.txt、data/README 版本节"],
   ["第 2 周 06-23", "第 2 周启动：防泄漏预处理 + 三个基线 + 第一张混淆矩阵", "02_preprocess.py（140,272/35,069/82,332）、03_baseline.py（XGB+W 使 Balanced Acc 0.550→0.655）、figures/confusion_matrix_baseline.png"],
   ["第 2 周 06-27", "第 2 周复审修复：recall 列名纠正、环境锁补 pyarrow、划分重叠审计、证据入库", "reports/week2/（指标/配置/预处理报告/重叠审计）、04_split_overlap_audit.py、requirements.lock.txt 更新"],
   ["第 3 周 07-01", "第 3 周：3 模型 × 4 方法 × 3 种子 = 36 组全部完成（0 失败）", "runs/experiments/（36 目录）、reports/week3/（稳定性表/每类Recall/运行日志等 6 件）、figures/method_comparison_macroF1.png"],
   ["第 4 周 07-08", "第 4 周：误差分析——验证集选型（三模型一致 SMOTE）混淆矩阵、错误噪声归因、纯模型体积、三问回答", "reports/week4/（4 件）、figures/confusion_matrix_best.png；归因 novel 83–84%/conflict 7.4–8.4%/overlap 8–9%（v2 attack_cat 口径），确定性校验 0 不一致"],
   ["第 4-5 周 07-12", "红队两轮（evidence 模式）：首轮 3 critical 属实并修复；复攻+方法审稿人二轮 11 项（v1 残留清理、MLP 单种子限制披露、开销倍数修正 2.3–5.9 倍）", "reports/redteam/ 台账两轮留痕、configs/experiment_hyperparams.yaml、paper-red-team skill 入库"],
   ["第 5 周 07-15", "第 5 周：轻量化（类别权重 XGBoost + 特征筛选，验证集选 K*=32）", "runs/lightweight/（sweep/终评/特征重要性）、reports/week5/、figures/lightweight_tradeoff.png；加速 2.52×、Balanced Acc +0.006、Analysis Recall 翻倍、体积 +2%（负结果如实报告）"],
   ["（待填）", "", ""]],
  [16, 44, 40]));

// ── 组装文档 ──
const numberingConfig = ["st-data", "st-w1", "st-w2", "st-w8"].map(ref => ({
  reference: ref,
  levels: [{
    level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } },
  }],
}));

const doc = new Document({
  numbering: { config: numberingConfig },
  styles: {
    default: {
      document: {
        run: { font: F_BODY, size: 24, color: "000000" },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: F_HEAD, size: 32, bold: true, color: P.primary },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 },
      },
      heading2: {
        run: { font: F_HEAD, size: 28, bold: true, color: P.primary },
        paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 1 },
      },
      heading3: {
        run: { font: F_HEAD, size: 24, bold: true, color: P.primary },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 },
      },
    },
  },
  sections: [
    { // 封面
      properties: {
        page: { size: { width: 11906, height: 16838 }, margin: { top: 0, bottom: 0, left: 0, right: 0 } },
      },
      children: buildCoverR4({
        palette: P,
        title: "毕设论文流程与实验执行手册",
        subtitle: "面向类别不平衡的网络入侵检测方法比较与轻量化改进研究",
        englishLabel: "PROJECT PLAYBOOK",
        metaLines: [
          "数据集：UNSW-NB15（官方划分集）",
          "研究周期：12 周（2026 年 6 月 至 9 月，第 12 周 09-07 定稿）",
          "仓库：github.com/ausyeah/graduate-article",
          "负责人：【你的姓名】",
        ],
        footerLeft: "本科毕业设计 · 内部执行文档",
        footerRight: "2026-09-07",
      }),
    },
    { // 目录（罗马页码）
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
          pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN },
        },
      },
      footers: { default: pageFooter() },
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 480, after: 360 },
          children: [new TextRun({ text: "目  录", bold: true, size: 32, font: F_HEAD })],
        }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({
          spacing: { before: 200 },
          children: [new TextRun({
            text: "注：本目录由域代码生成。编辑后如需更新页码，请在目录上点击右键并选择「更新域」。",
            italics: true, size: 18, color: "888888", font: F_BODY })],
        }),
      ],
    },
    { // 正文（阿拉伯页码从 1 起）
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
          pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL },
        },
      },
      headers: { default: pageHeader() },
      footers: { default: pageFooter() },
      children: body,
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(process.argv[2] || "output.docx", buf);
  console.log("DOCX generated:", process.argv[2] || "output.docx");
});
