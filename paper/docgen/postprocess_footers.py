"""docx 后处理：1) 删除封面节的空 <w:pgNumType/>；2) 按节顺序给页脚 PAGE 域补格式开关。

节顺序：1=封面（无页脚） 2=目录（ROMAN） 3=正文（arabic）
"""
import re
import shutil
import sys
import zipfile

path = sys.argv[1]
tmp = path + ".tmp"

with zipfile.ZipFile(path, "r") as zin:
    names = zin.namelist()
    data = {n: zin.read(n) for n in names}

doc = data["word/document.xml"].decode("utf-8")
doc = doc.replace("<w:pgNumType/>", "")

# 按文档顺序找 sectPr 的 default footerReference
sect_blocks = re.findall(r"<w:sectPr[ >].*?</w:sectPr>", doc, flags=re.S)
footer_ids = []
for blk in sect_blocks:
    m = re.search(r'<w:footerReference w:type="default" r:id="(rId\d+)"', blk)
    footer_ids.append(m.group(1) if m else None)
print("sections:", len(sect_blocks), "footer ids:", footer_ids)

rels = data["word/_rels/document.xml.rels"].decode("utf-8")
id2target = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels))

def patch_footer(target, fmt):
    name = "word/" + target
    xml = data[name].decode("utf-8")
    xml, n = re.subn(
        r'(<w:instrText[^>]*>)\s*PAGE\s*(</w:instrText>)',
        r"\1 PAGE \\* " + fmt + r" \\* MERGEFORMAT \2",
        xml,
    )
    data[name] = xml.encode("utf-8")
    print(f"patched {name} with {fmt} ({n} fields)")

plan = {1: "ROMAN", 2: "arabic"}
for idx, fmt in plan.items():
    if idx < len(footer_ids) and footer_ids[idx]:
        patch_footer(id2target[footer_ids[idx]], fmt)

data["word/document.xml"] = doc.encode("utf-8")

with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for n in names:
        zout.writestr(n, data[n])
shutil.move(tmp, path)
print("postprocess done")
