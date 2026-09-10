"""Build the KGF Buyer Edition company profile deck.
Design system inherited from KGF_C3_Pitch_Deck.pptx; type scale consolidated per
power-design/principles/design-principles.md (6 sizes, floor raised to 13pt).
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import sys, os as _os
OUT = "Clients/Work/company-profile/KGF_Company_Profile_BUYER_EDITION.pptx"
if _os.path.exists(OUT):
    try:
        open(OUT, "r+b").close()
    except PermissionError:
        OUT = "Clients/Work/company-profile/KGF_Company_Profile_BUYER_EDITION_v2.pptx"
ASSETS = "Clients/Work/company-profile/assets_from_c3/"
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

SERIF = "Georgia"
SANS  = "Segoe UI"

# consolidated scale
S_HEAD, S_STAT, S_SUB, S_BODY, S_LABEL, S_CAP = 36, 32, 20, 16, 13, 11
M = 0.72                      # left margin, inherited from C3
RIGHT = 13.33 - 0.72

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
    lines = content.split("\n")
    for i, ln in enumerate(lines):
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


def header(s, num, label, headline, hl_size=None):
    """C3 signature: numbered eyebrow, hairline rule, accent tick, headline."""
    if hl_size is None:
        hl_size = S_HEAD if len(headline) <= 44 else S_STAT
    txt(s, M, 0.62, 6.0, 0.3, f"{num}   {label}", S_LABEL, False, GOLD, SANS,
        space=1.4, caps=True)
    rect(s, M, 0.90, RIGHT - M, 0.012, RULE)
    rect(s, M, 0.895, 0.44, 0.022, GOLD)
    txt(s, M, 1.12, 11.89, 1.30, headline, hl_size, True, INK, SERIF, line=1.12)


def photo(s, x, y, w, h, caption, img=None, label=None, fit="cover"):
    """Place an image without distorting it.
    fit="cover"   -> fill the box, crop the overflow (photographs)
    fit="contain" -> fit inside the box, centred, never cropped (logos)
    """
    path = ASSETS + img if img else None
    if path and os.path.exists(path):
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
    """Left-to-right gradient veil so cover text stays legible over a photo."""
    from pptx.oxml.ns import qn
    from lxml import etree
    sh = rect(s, x, y, w, h, GREEN)
    spPr = sh._element.spPr
    for tag in ("a:solidFill", "a:noFill", "a:gradFill"):
        el = spPr.find(qn(tag))
        if el is not None:
            spPr.remove(el)
    xml = (
        '<a:gradFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
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


def footer(s, page):
    txt(s, M, 7.02, 6.0, 0.26, "PT KLUMBAYAN GOLD FARM   ·   COMPANY PROFILE",
        S_CAP, False, MUTED, SANS, space=1.0)
    txt(s, RIGHT - 2.0, 7.02, 2.0, 0.26, page, S_CAP, False, MUTED, SANS,
        PP_ALIGN.RIGHT, space=1.0)


# ------------------------------------------------------------------ 1 COVER
s = slide()
photo(s, 0, 0, 13.33, 7.5, "cover image", "cover_bg.jpg")
scrim(s, 0, 0, 9.60, 7.5)
photo(s, 0.41, 0.24, 0.76, 0.76, "logo", "logo_small.png", fit="contain")
txt(s, 1.30, 0.32, 4.4, 0.34, "PT Klumbayan Gold Farm", S_SUB, True, WHITE, SANS)
txt(s, 1.30, 0.68, 4.4, 0.28, "LAMPUNG · INDONESIA · EST. 2022", S_CAP, False,
    RGBColor(0xC7, 0xD8, 0xCD), SANS, space=1.6)
txt(s, M, 2.10, 5.6, 1.85, "Graded for Europe.\nAvailable to you.", S_HEAD, True,
    WHITE, SERIF, line=1.08)
txt(s, M, 4.25, 5.2, 1.10,
    "A tech-enabled agroforestry off-taker in Lampung supplying black pepper, "
    "robusta coffee and cocoa with plot-level traceability.",
    S_BODY, False, RGBColor(0xD9, 0xE1, 0xDA), SANS, line=1.36)
txt(s, M, 5.52, 4.0, 0.26, "MEMBER OF", S_CAP, True, GOLD, SANS, space=1.6)
rect(s, M, 5.80, 4.30, 0.62, RGBColor(0xFF, 0xFF, 0xFF))
photo(s, M + 0.12, 5.88, 1.90, 0.46, "ssi", "logo_ssii.png", fit="contain")
photo(s, M + 2.24, 5.88, 1.90, 0.46, "agf", "logo_agrowforests.png", fit="contain")
txt(s, M + 4.48, 5.86, 4.6, 0.24, "SUSTAINABLE SPICES INITIATIVE INDONESIA",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS, space=0.9)
txt(s, M + 4.48, 6.12, 4.6, 0.24, "aGROWforests CONSORTIUM",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS, space=0.9)
rect(s, M, 6.60, 5.0, 0.012, RGBColor(0x4A, 0x6B, 0x5C))
txt(s, M, 6.75, 5.4, 0.26, "COMPANY PROFILE · BUYER EDITION · AUGUST 2026",
    S_CAP, False, GOLD, SANS, space=1.2)
txt(s, M, 7.02, 6.0, 0.26, "klumbayanfarm.com    arif@klumbayanfarm.com    +62 853 7887 0007",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS)

# ------------------------------------------------------------------ 2 ORIGIN
s = slide()
header(s, "01", "Origin", "We started by repairing land, not by trading it.")
txt(s, M, 2.58, 6.3, 1.5,
    "PT Klumbayan Gold Farm was founded in 2022 in Pesawaran to restore land degraded "
    "by former gold mining, and to bring villagers back into professional farming "
    "through regenerative agribusiness. The company name records where the work began.",
    S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 4.28, 6.3, 1.1,
    "We did not add sustainability to a trading business. We added a trading business "
    "to a restoration project.", S_SUB, True, GREEN, SERIF, line=1.24)
statblock(s, M, 5.45, 1.9, "2022", "Founded")
statblock(s, M + 2.1, 5.45, 1.9, "1,250", "Farmers")
statblock(s, M + 4.2, 5.45, 2.0, "17", "Buying stations")
photo(s, 7.55, 2.58, 5.06, 3.9, "restored land", "ops_farmer_training.jpg", "Farmer training, Lampung")
footer(s, "01")

# ------------------------------------------------------------------ 3 PROBLEM
s = slide()
header(s, "02", "The problem", "A buyer cannot see past the collector.")
w, gap = 3.62, 0.33
for i, (t, b) in enumerate([
    ("Origin becomes an estimate",
     "Indonesian spice normally passes through several layers of collectors. By the "
     "time it reaches an exporter, the farm it came from is no longer knowable, only "
     "assertable."),
    ("Quality becomes an average",
     "Mixed lots from unknown plots mean specification is managed by blending after "
     "the fact, rather than by control at source."),
    ("Compliance becomes a risk",
     "Once EU deforestation rules apply, an unverifiable origin is not a documentation "
     "gap. It is a market access failure."),
]):
    card(s, M + i * (w + gap), 2.62, w, 2.85, t, b)
txt(s, M, 5.85, 11.0, 0.5,
    "Every one of these is a sourcing problem before it is a paperwork problem.",
    S_SUB, True, GREEN, SERIF)
footer(s, "02")

# ------------------------------------------------------------------ 4 MODEL
s = slide()
header(s, "03", "The model", "One company from the plot to the container.")
# chain diagram, drawn natively so it stays editable
_nw, _ng = 2.62, 0.47
_chain = [("Farmers", "1,250 registered"),
          ("Buying stations", "17 verified"),
          ("Gudang Natar", "2,000 tonnes"),
          ("Export container", "Lot-level record")]
for _i, (_t, _sub) in enumerate(_chain):
    _x = M + _i * (_nw + _ng)
    _fill = GREEN if _i == 3 else WHITE
    node(s, _x, 2.58, _nw, 0.92, _t, _sub, _fill, GREEN,
         WHITE if _i == 3 else INK, RGBColor(0xC7, 0xD8, 0xCD) if _i == 3 else BODY)
    if _i < 3:
        arrow(s, _x + _nw + 0.09, 2.93, _ng - 0.18, 0.22)
rect(s, M, 3.72, 11.89, 0.028, GOLD)
rect(s, M, 3.72, 11.89, 0.42, RGBColor(0xF7, 0xF2, 0xE4))
txt(s, M + 0.16, 3.82, 11.5, 0.26,
    "TAPAK records farmer identity, plot coordinates, volume and receipts at every step",
    S_LABEL, True, GOLD, SANS, PP_ALIGN.CENTER, space=0.6)
for i, (t, b) in enumerate([
    ("We organise the farmers",
     "1,250 registered, trained and bought from directly."),
    ("We own the middle",
     "17 verified buying stations and our own 2,000-tonne facility, so consolidation "
     "and quality control are not outsourced."),
    ("We record as we go",
     "Captured at the moment of purchase, not reconstructed afterwards."),
]):
    card(s, M + i * (w + gap), 4.42, w, 2.30, t, b)
footer(s, "03")

# ------------------------------------------------------------------ 5 OPERATIONS
s = slide()
header(s, "04", "Operations", "Built and running, not proposed.", S_STAT)
ops = [("ops_natar_warehouse.jpg", "Natar warehouse"),
       ("ops_cleaning_grading.jpg", "Cleaning and grading line"),
       ("ops_quality_control.jpg", "Quality control"),
       ("ops_cacao_roasting.jpg", "Cacao roasting"),
       ("ops_cacao_winnowing.jpg", "Cacao winnowing"),
       ("ops_field_school.jpg", "Field school")]
pw, ph, gx, gy = 3.86, 1.86, 0.16, 0.16
for i, (fn, lb) in enumerate(ops):
    photo(s, M + (i % 3) * (pw + gx), 2.58 + (i // 3) * (ph + gy), pw, ph, lb, fn, lb)
txt(s, M, 6.62, 11.4, 0.4,
    "Gudang Natar: 2,000 tonnes  ·  green house  ·  sifting machine  ·  Suton machine  ·  oven",
    S_LABEL, False, MUTED, SANS, space=0.6)
footer(s, "04")

# ------------------------------------------------------------------ 6 CATALOGUE
s = slide()
header(s, "05", "Product catalogue", "Six commodities from one supply base.", S_STAT)
COL1, COL2, COL3 = 4.30, 4.55, 3.04
hy = 2.62
rect(s, M, hy, 11.89, 0.40, GREEN)
txt(s, M + 0.22, hy + 0.10, COL1 - 0.28, 0.24, "Product", S_CAP, True, WHITE, SANS, caps=True, space=1.2)
txt(s, M + COL1, hy + 0.10, COL2, 0.24, "Grade and specification", S_CAP, True, WHITE, SANS,
    caps=True, space=1.2)
txt(s, M + COL1 + COL2, hy + 0.10, COL3, 0.24, "Availability", S_CAP, True, WHITE, SANS,
    caps=True, space=1.2)
CAT = [("Black pepper, standard", "Bulk density 500 g/l", "Available now", "200 MT / year", GREEN),
       ("Black pepper, premium", "Premium FAQ, min. 580 g/l", "Contracted 2026", "80 to 100 MT, Europe", GOLD),
       ("Robusta coffee, green", "Dry natural, defect 80 / 120", "Available now", "300 MT / month", GREEN),
       ("Cocoa", "Beans, powder and nibs", "Available", "Processed in-house", GREEN),
       ("Cloves", "Whole dried", "To order", "Volume on enquiry", MUTED),
       ("Java long pepper, cubeb", "Whole dried, specialty", "To order", "Volume on enquiry", MUTED)]
ry = hy + 0.46
for i, (prod, spec, stat, note, col) in enumerate(CAT):
    if i % 2 == 0:
        rect(s, M, ry - 0.05, 11.89, 0.60, LIGHT)
    txt(s, M + 0.22, ry + 0.02, COL1 - 0.3, 0.28, prod, S_BODY, True, INK, SANS)
    txt(s, M + COL1, ry + 0.04, COL2 - 0.3, 0.26, spec, S_BODY, False, BODY, SANS)
    txt(s, M + COL1 + COL2, ry + 0.00, COL3, 0.24, stat, S_CAP, True, col, SANS,
        caps=True, space=1.0)
    txt(s, M + COL1 + COL2, ry + 0.24, COL3, 0.24, note, S_CAP, False, MUTED, SANS)
    ry += 0.60
txt(s, M, 6.70, 11.4, 0.30,
    "Full parameters for every product are set out in our Product Specification Sheet.",
    S_LABEL, False, MUTED, SANS)
footer(s, "05")

# ------------------------------------------------------------------ 7 GRADE SPLIT
s = slide()
header(s, "06", "The grade split", "One harvest, two grades. One is available.")
# split diagram, drawn natively
node(s, M, 3.05, 2.55, 0.92, "One harvest", "Lampung black pepper")
arrow(s, M + 2.66, 3.40, 0.40, 0.22)
node(s, M + 3.18, 3.05, 2.55, 0.92, "Grade to 580 g/l", "European spec")
# split connectors
rect(s, M + 5.36, 3.50, 0.30, 0.022, GOLD)
rect(s, M + 5.64, 2.92, 0.022, 0.60, GOLD)
rect(s, M + 5.64, 3.50, 0.022, 0.62, GOLD)
arrow(s, M + 5.70, 2.81, 0.32, 0.22)
arrow(s, M + 5.70, 4.01, 0.32, 0.22)
# premium branch
_bw = 5.55
rect(s, M + 6.10, 2.55, _bw, 0.74, LIGHT, RULE)
txt(s, M + 6.30, 2.66, _bw - 0.4, 0.26, "PREMIUM · 580 g/l  ·  CONTRACTED TO EUROPE",
    S_LABEL, True, MUTED, SANS, space=0.9)
txt(s, M + 6.30, 2.95, _bw - 0.4, 0.26, "80 to 100 tonnes for 2026", S_BODY, False, BODY, SANS)
# standard branch
rect(s, M + 6.10, 3.75, _bw, 0.74, GREEN)
txt(s, M + 6.30, 3.86, _bw - 0.4, 0.26, "STANDARD · 500 g/l  ·  AVAILABLE NOW",
    S_LABEL, True, RGBColor(0xC7, 0xD8, 0xCD), SANS, space=0.9)
txt(s, M + 6.30, 4.15, _bw - 0.4, 0.26, "200 tonnes per year", S_BODY, False, WHITE, SANS)
# third inbound stream
rect(s, M + 3.18, 4.62, 2.55, 0.62, RGBColor(0xF7, 0xF2, 0xE4), GOLD)
txt(s, M + 3.32, 4.76, 2.27, 0.36, "Lower-grade raw material bought in directly",
    S_CAP, True, GOLD, SANS, PP_ALIGN.CENTER, line=1.15)
rect(s, M + 5.64, 4.90, 0.46, 0.022, GOLD)
rect(s, M + 6.08, 4.49, 0.022, 0.43, GOLD)
txt(s, M, 5.55, 11.4, 0.8,
    "The two do not compete. A buyer serving the grinding and blending market gets "
    "available volume at a standard price, rather than paying a premium for "
    "specification they do not need.", S_BODY, False, BODY, SANS, line=1.36)
footer(s, "06")

# ------------------------------------------------------------------ 8 CAPACITY
s = slide()
header(s, "07", "Capacity", "The plant is running below its limit, on purpose.")
txt(s, M, 2.62, 11.4, 1.0,
    "We concentrated on a single European contract, so machine hours and farmer supply "
    "both have headroom. New buyer volume does not displace anything. It fills capacity "
    "that already exists.", S_BODY, False, BODY, SANS, line=1.38)
for i, (v, l) in enumerate([("200 MT/yr", "Standard pepper, available"),
                            ("300 MT/mo", "Robusta, ceiling 720"),
                            ("2,000 MT", "Warehouse at Natar")]):
    statblock(s, M + i * 3.95, 3.90, 3.7, v, l)
rect(s, M, 5.35, 11.89, 0.012, RULE)
txt(s, M, 5.60, 11.4, 0.8,
    "The limit is how far ahead an order is placed, not whether we have the plant or "
    "the farmers to fulfil it.", S_SUB, True, GREEN, SERIF, line=1.22)
footer(s, "07")

# ------------------------------------------------------------------ 9 TECHNOLOGY
s = slide()
header(s, "08", "Technology", "TAPAK: every lot traced to a mapped plot.")
txt(s, M, 2.58, 6.4, 0.36, "TRACEABILITY AND ACCOUNTABILITY OF PROFESSIONAL AGRI-KGF",
    S_LABEL, True, GOLD, SANS, space=0.9)
txt(s, M, 3.02, 6.4, 1.5,
    "Live and in production use. Every purchase records farmer identity, plot polygon "
    "coordinates, volume, digital receipts and warehouse lot movement.",
    S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 4.55, 6.4, 1.7,
    "A buyer asking which farms a container came from receives a plot-level answer, and "
    "can be granted dashboard access to verify it independently rather than taking our "
    "word for it.", S_BODY, False, BODY, SANS, line=1.38)
photo(s, 7.55, 2.58, 5.06, 3.9, "TAPAK plot map, personal data masked")
footer(s, "08")

# ------------------------------------------------------------------ 10 COMPLIANCE
s = slide()
header(s, "09", "Quality and compliance", "What we hold, and what we do not.")
rows = [("Plot-level traceability", "LIVE", GREEN),
        ("Health, safety and waste SOP, Natar", "IN PLACE", GREEN),
        ("Social security and payroll", "PAID AND ACTIVE", GREEN),
        ("EU deforestation due diligence", "IN PREPARATION", GOLD),
        ("Business licence and KBLI", "UPDATE IN PROGRESS", GOLD),
        ("Phytosanitary certificate", "TO CONFIRM", GOLD),
        ("Halal certification", "IN PROGRESS", GOLD),
        ("Organic certification", "IN PROGRESS", GOLD)]
y = 2.55
for i, (item, status, col) in enumerate(rows):
    if i % 2 == 0: rect(s, M, y - 0.04, 11.89, 0.46, LIGHT)
    txt(s, M + 0.22, y + 0.04, 7.4, 0.32, item, S_BODY, False, INK, SANS)
    txt(s, M + 8.0, y + 0.06, 3.5, 0.3, status, S_LABEL, True, col, SANS, space=0.9)
    y += 0.49
txt(s, M, 6.42, 11.4, 0.56,
    "We state each item at the stage it has actually reached, rather than claim what is "
    "not yet issued.", S_BODY, True, GREEN, SANS)
footer(s, "09")

# ------------------------------------------------------------------ 11 PROOF
s = slide()
header(s, "10", "Proof", "Buyers have already inspected the operation.")
txt(s, M, 2.58, 6.4, 1.4,
    "A foreign buyer travelled to Lampung and inspected our gardens, processing line and "
    "warehouse in person. Their interest covered black pepper, robusta green beans, cocoa "
    "beans and processed cocoa, and cocoa pods.", S_BODY, False, BODY, SANS, line=1.38)
for i, (t, b) in enumerate([
    ("Verstegen", "Contracts against European quality standards and audits our facility."),
    ("GIZ", "Funds and audits the aGROWforests consortium we lead locally."),
    ("Netherlands", "Our current export market."),
]):
    yy = 4.15 + i * 0.86
    rect(s, M, yy, 0.03, 0.66, GOLD)
    txt(s, M + 0.22, yy, 2.0, 0.3, t, S_BODY, True, INK, SANS)
    txt(s, M + 2.3, yy, 4.1, 0.66, b, S_BODY, False, BODY, SANS, line=1.3)
photo(s, 7.55, 2.58, 5.06, 4.3, "buyer visit", "impact_photo.jpg", "Buyer visit to the gardens")
footer(s, "10")

# ------------------------------------------------------------------ 12 TEAM
s = slide()
header(s, "11", "Team", "The people who run it.")
team = [("team_1_faizal.png", "Faizal Riza", "Chief Executive Officer"),
        ("team_2_arif.png", "Arif Rachman", "COO / Project Director"),
        ("team_3_rafiq.png", "Muhammad Rafiq", "Technical Manager"),
        ("team_4_heri.png", "Heri Adi Prasetya", "Operations Manager - IT Dev"),
        ("team_5_nico.png", "Nico Setyo Utomo", "Data and Management"),
        ("team_6_yanfa.png", "Yanfa Ghiyats Ghifari", "Senior Facilitator")]
cw2 = 3.86
for i, (fn, n, role) in enumerate(team):
    x = M + (i % 3) * (cw2 + gx); yy = 2.62 + (i // 3) * 2.08
    photo(s, x + (cw2 - 1.30) / 2, yy, 1.30, 1.30, "portrait", fn)
    txt(s, x, yy + 1.40, cw2, 0.28, n, S_BODY, True, INK, SANS, PP_ALIGN.CENTER)
    txt(s, x, yy + 1.68, cw2, 0.26, role, S_CAP, False, MUTED, SANS,
        PP_ALIGN.CENTER, caps=True, space=0.8)
txt(s, M, 6.70, 11.4, 0.26,
    "15 internal staff, including five field facilitators working directly with farmer "
    "groups across Lampung.", S_LABEL, False, MUTED, SANS)
footer(s, "11")

# ------------------------------------------------------------------ 13 PARTNERS
s = slide()
header(s, "12", "Partners", "We do not do this alone.")
GROUPS = [
    ("Market", "Buyer and national supply",
     [("logo_verstegen.png", "Verstegen"), (None, "PT CAN")]),
    ("Programme", "Funders and platforms",
     [("logo_giz.png", "GIZ"), ("logo_ssii.png", "SSI-I"), (None, "Solidaridad")]),
    ("Research", "Applied science partners",
     [("logo_brin.png", "BRIN"), ("logo_sith_itb.png", "SITH ITB")]),
    ("Institutional", "Government and national",
     [("logo_kemenperin.png", "Kemenperin"), (None, "Bank Indonesia"), (None, "ASTRA")]),
]
gw = (11.89 - 3 * 0.28) / 4
for i, (title, sub, logos) in enumerate(GROUPS):
    x = M + i * (gw + 0.28)
    rect(s, x, 2.62, gw, 0.045, GOLD)
    txt(s, x, 2.78, gw, 0.38, title, S_SUB, True, INK, SANS, caps=True, space=1.0)
    txt(s, x, 3.18, gw, 0.40, sub, S_CAP, False, MUTED, SANS)
    rect(s, x, 3.52, gw, 1.72, LIGHT)
    ly = 3.64
    for fn, nm in logos:
        if fn:
            photo(s, x + 0.22, ly, gw - 0.44, 0.44, nm, fn, fit="contain")
        else:
            txt(s, x + 0.22, ly + 0.10, gw - 0.44, 0.26, nm, S_BODY, True, MUTED, SANS,
                PP_ALIGN.CENTER)
        ly += 0.52
    names = "\n".join(n for _, n in logos)
    txt(s, x, 5.42, gw, 1.20, names, S_BODY, False, BODY, SANS, line=1.42)
txt(s, M, 6.72, 11.4, 0.28,
    "KGF is the field implementer and off-taker inside the aGROWforests consortium.",
    S_LABEL, False, MUTED, SANS)
footer(s, "12")

# ------------------------------------------------------------------ 14 HOW TO BUY
s = slide()
header(s, "13", "How to buy", "What we propose, in the order we propose it.")
steps = [("1", "Send an enquiry", "Product, grade, quantity and delivery period."),
         ("2", "We quote", "Full specification, with availability confirmed."),
         ("3", "Samples", "Despatched for approval before any commitment."),
         ("4", "A trial container", "So quality is judged on the product, not on paper."),
         ("5", "A standing relationship", "Seasonal supply, documentation aligned to your market, halal included.")]
y = 2.62
for num, t, b in steps:
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(M), Inches(y), Inches(0.42), Inches(0.42))
    circ.fill.solid(); circ.fill.fore_color.rgb = GREEN; circ.line.fill.background()
    circ.shadow.inherit = False
    tfc = circ.text_frame; tfc.word_wrap = False
    pc = tfc.paragraphs[0]; pc.alignment = PP_ALIGN.CENTER
    rc = pc.add_run(); rc.text = num
    rc.font.size = Pt(S_LABEL); rc.font.bold = True; rc.font.color.rgb = WHITE; rc.font.name = SANS
    txt(s, M + 0.68, y + 0.02, 3.3, 0.34, t, S_BODY, True, INK, SANS)
    txt(s, M + 4.1, y + 0.02, 7.5, 0.62, b, S_BODY, False, BODY, SANS, line=1.3)
    y += 0.76
rect(s, M, 6.45, 11.89, 0.012, RULE)
txt(s, M, 6.60, 11.4, 0.34, "We host buyer inspections of our farms and facility at any time.",
    S_SUB, True, GREEN, SERIF)
footer(s, "13")

# ------------------------------------------------------------------ 15 CLOSING
s = slide()
rect(s, 0, 0, 13.33, 7.5, GREEN)
photo(s, 6.4, 0, 6.93, 7.5, "closing image", "closing_bg.jpg")
photo(s, 0.41, 0.30, 0.76, 0.76, "logo", "logo_small.png")
txt(s, M, 2.05, 5.2, 1.45, "Come and see the plots.", S_HEAD, True, WHITE, SERIF, line=1.1)
txt(s, M, 3.62, 5.0, 0.42,
    "PT Klumbayan Gold Farm", S_SUB, True, RGBColor(0xC7, 0xD8, 0xCD), SANS)
rect(s, M, 4.20, 5.0, 0.012, RGBColor(0x4A, 0x6B, 0x5C))
txt(s, M, 4.45, 5.2, 1.15,
    "Jln. Wolter Monginsidi No. 159\nBandar Lampung, Lampung, Indonesia\n"
    "Warehouse: Gudang Natar, Lampung Selatan",
    S_BODY, False, RGBColor(0xD9, 0xE1, 0xDA), SANS, line=1.4)
txt(s, M, 5.78, 5.2, 1.05,
    "Arif Rachman, Operational Director\narif@klumbayanfarm.com\n+62 853 7887 0007",
    S_BODY, False, WHITE, SANS, line=1.4)
txt(s, M, 6.98, 5.2, 0.3, "KLUMBAYANFARM.COM", S_LABEL, True, GOLD, SANS, space=1.6)

prs.save(OUT)
print("saved", OUT, "| slides:", len(prs.slides.__iter__.__self__._sldIdLst))
