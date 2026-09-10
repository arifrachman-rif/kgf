import os
import pypdf

pdf_path = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara/febi_kurniawan_kk.pdf"

if os.path.exists(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    page = reader.pages[0]
    count = 0
    for img_obj in page.images:
        out_name = f"scratch/febi_kk_img_{count}.png"
        with open(out_name, "wb") as f:
            f.write(img_obj.data)
        print(f"Extracted image: {out_name}")
        count += 1
