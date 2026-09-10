import re

with open("/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/wa_dom_visible.html", "r", encoding="utf-8") as f:
    html = f.read()

print("contenteditable:", len(re.findall(r'contenteditable', html, re.IGNORECASE)))
print("role=textbox:", len(re.findall(r'role=[\'"]textbox[\'"]', html, re.IGNORECASE)))
print("<input:", len(re.findall(r'<input', html, re.IGNORECASE)))
print("Faizal:", len(re.findall(r'Faizal', html, re.IGNORECASE)))
print("Cari:", len(re.findall(r'Cari', html, re.IGNORECASE)))
print("Search:", len(re.findall(r'Search', html, re.IGNORECASE)))
print("canvas:", len(re.findall(r'<canvas', html, re.IGNORECASE)))
