# 手册（.docx）生成工具链

《毕设流程与实验执行手册》由 docx-js 脚本生成，改内容→重新生成→机器检查→渲染验收，四步全部可复现。

## 文件

- `generate.js` — 手册全文内容与排版（docx-js）。改手册文字只动这个文件。
- `postprocess_footers.py` — 后处理：删封面空 pgNumType、按节给页脚 PAGE 域补 ROMAN/arabic 开关。
- `export_pdf.ps1` — 通过 Word COM 把 docx 导出 PDF（路径必须纯 ASCII，中文路径会触发 PowerShell 编码 bug，先复制到英文路径再导出）。
- `render_png.py` — pypdfium2 把 PDF 逐页渲染 PNG 供视觉检查。

## 复现步骤

```bash
npm install docx --registry=https://registry.npmmirror.com   # 在本目录
node generate.js <输出.docx 绝对路径>
python "$DOCX_SCRIPTS/add_toc_placeholders.py" <docx> --auto   # 目录占位条目（skill 自带脚本）
python postprocess_footers.py <docx>
python "$DOCX_SCRIPTS/postcheck.py" <docx>                     # 机器检查，需 0 错误
cp <docx> playbook.docx && powershell -File export_pdf.ps1 && python render_png.py
```

`$DOCX_SCRIPTS` 指向 docx skill 的 scripts 目录（含 add_toc_placeholders.py / postcheck.py）。

## 质量标准

- postcheck 0 错误才可入库；
- 所有标题 keepNext（不得孤悬页底）；
- 表格 tableHeader + cantSplit + 百分比列宽；
- 无 Markdown 残留、无未转义中文弯引号（用「」替代）。
