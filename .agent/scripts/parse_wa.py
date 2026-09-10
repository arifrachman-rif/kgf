from bs4 import BeautifulSoup

with open("/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/wa_dom_visible.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

inputs = soup.find_all(['input', 'textarea'])
print("Inputs:", len(inputs))

contenteditables = soup.find_all(attrs={"contenteditable": True})
print("Contenteditables:", len(contenteditables))

# Khusus mencari div dengan contenteditable "true" (sebagai string)
contenteditables_str = soup.find_all(attrs={"contenteditable": "true"})
print("Contenteditables (str 'true'):", len(contenteditables_str))

textboxes = soup.find_all(attrs={"role": "textbox"})
print("Role textboxes:", len(textboxes))

canvases = soup.find_all('canvas')
print("Canvases:", len(canvases))
