"""Stamp a "DevOps Interview Guide · ARTM  n / N" footer on every page of a PDF.
Usage: add_footer.py <input.pdf> <output.pdf>  (called by build-pdf.sh)"""
import sys, io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
src, out = sys.argv[1], sys.argv[2]
r = PdfReader(src); w = PdfWriter(); n = len(r.pages)
for i, p in enumerate(r.pages, 1):
    W, H = float(p.mediabox.width), float(p.mediabox.height)
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
    c.setFont("Helvetica", 7.5); c.setFillColorRGB(0.45, 0.5, 0.58)
    c.drawString(50, 28, "DevOps Interview Guide · ARTM"); c.drawRightString(W - 50, 28, f"{i} / {n}")
    c.save(); buf.seek(0)
    p.merge_page(PdfReader(buf).pages[0]); w.add_page(p)
w.add_metadata({"/Title": "DevOps Interview Guide ARTM"})
with open(out, "wb") as f: w.write(f)
print(n, "pages")
