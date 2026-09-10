"""Banner konsorsium KGF: foto kebun agroforestry + logo mitra.

Dibuat 31 Agustus 2026. Foto asli dari kunjungan lapangan (_visit_raw),
bukan gambar hasil AI. Jalankan ulang untuk mengubah ukuran atau urutan logo.
"""
from PIL import Image, ImageDraw, ImageFilter

W, H = 2400, 820
BAR = 230                      # tinggi bilah putih tempat logo
PHOTO_H = H - BAR
A = "assets_from_c3"
BG = "_visit_raw/B7DA6AD2-8DF4-4CA8-9901-6244FE0216D7_1_105_c.jpeg"

def fit(path, h):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)

# --- latar: foto kebun, di-crop panoramik ---
src = Image.open(BG).convert("RGB")
scale = max(W / src.width, PHOTO_H / src.height)
src = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)
top = round((src.height - PHOTO_H) * 0.55)     # geser turun: kaki orang tidak terpotong
photo = src.crop((0, top, W, top + PHOTO_H))

canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
canvas.paste(photo, (0, 0))

# gradasi gelap di bawah supaya batas ke bilah putih tidak mentah
grad = Image.new("L", (1, PHOTO_H))
for y in range(PHOTO_H):
    t = max(0.0, (y - PHOTO_H * 0.55) / (PHOTO_H * 0.45))
    grad.putpixel((0, y), int(120 * t ** 1.6))
shade = Image.new("RGBA", (W, PHOTO_H), (12, 34, 18, 255))
shade.putalpha(grad.resize((W, PHOTO_H)))
canvas.alpha_composite(shade, (0, 0))

# --- bilah logo ---
d = ImageDraw.Draw(canvas)
d.rectangle([0, PHOTO_H, W, H], fill=(255, 255, 255, 255))
d.rectangle([0, PHOTO_H, W, PHOTO_H + 6], fill=(198, 163, 26, 255))   # garis emas aGROWforests

PAD, CY = 80, PHOTO_H + BAR // 2

# kiri: KGF
kgf = fit(f"{A}/logo_kgf.png", 168)
canvas.alpha_composite(kgf, (PAD, CY - kgf.height // 2))

# kanan: mitra konsorsium
partners = [
    (f"{A}/logo_agrowforests_tr.png", 150),
    (f"{A}/logo_ssii.png", 104),
    (f"{A}/logo_giz_tr.png", 92),
    (f"{A}/logo_solidaridad_dark.png", 58),
]
logos = [fit(p, h) for p, h in partners]
GAP = 72
total = sum(l.width for l in logos) + GAP * (len(logos) - 1)
x = W - PAD - total
for l in logos:
    canvas.alpha_composite(l, (x, CY - l.height // 2))
    x += l.width + GAP

# pemisah tipis antara KGF dan mitra
sep = PAD + kgf.width + 60
d.line([sep, CY - 62, sep, CY + 62], fill=(210, 210, 210, 255), width=3)

out = "KGF_banner_konsorsium.png"
canvas.convert("RGB").save(out, quality=95)
print("tersimpan:", out, canvas.size)
