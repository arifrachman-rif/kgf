import re

with open("scratch/wa_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

if "canvas" in html and "qr" in html.lower():
    print("STATUS: Meminta pemindaian QR Code (Sesi terputus/usang).")
elif 'title="Agung Pevesindo Haeruddin"' in html:
    print("STATUS: Kontak Agung ditemukan di layar!")
elif 'aria-label="Search"' in html or 'placeholder="Search' in html:
    print("STATUS: Kotak pencarian tersedia, tapi locators mungkin berubah.")
else:
    print("STATUS: Tidak diketahui. Mungkin layar memuat terlalu lama atau terjadi error.")
