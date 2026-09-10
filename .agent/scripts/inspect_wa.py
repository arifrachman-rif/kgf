import re

with open("/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/wa_dom_visible.html", "r", encoding="utf-8") as f:
    html = f.read()

matches = re.finditer(r'.{0,100}contenteditable.{0,150}', html, re.IGNORECASE)
print("Ditemukan elemen berikut:")
for i, m in enumerate(matches):
    print(f"\n--- Elemen {i+1} ---")
    print(m.group(0))
