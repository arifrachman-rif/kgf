python3 -m venv myenv
source myenv/bin/activate
pip install python-docx

cat << 'PYEOF' > modify.py
from docx import Document

try:
    doc = Document('/mnt/c/Users/rifra/Downloads/Harga penawaran Slice dried White Ginger.docx')
    doc.add_heading('Tambahan Penawaran Komoditas', level=2)
    
    doc.add_paragraph('Lampung Black Pepper\nDensity: 500 G/L\nMC Max: 13%\nFM Max: 1%\nPrice: Rp 125,000/kg')
    doc.add_paragraph('Robusta Coffee Grade 1\nMC: 13%\nPrice: Rp 85,000/kg')
    doc.add_paragraph('Robusta Coffee Grade 3\nMC: 13%\nPrice: Rp 82,000/kg')
    
    doc.save('/mnt/c/Users/rifra/Downloads/Harga Bu Diska.docx')
    print("Dokumen Harga Bu Diska.docx berhasil dibuat!")
except Exception as e:
    print(f"Error: {e}")
PYEOF

python3 modify.py
