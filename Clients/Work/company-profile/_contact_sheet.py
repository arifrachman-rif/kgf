"""Build a numbered contact sheet from a directory of images, so a whole shoot
can be reviewed in one look instead of opened one file at a time."""
import sys, os
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
cell, pad, label = 380, 10, 26

names = sorted(f for f in os.listdir(src)
               if f.lower().endswith((".jpg", ".jpeg", ".png")))
rows = (len(names) + cols - 1) // cols
W = cols * (cell + pad) + pad
H = rows * (cell + label + pad) + pad
sheet = Image.new("RGB", (W, H), (24, 24, 24))
draw = ImageDraw.Draw(sheet)

for i, n in enumerate(names):
    im = Image.open(os.path.join(src, n))
    im.thumbnail((cell, cell), Image.LANCZOS)
    cx = pad + (i % cols) * (cell + pad)
    cy = pad + (i // cols) * (cell + label + pad)
    sheet.paste(im, (cx + (cell - im.width) // 2, cy + (cell - im.height) // 2))
    draw.text((cx + 4, cy + cell + 6), f"{i + 1:02d}  {n[:8]}", fill=(230, 230, 230))

sheet.save(out, quality=88)
print("saved", out, sheet.size, "|", len(names), "images")
for i, n in enumerate(names):
    print(f"  {i + 1:02d}  {n}")
