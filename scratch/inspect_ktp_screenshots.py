import os
import pytesseract
from PIL import Image

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
files = [f for f in os.listdir(ktp_dir) if f.startswith("Screenshot")]

print(f"Inspecting {len(files)} screenshot files in KTP folder:")

for f in sorted(files):
    p = os.path.join(ktp_dir, f)
    try:
        txt = pytesseract.image_to_string(Image.open(p))
        lines = [l.strip() for l in txt.split("\n") if l.strip()]
        print(f"\n--- {f} ---")
        for line in lines:
            if any(k in line.lower() for k in ['nama', 'nik', 'fadhilah', 'kurniawan', 'taufik', 'ruly', 'hendro', 'duta', 'febi']):
                print("  Found:", line)
            elif len(line.split()) >= 2 and not any(c in line for c in ['1','2','3','4','5','6','7','8','9','0']):
                print("  Text:", line)
    except Exception as e:
        print(f"Error OCR on {f}: {e}")
