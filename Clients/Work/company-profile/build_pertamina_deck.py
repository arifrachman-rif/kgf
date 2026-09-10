"""Bangun profil perusahaan KGF edisi Pertamina UMK Academy 2026.

Bahasa Indonesia. Audiensnya penilai program pemberdayaan, bukan pembeli dan
bukan investor, jadi urutannya: siapa kami, dari mana kami mulai, apa yang sudah
berjalan, lalu apa yang kami cari dari program.

Sumbu penyusunan: UMK Academy 2026 menambahkan materi Go Green dan Go Aggregator
di samping Go Modern, Go Digital, Go Online dan Go Global. KGF sudah menjalankan
agregasi petani, praktik hijau, penelusuran digital dan ekspor, jadi tiap halaman
inti dipetakan ke salah satu kelas itu lewat penanda di pojok kanan judul.

Design system diwarisi dari build_icif_deck.py. Jangan dibuat ulang di sini.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import sys, os as _os
OUT = "Clients/Work/company-profile/KGF_Company_Profile_PERTAMINA_UMK_2026.pptx"
if _os.path.exists(OUT):
    try:
        open(OUT, "r+b").close()
    except PermissionError:
        OUT = "Clients/Work/company-profile/KGF_Company_Profile_PERTAMINA_UMK_2026_v2.pptx"
ASSETS = "Clients/Work/company-profile/assets_from_c3/"
VISIT  = "Clients/Work/company-profile/assets_visit/"
import os

INK   = RGBColor(0x14, 0x1D, 0x18)
GREEN = RGBColor(0x1F, 0x40, 0x34)
GOLD  = RGBColor(0x9A, 0x75, 0x26)
MUTED = RGBColor(0x6C, 0x7A, 0x72)
BODY  = RGBColor(0x3D, 0x4A, 0x43)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xEF, 0xF3, 0xEE)
PHOTO = RGBColor(0xE7, 0xE0, 0xCE)
RULE  = RGBColor(0xB9, 0xC7, 0xBE)
FLAG  = RGBColor(0xFD, 0xF3, 0xD8)

SERIF = "Georgia"
SANS  = "Segoe UI"

S_HEAD, S_STAT, S_SUB, S_BODY, S_LABEL, S_CAP = 36, 32, 20, 16, 13, 11
M = 0.72
RIGHT = 13.33 - 0.72

PLACEHOLDERS = []

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = WHITE; bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def txt(s, x, y, w, h, content, size=S_BODY, bold=False, color=BODY,
        font=SANS, align=PP_ALIGN.LEFT, space=0, caps=False, line=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate(content.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line: p.line_spacing = line
        r = p.add_run(); r.text = ln.upper() if caps else ln
        f = r.font
        f.size = Pt(size); f.bold = bold; f.color.rgb = color; f.name = font
        if space:
            from pptx.oxml.ns import qn
            r.font._rPr.set('spc', str(int(space * 100)))
    return tb


def rect(s, x, y, w, h, color, line_color=None):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = color
    if line_color:
        sh.line.color.rgb = line_color; sh.line.width = Pt(0.75)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def header(s, num, label, headline, kelas=None, hl_size=None):
    """Eyebrow bernomor, garis rambut, tik emas, judul. `kelas` menempelkan
    penanda kelas UMK Academy di ujung kanan garis."""
    if hl_size is None:
        hl_size = S_HEAD if len(headline) <= 44 else S_STAT
    txt(s, M, 0.62, 6.0, 0.3, f"{num}   {label}", S_LABEL, False, GOLD, SANS,
        space=1.4, caps=True)
    if kelas:
        txt(s, RIGHT - 4.2, 0.62, 4.2, 0.3, kelas, S_CAP, True, GREEN, SANS,
            PP_ALIGN.RIGHT, space=1.2, caps=True)
    rect(s, M, 0.90, RIGHT - M, 0.012, RULE)
    rect(s, M, 0.895, 0.44, 0.022, GOLD)
    txt(s, M, 1.12, 11.89, 1.30, headline, hl_size, True, INK, SERIF, line=1.12)


def photo(s, x, y, w, h, caption, img=None, label=None, fit="cover"):
    path = None
    for root in (ASSETS, VISIT):
        if img and os.path.exists(root + img):
            path = root + img
            break
    if path:
        pic = s.shapes.add_picture(path, Inches(x), Inches(y))
        nat = pic.width / pic.height
        tgt = w / h
        if fit == "cover":
            if nat > tgt:
                c = (1 - tgt / nat) / 2
                pic.crop_left = c; pic.crop_right = c
            else:
                c = (1 - nat / tgt) / 2
                pic.crop_top = c; pic.crop_bottom = c
            pic.left, pic.top = Inches(x), Inches(y)
            pic.width, pic.height = Inches(w), Inches(h)
        else:
            if nat > tgt:
                nw, nh = w, w / nat
            else:
                nh, nw = h, h * nat
            pic.width, pic.height = Inches(nw), Inches(nh)
            pic.left = Inches(x + (w - nw) / 2)
            pic.top = Inches(y + (h - nh) / 2)
        if label:
            rect(s, x, y + h - 0.30, w, 0.30, GREEN)
            txt(s, x + 0.12, y + h - 0.245, w - 0.24, 0.22, label, S_CAP, True,
                WHITE, SANS, caps=True, space=0.9)
        return
    rect(s, x, y, w, h, PHOTO, RULE)
    txt(s, x + 0.18, y + h / 2 - 0.28, w - 0.36, 0.56, caption, S_CAP, False,
        GOLD, SANS, PP_ALIGN.CENTER, caps=True, space=0.8)


def scrim(s, x, y, w, h, hexcol="1F4034"):
    from pptx.oxml.ns import qn
    from lxml import etree
    sh = rect(s, x, y, w, h, GREEN)
    spPr = sh._element.spPr
    for tag in ("a:solidFill", "a:noFill", "a:gradFill"):
        el = spPr.find(qn(tag))
        if el is not None:
            spPr.remove(el)
    xml = ('<a:gradFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
           'rotWithShape="1"><a:gsLst>'
           f'<a:gs pos="0"><a:srgbClr val="{hexcol}"><a:alpha val="100000"/></a:srgbClr></a:gs>'
           f'<a:gs pos="42000"><a:srgbClr val="{hexcol}"><a:alpha val="92000"/></a:srgbClr></a:gs>'
           f'<a:gs pos="72000"><a:srgbClr val="{hexcol}"><a:alpha val="55000"/></a:srgbClr></a:gs>'
           f'<a:gs pos="100000"><a:srgbClr val="{hexcol}"><a:alpha val="0"/></a:srgbClr></a:gs>'
           '</a:gsLst><a:lin ang="0" scaled="0"/></a:gradFill>')
    spPr.find(qn("a:prstGeom")).addnext(etree.fromstring(xml))
    return sh


def node(s, x, y, w, h, title, sub, fill=WHITE, line=GREEN, tcol=INK, scol=BODY):
    b = rect(s, x, y, w, h, fill, line)
    txt(s, x + 0.16, y + 0.13, w - 0.32, 0.28, title, S_LABEL, True, tcol, SANS,
        PP_ALIGN.CENTER, caps=True, space=0.9)
    txt(s, x + 0.16, y + 0.47, w - 0.32, 0.34, sub, S_LABEL, False, scol, SANS,
        PP_ALIGN.CENTER)
    return b


def arrow(s, x, y, w, h=0.22, color=None):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    a.fill.solid(); a.fill.fore_color.rgb = color or GOLD
    a.line.fill.background(); a.shadow.inherit = False
    return a


def statblock(s, x, y, w, value, label):
    txt(s, x, y, w, 0.62, value, S_STAT, True, GREEN, SERIF)
    txt(s, x, y + 0.62, w, 0.3, label, S_CAP, False, MUTED, SANS, caps=True, space=1.0)


def card(s, x, y, w, h, title, body, accent=True):
    if accent: rect(s, x, y, 0.03, h, GOLD)
    txt(s, x + 0.24, y, w - 0.24, 0.74, title, S_SUB, True, INK, SANS, line=1.14)
    txt(s, x + 0.24, y + 0.84, w - 0.24, h - 0.84, body, S_BODY, False, BODY, SANS, line=1.32)


def todo(s, x, y, w, what, page):
    PLACEHOLDERS.append((page, what))
    rect(s, x, y, w, 0.34, FLAG, GOLD)
    txt(s, x + 0.14, y + 0.07, w - 0.28, 0.24, "[ LENGKAPI: " + what + " ]",
        S_CAP, True, GOLD, SANS, space=0.6)


def footer(s, page):
    txt(s, M, 7.02, 8.6, 0.26,
        "PT KLUMBAYAN GOLD FARM   ·   PERTAMINA UMK ACADEMY 2026",
        S_CAP, False, MUTED, SANS, space=1.0)
    txt(s, RIGHT - 2.0, 7.02, 2.0, 0.26, page, S_CAP, False, MUTED, SANS,
        PP_ALIGN.RIGHT, space=1.0)


w3, gap3 = 3.62, 0.33
gx = 0.16

# ------------------------------------------------------------------ 1 SAMPUL
s = slide()
photo(s, 0, 0, 13.33, 7.5, "sampul", "cover_bg.jpg")
scrim(s, 0, 0, 9.60, 7.5)
photo(s, 0.41, 0.24, 0.76, 0.76, "logo", "logo_small.png", fit="contain")
txt(s, 1.30, 0.32, 4.4, 0.34, "PT Klumbayan Gold Farm", S_SUB, True, WHITE, SANS)
txt(s, 1.30, 0.68, 4.4, 0.28, "LAMPUNG · INDONESIA · BERDIRI 2022", S_CAP, False,
    RGBColor(0xC7, 0xD8, 0xCD), SANS, space=1.6)
txt(s, M, 2.05, 7.4, 1.95, "Dari lahan bekas tambang\nke rantai pasok Eropa.",
    S_STAT, True, WHITE, SERIF, line=1.10)
txt(s, M, 4.25, 5.6, 1.15,
    "Agribisnis regeneratif di Lampung. Lada hitam, kopi robusta dan kakao, dibeli "
    "langsung dari 1.250 petani, tertelusur sampai titik kebun.",
    S_BODY, False, RGBColor(0xD9, 0xE1, 0xDA), SANS, line=1.36)
rect(s, M, 5.55, 5.6, 0.012, RGBColor(0x4A, 0x6B, 0x5C))
txt(s, M, 5.72, 6.2, 0.26, "DIAJUKAN UNTUK", S_CAP, True, GOLD, SANS, space=1.6)
txt(s, M, 5.99, 6.6, 0.42, "Pertamina UMK Academy 2026", S_SUB, True, WHITE, SERIF)
txt(s, M, 6.75, 8.4, 0.26, "PROFIL PERUSAHAAN · AGUSTUS 2026",
    S_CAP, False, GOLD, SANS, space=1.2)
txt(s, M, 7.02, 7.4, 0.26,
    "klumbayanfarm.com    arif@klumbayanfarm.com    +62 853 7887 0007",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS)

# ------------------------------------------------------------------ 2 PROFIL
s = slide()
header(s, "01", "Profil singkat", "Kami membeli langsung dari petani.")
txt(s, M, 2.58, 6.3, 1.6,
    "PT Klumbayan Gold Farm adalah perusahaan agroforestri dan perdagangan hasil bumi "
    "di Lampung. Kami membeli lada hitam, kopi robusta dan kakao langsung dari petani "
    "yang kami organisir sendiri, tanpa lapisan pengepul di antaranya.",
    S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 4.35, 6.3, 1.1,
    "Hasil panen dikonsolidasi dan dikendalikan mutunya di gudang kami sendiri di Natar, "
    "lalu dikirim ke pembeli dalam dan luar negeri.",
    S_BODY, False, BODY, SANS, line=1.38)
statblock(s, M, 5.55, 1.9, "2022", "Berdiri")
statblock(s, M + 2.1, 5.55, 1.9, "1.250", "Petani")
statblock(s, M + 4.2, 5.55, 2.0, "15", "Karyawan")
photo(s, 7.55, 2.58, 5.06, 3.9, "petani", "ops_farmer_training.jpg",
      "Pelatihan petani, Lampung")
footer(s, "01")

# ------------------------------------------------------------------ 3 ASAL USUL
s = slide()
header(s, "02", "Asal usul", "Kami mulai dari memperbaiki lahan.")
txt(s, M, 2.58, 11.4, 1.0,
    "Perusahaan ini berdiri pada 2022 di Pesawaran dengan satu tujuan: memulihkan lahan "
    "yang rusak akibat bekas penambangan emas, dan mengembalikan warga desa ke pertanian "
    "yang dikelola secara profesional. Nama perusahaan merekam dari mana pekerjaan itu "
    "dimulai.", S_BODY, False, BODY, SANS, line=1.38)
_nw, _ng = 2.62, 0.47
for _i, (_t, _sub) in enumerate([("Rusak", "Bekas tambang, tidak produktif"),
                                 ("Ditanami ulang", "Agroforestri, bukan monokultur"),
                                 ("Produktif", "Lada, kopi dan kakao"),
                                 ("Diperdagangkan", "Masuk rantai pasok ekspor")]):
    _x = M + _i * (_nw + _ng)
    _fill = GREEN if _i == 3 else WHITE
    node(s, _x, 4.18, _nw, 0.92, _t, _sub, _fill, GREEN,
         WHITE if _i == 3 else INK, RGBColor(0xC7, 0xD8, 0xCD) if _i == 3 else BODY)
    if _i < 3:
        arrow(s, _x + _nw + 0.09, 4.53, _ng - 0.18, 0.22)
rect(s, M, 5.55, 11.89, 0.012, RULE)
txt(s, M, 5.75, 11.4, 0.9,
    "Kami tidak menambahkan keberlanjutan ke dalam bisnis dagang. Kami menambahkan bisnis "
    "dagang ke dalam proyek pemulihan lahan.", S_SUB, True, GREEN, SERIF, line=1.22)
footer(s, "02")

# ------------------------------------------------------------------ 4 AGREGASI
s = slide()
header(s, "03", "Agregasi petani", "1.250 petani, satu rantai pasok.", "GO AGGREGATOR")
txt(s, M, 2.55, 11.4, 0.8,
    "Kami tidak menunggu hasil panen datang ke gudang. Kami membangun jaringan pembelian "
    "sampai ke desa, sehingga petani kecil punya pembeli yang pasti dan kami punya pasokan "
    "yang terukur.", S_BODY, False, BODY, SANS, line=1.38)
for i, (v, l) in enumerate([("1.250", "Petani"),
                            ("17", "Stasiun beli"),
                            ("3", "Kabupaten"),
                            ("±600 ha", "Lahan binaan"),
                            ("2.000 ton", "Gudang")]):
    statblock(s, M + i * 2.38, 3.45, 2.25, v, l)
rect(s, M, 4.55, 11.89, 0.012, RULE)
for i, (t, b) in enumerate([
    ("Tercatat, bukan diperkirakan",
     "Tiap petani punya rekaman identitas dan titik kebun."),
    ("Menetap, bukan berkunjung",
     "Lima belas staf tinggal di Lampung."),
    ("Kami membeli, bukan hanya membina",
     "Hubungan dengan petani tak berhenti saat program usai."),
]):
    card(s, M + i * (w3 + gap3), 4.62, w3, 1.60, t, b)
txt(s, M, 6.40, 6.4, 0.26, "Pesawaran · Tanggamus · Lampung Barat",
    S_LABEL, True, GOLD, SANS, space=0.8)
txt(s, M + 6.9, 6.42, 5.0, 0.26,
    "Luas binaan diperkirakan pada rata-rata 0,5 ha per petani.",
    S_CAP, False, MUTED, SANS)
footer(s, "03")

# ------------------------------------------------------------------ 5 PRAKTIK HIJAU
s = slide()
header(s, "04", "Praktik hijau", "Sisa panen kembali ke tanah.", "GO GREEN")
txt(s, M, 2.58, 6.4, 1.4,
    "Tanaman kami tumbuh berlapis bersama pohon naungan, di atas lahan yang sedang "
    "dipulihkan, bukan lahan yang dibuka baru.",
    S_BODY, False, BODY, SANS, line=1.38)
for i, (t, b) in enumerate([
    ("Pengomposan berjalan", "Unit di LKC dan Taman Sari, ditambah dua unit komunal di "
     "Ulu Belu. Petani dilatih membuat kompos sendiri."),
    ("Lahan pulih, bukan lahan baru", "Pertumbuhan diisi dengan memulihkan lahan rusak, "
     "bukan dengan membuka hutan."),
]):
    card(s, M, 3.55 + i * 1.65, 6.4, 1.55, t, b)
statblock(s, 7.55, 2.58, 2.4, "10+ ton", "Kompos tersalur")
statblock(s, 10.2, 2.58, 2.4, "4", "Unit kompos")
photo(s, 7.55, 3.80, 5.06, 2.68, "kebun", "visit_agroforestry_plot.jpg",
      "Kebun agroforestri berlapis")
footer(s, "04")

# ------------------------------------------------------------------ 6 EKSPOR
s = slide()
header(s, "05", "Pasar dan ekspor", "Sudah mengekspor ke Belanda.", "GO GLOBAL")
txt(s, M, 2.58, 11.4, 0.8,
    "Pembeli utama kami adalah Verstegen Spices and Sauces dari Belanda, yang membeli "
    "lada hitam kami dengan standar mutu Eropa dan mengaudit fasilitas kami.",
    S_BODY, False, BODY, SANS, line=1.38)
for i, (v, l) in enumerate([("80-100 ton", "Lada dikontrak, 2026"),
                            ("300 ton", "Kopi robusta per bulan"),
                            ("2.000 ton", "Kapasitas gudang")]):
    statblock(s, M + i * 3.95, 3.55, 3.7, v, l)
rect(s, M, 4.75, 11.89, 0.012, RULE)
for i, (t, b) in enumerate([
    ("Standar yang diaudit pembeli",
     "Gudang dan proses kami diperiksa terhadap syarat pembeli Eropa."),
    ("Kesiapan regulasi Eropa",
     "Penyiapan uji tuntas deforestasi Uni Eropa sedang berjalan."),
    ("Pasar baru sedang dijajaki",
     "Penjajakan pembeli Bangladesh berlanjut setelah kunjungan mereka."),
]):
    card(s, M + i * (w3 + gap3), 4.85, w3, 1.95, t, b)
footer(s, "05")

# ------------------------------------------------------------------ 7 TEKNOLOGI
s = slide()
header(s, "06", "Teknologi", "TAPAK: tiap lot tertelusur ke kebun.", "GO DIGITAL")
txt(s, M, 2.58, 6.4, 0.34, "TRACEABILITY AND ACCOUNTABILITY OF PROFESSIONAL AGRI-KGF",
    S_LABEL, True, GOLD, SANS, space=0.9)
txt(s, M, 3.12, 6.4, 1.5,
    "Platform milik kami sendiri, sudah dipakai dalam operasi harian. Setiap pembelian "
    "merekam identitas petani, koordinat kebun, volume, bukti pembayaran digital dan "
    "pergerakan lot di gudang.", S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 4.75, 6.4, 1.5,
    "Pembeli yang bertanya satu kontainer berasal dari kebun mana akan mendapat jawaban "
    "sampai titik kebun, dan bisa diberi akses untuk memeriksanya sendiri.",
    S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 6.30, 6.4, 0.5,
    "Pencatatan dilakukan saat transaksi terjadi, bukan disusun ulang belakangan.",
    S_BODY, True, GREEN, SANS, line=1.3)
photo(s, 7.55, 2.58, 5.06, 3.9, "tangkapan layar TAPAK")
footer(s, "06")

# ------------------------------------------------------------------ 8 PRODUK
s = slide()
header(s, "07", "Produk", "Enam komoditas dari satu basis pasokan.", None, S_STAT)
C1, C2, C3 = 4.30, 4.55, 3.04
hy = 2.60
rect(s, M, hy, 11.89, 0.40, GREEN)
txt(s, M + 0.22, hy + 0.10, C1 - 0.28, 0.24, "Produk", S_CAP, True, WHITE, SANS,
    caps=True, space=1.2)
txt(s, M + C1, hy + 0.10, C2, 0.24, "Mutu dan bentuk", S_CAP, True, WHITE, SANS,
    caps=True, space=1.2)
txt(s, M + C1 + C2, hy + 0.10, C3, 0.24, "Ketersediaan", S_CAP, True, WHITE, SANS,
    caps=True, space=1.2)
KAT = [("Lada hitam, premium", "Kepadatan min. 580 g/l", "Dikontrak 2026", "80-100 ton, Eropa", GOLD),
       ("Lada hitam, standar", "Kepadatan 500 g/l", "Tersedia", "200 ton per tahun", GREEN),
       ("Kopi robusta", "Natural kering, sortir defect 80/120", "Tersedia", "300 ton per bulan", GREEN),
       ("Kakao", "Biji, bubuk dan nib", "Tersedia", "Diolah sendiri", GREEN),
       ("Cengkih", "Kering utuh", "Sesuai pesanan", "Volume atas permintaan", MUTED),
       ("Cabe jawa, kemukus", "Kering utuh, spesialti", "Sesuai pesanan", "Volume atas permintaan", MUTED)]
ry = hy + 0.46
for i, (prod, spec, stat, note, col) in enumerate(KAT):
    if i % 2 == 0:
        rect(s, M, ry - 0.05, 11.89, 0.56, LIGHT)
    txt(s, M + 0.22, ry + 0.02, C1 - 0.3, 0.28, prod, S_BODY, True, INK, SANS)
    txt(s, M + C1, ry + 0.04, C2 - 0.3, 0.26, spec, S_BODY, False, BODY, SANS)
    txt(s, M + C1 + C2, ry + 0.00, C3, 0.24, stat, S_CAP, True, col, SANS,
        caps=True, space=1.0)
    txt(s, M + C1 + C2, ry + 0.24, C3, 0.24, note, S_CAP, False, MUTED, SANS)
    ry += 0.56
txt(s, M, 6.48, 11.4, 0.3,
    "Pengolahan kakao menjadi bubuk dan nib dilakukan di Lampung, bukan dikirim keluar "
    "sebagai biji mentah.", S_LABEL, False, MUTED, SANS)
footer(s, "07")

# ------------------------------------------------------------------ 9 OPERASI
s = slide()
header(s, "08", "Operasi", "Sudah berjalan, bukan rencana.", None, S_STAT)
ops = [("ops_natar_warehouse.jpg", "Gudang Natar, 2.000 ton"),
       ("ops_cleaning_grading.jpg", "Lini pembersihan dan sortasi"),
       ("ops_quality_control.jpg", "Kendali mutu"),
       ("ops_cacao_roasting.jpg", "Penyangraian kakao"),
       ("ops_cacao_winnowing.jpg", "Pemisahan kulit kakao"),
       ("ops_field_school.jpg", "Sekolah lapang")]
pw, ph, gy = 3.86, 1.86, 0.16
for i, (fn, lb) in enumerate(ops):
    photo(s, M + (i % 3) * (pw + gx), 2.58 + (i // 3) * (ph + gy), pw, ph, lb, fn, lb)
txt(s, M, 6.62, 11.4, 0.4,
    "Gudang Natar: kapasitas 2.000 ton  ·  rumah pengering  ·  mesin ayak  ·  "
    "mesin suton  ·  oven", S_LABEL, False, MUTED, SANS, space=0.6)
footer(s, "08")

# ------------------------------------------------------------------ 10 LEGAL
s = slide()
header(s, "09", "Legalitas dan kepatuhan", "Apa yang sudah, dan apa yang belum.")
baris = [("Penelusuran sampai titik kebun", "BERJALAN", GREEN),
         ("SOP K3 dan limbah, Gudang Natar", "TERPASANG", GREEN),
         ("BPJS dan kepatuhan penggajian", "LUNAS DAN AKTIF", GREEN),
         ("Izin usaha dan penambahan KBLI", "PROSES PEMBARUAN", GOLD),
         ("Sertifikasi halal", "DALAM PROSES", GOLD),
         ("Uji tuntas deforestasi Uni Eropa", "DALAM PENYIAPAN", GOLD),
         ("Sertifikasi organik", "BELUM, LAHAN MASIH TRANSISI", MUTED)]
y = 2.60
for i, (item, status, col) in enumerate(baris):
    if i % 2 == 0: rect(s, M, y - 0.04, 11.89, 0.46, LIGHT)
    txt(s, M + 0.22, y + 0.04, 7.4, 0.32, item, S_BODY, False, INK, SANS)
    txt(s, M + 8.0, y + 0.06, 3.7, 0.3, status, S_LABEL, True, col, SANS, space=0.9)
    y += 0.49
txt(s, M, 6.15, 11.4, 0.3,
    "Kami menyebut tiap butir pada tahap yang benar-benar dicapai.",
    S_BODY, True, GREEN, SANS)
todo(s, M, 6.52, 8.6, "NIB, NPWP, dan omzet tahun berjalan sesuai format formulir", 9)
footer(s, "09")

# ------------------------------------------------------------------ 11 TIM
s = slide()
header(s, "10", "Tim", "Orang-orang yang menjalankannya.")
tim = [("team_1_faizal.png", "Faizal Riza", "Direktur Utama"),
       ("team_2_arif.png", "Arif Rachman", "Direktur Operasional"),
       ("team_3_rafiq.png", "Muhammad Rafiq", "Manajer Teknis"),
       ("team_4_heri.png", "Heri Adi Prasetya", "Manajer Operasional"),
       ("team_5_nico.png", "Nico Setyo Utomo", "Data dan Manajemen"),
       ("team_6_yanfa.png", "Yanfa Ghiyats Ghifari", "Fasilitator Senior")]
cw2 = 3.86
for i, (fn, n, role) in enumerate(tim):
    x = M + (i % 3) * (cw2 + gx); yy = 2.62 + (i // 3) * 2.08
    photo(s, x + (cw2 - 1.30) / 2, yy, 1.30, 1.30, "foto", fn)
    txt(s, x, yy + 1.40, cw2, 0.28, n, S_BODY, True, INK, SANS, PP_ALIGN.CENTER)
    txt(s, x, yy + 1.68, cw2, 0.26, role, S_CAP, False, MUTED, SANS,
        PP_ALIGN.CENTER, caps=True, space=0.8)
txt(s, M, 6.70, 11.4, 0.26,
    "15 karyawan tetap, termasuk lima fasilitator lapangan yang bekerja langsung dengan "
    "kelompok tani di tiga kabupaten.", S_LABEL, False, MUTED, SANS)
footer(s, "10")

# ------------------------------------------------------------------ 12 HARAPAN
s = slide()
header(s, "11", "Harapan dari program", "Yang kami butuhkan, bukan yang kami punya.",
       None, S_STAT)
txt(s, M, 2.58, 11.4, 0.8,
    "Kami datang bukan karena belum berjalan, tetapi karena tahu di titik mana kami "
    "tersendat. Empat hal berikut yang paling menahan pertumbuhan kami saat ini.",
    S_BODY, False, BODY, SANS, line=1.38)
butuh = [("1", "Pencatatan keuangan dan kesiapan permodalan",
          "Angka penjualan kami masih tercatat seadanya. Kami perlu pembukuan yang layak "
          "diperiksa lembaga pembiayaan."),
         ("2", "Perluasan pasar dalam negeri",
          "Ekspor sudah jalan, pasar domestik belum digarap. Kanal daring dan pembeli "
          "dalam negeri masih kosong."),
         ("3", "Sertifikasi yang belum kami pegang",
          "Halal dan keamanan pangan menjadi syarat pembeli baru, dan prosesnya belum "
          "kami kuasai."),
         ("4", "Kemitraan antar pelaku UMK",
          "Kapasitas gudang dan mesin kami masih longgar dan bisa dipakai bersama pelaku "
          "lain di Lampung.")]
yy = 3.62
for num, t, b in butuh:
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(M), Inches(yy), Inches(0.42), Inches(0.42))
    circ.fill.solid(); circ.fill.fore_color.rgb = GREEN; circ.line.fill.background()
    circ.shadow.inherit = False
    pc = circ.text_frame.paragraphs[0]; pc.alignment = PP_ALIGN.CENTER
    rc = pc.add_run(); rc.text = num
    rc.font.size = Pt(S_LABEL); rc.font.bold = True; rc.font.color.rgb = WHITE
    rc.font.name = SANS
    txt(s, M + 0.68, yy + 0.02, 4.0, 0.34, t, S_BODY, True, INK, SANS)
    txt(s, M + 4.9, yy + 0.02, 6.7, 0.72, b, S_BODY, False, BODY, SANS, line=1.30)
    yy += 0.78
footer(s, "11")

# ------------------------------------------------------------------ 13 PENUTUP
s = slide()
rect(s, 0, 0, 13.33, 7.5, GREEN)
photo(s, 6.4, 0, 6.93, 7.5, "penutup", "closing_bg.jpg")
photo(s, 0.41, 0.30, 0.76, 0.76, "logo", "logo_small.png")
txt(s, M, 2.05, 5.2, 1.45, "Silakan datang\nmelihat kebunnya.", S_HEAD, True, WHITE,
    SERIF, line=1.1)
txt(s, M, 3.85, 5.0, 0.42, "PT Klumbayan Gold Farm", S_SUB, True,
    RGBColor(0xC7, 0xD8, 0xCD), SANS)
rect(s, M, 4.42, 5.0, 0.012, RGBColor(0x4A, 0x6B, 0x5C))
txt(s, M, 4.65, 5.2, 1.15,
    "Jln. Wolter Monginsidi No. 159\nBandar Lampung, Lampung\n"
    "Gudang: Natar, Lampung Selatan",
    S_BODY, False, RGBColor(0xD9, 0xE1, 0xDA), SANS, line=1.4)
txt(s, M, 5.95, 5.2, 1.05,
    "Arif Rachman, Direktur Operasional\narif@klumbayanfarm.com\n+62 853 7887 0007",
    S_BODY, False, WHITE, SANS, line=1.4)
txt(s, M, 6.98, 5.2, 0.3, "KLUMBAYANFARM.COM", S_LABEL, True, GOLD, SANS, space=1.6)

prs.save(OUT)
print("tersimpan", OUT, "| slide:", len(prs.slides._sldIdLst))
if PLACEHOLDERS:
    print("")
    print("HARUS DILENGKAPI SEBELUM DIKIRIM:")
    for pg, what in PLACEHOLDERS:
        print("  halaman %-3s %s" % (pg, what))
