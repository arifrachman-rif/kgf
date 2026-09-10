import os
import fitz # PyMuPDF

pdf_path = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara/febi_kurniawan_kk.pdf"
out_img = "scratch/febi_kk_view.png"

if os.path.exists(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    pix.save(out_img)
    print(f"Saved PDF page 1 to {out_img}")
else:
    print("PDF path not found.")
