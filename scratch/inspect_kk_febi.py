import os
import pypdf

pdf_path = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara/febi_kurniawan_kk.pdf"

if os.path.exists(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total pages: {len(reader.pages)}")
    for i, page in enumerate(reader.pages):
        print(f"--- Page {i+1} ---")
        text = page.extract_text()
        print(text[:1000])
else:
    print("File not found.")
