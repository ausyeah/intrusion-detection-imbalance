import sys
sys.path.insert(0, r"D:\ZCode-work\.zcode\workspace\default\docgen\pylibs")
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument(r"D:\ZCode-work\.zcode\workspace\default\docgen\playbook.pdf")
n = len(pdf)
for i in range(n):
    page = pdf[i]
    bitmap = page.render(scale=2.0)
    img = bitmap.to_pil()
    img.save(rf"D:\ZCode-work\.zcode\workspace\default\docgen\page-{i+1:02d}.png")
print(f"RENDERED {n} pages")
