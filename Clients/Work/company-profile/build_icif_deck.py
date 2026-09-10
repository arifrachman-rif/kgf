"""Build the KGF ICIF Edition profile deck (investors, impact funds, European buyers).
Design system inherited from KGF_C3_Pitch_Deck.pptx; type scale consolidated per
power-design/principles/design-principles.md (6 sizes, floor raised to 13pt).
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import sys, os as _os
OUT = "Clients/Work/company-profile/KGF_Company_Profile_ICIF_EDITION.pptx"
if _os.path.exists(OUT):
    try:
        open(OUT, "r+b").close()
    except PermissionError:
        # Was pointing at the BUYER deck, copy-pasted from build_buyer_deck.py.
        # Building this file while the ICIF deck was open in PowerPoint would have
        # silently overwritten the buyer deck instead. Fixed 20 Aug 2026.
        OUT = "Clients/Work/company-profile/KGF_Company_Profile_ICIF_EDITION_v2.pptx"
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


def scrim(s, x, y, w, h, hexcol="1F4034", flip=False):
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
        f'</a:gsLst><a:lin ang="{10800000 if flip else 0}" scaled="0"/></a:gradFill>')
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


PLACEHOLDERS = []             # collected and printed at build time


def todo(s, x, y, w, what, page):
    """A gap that must be filled before this deck is issued. Deliberately loud."""
    PLACEHOLDERS.append((page, what))
    rect(s, x, y, w, 0.34, RGBColor(0xFD, 0xF3, 0xD8), GOLD)
    txt(s, x + 0.14, y + 0.07, w - 0.28, 0.24, "[ TO COMPLETE: " + what + " ]",
        S_CAP, True, GOLD, SANS, space=0.6)


def footer(s, page):
    txt(s, M, 7.02, 6.0, 0.26, "PT KLUMBAYAN GOLD FARM   ·   COMPANY PROFILE",
        S_CAP, False, MUTED, SANS, space=1.0)
    txt(s, RIGHT - 2.0, 7.02, 2.0, 0.26, page, S_CAP, False, MUTED, SANS,
        PP_ALIGN.RIGHT, space=1.0)



# ------------------------------------------------------------------ 1 COVER
s = slide()
photo(s, 0, 0, 13.33, 7.5, "cover", "cover_bg.jpg")
scrim(s, 0, 0, 9.60, 7.5)
photo(s, 0.41, 0.24, 0.76, 0.76, "logo", "logo_small.png", fit="contain")
txt(s, 1.30, 0.32, 4.4, 0.34, "PT Klumbayan Gold Farm", S_SUB, True, WHITE, SANS)
txt(s, 1.30, 0.68, 4.4, 0.28, "LAMPUNG · INDONESIA · EST. 2022", S_CAP, False,
    RGBColor(0xC7, 0xD8, 0xCD), SANS, space=1.6)
txt(s, M, 2.00, 7.4, 1.95, "From mined-out land\nto a European supply chain.",
    S_STAT, True, WHITE, SERIF, line=1.10)
txt(s, M, 4.20, 5.4, 1.15,
    "Regenerative agroforestry on degraded post-mining land in Lampung, traded into "
    "Europe with plot-level traceability.", S_BODY, False,
    RGBColor(0xD9, 0xE1, 0xDA), SANS, line=1.36)
txt(s, M, 5.50, 5.0, 0.26, "MEMBER OF", S_CAP, True, GOLD, SANS, space=1.6)
rect(s, M, 5.78, 4.30, 0.62, WHITE)
photo(s, M + 0.12, 5.86, 1.90, 0.46, "ssi", "logo_ssii.png", fit="contain")
photo(s, M + 2.24, 5.86, 1.90, 0.46, "agf", "logo_agrowforests.png", fit="contain")
txt(s, M + 4.48, 5.84, 4.8, 0.24, "SUSTAINABLE SPICES INITIATIVE INDONESIA",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS, space=0.9)
txt(s, M + 4.48, 6.10, 4.8, 0.24, "aGROWforests CONSORTIUM · GIZ FUNDED",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS, space=0.9)
rect(s, M, 6.58, 5.0, 0.012, RGBColor(0x4A, 0x6B, 0x5C))
# Kept short on purpose: the scrim only holds enough contrast to about x=7in, and
# the full category name ran past that onto the bright part of the photograph.
txt(s, M, 6.73, 8.4, 0.26,
    "ICIF NETHERLANDS BUSINESS MISSION 2026 · CATEGORY 03",
    S_CAP, False, GOLD, SANS, space=1.1)
txt(s, M, 7.00, 7.0, 0.26,
    "klumbayanfarm.com    arif@klumbayanfarm.com    +62 853 7887 0007",
    S_CAP, False, RGBColor(0xB9, 0xC7, 0xBE), SANS)

# ------------------------------------------------------------------ 2 THESIS
s = slide()
header(s, "01", "Thesis", "Circular agriculture starts with the land.")
txt(s, M, 2.58, 6.3, 1.5,
    "Most circular economy work begins after a product exists: recover it, recycle it, "
    "reuse the material. In agriculture the largest circular gain sits earlier. Land "
    "already destroyed can be brought back into production, instead of clearing new "
    "forest to replace it.", S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 4.28, 6.3, 1.0,
    "Restoring damaged land, rather than opening new land, is the circular principle "
    "applied at landscape scale.", S_SUB, True, GREEN, SERIF, line=1.24)
statblock(s, M, 5.45, 2.0, "2022", "Restoration began")
statblock(s, M + 2.2, 5.45, 2.0, "1,250", "Farmer households")
statblock(s, M + 4.4, 5.45, 2.1, "17", "Buying stations")
photo(s, 7.55, 2.58, 5.06, 3.95, "restored land", "ops_farmer_training.jpg",
      "Agroforestry on restored land")
footer(s, "01")

# ------------------------------------------------------------------ 3 ORIGIN
s = slide()
header(s, "02", "Origin", "We began on land a gold mine left behind.")
txt(s, M, 2.58, 11.4, 1.0,
    "PT Klumbayan Gold Farm was founded in Pesawaran, Lampung in 2022 with a single "
    "purpose: restore land degraded by former gold mining, and bring villagers back "
    "into professional farming through regenerative agribusiness. The company name "
    "records where that work began.", S_BODY, False, BODY, SANS, line=1.38)
steps = [("Degraded", "Post-mining land, stripped and unproductive"),
         ("Replanted", "Multi-strata agroforestry, not monoculture"),
         ("Productive", "Pepper, robusta and cocoa grown under shade"),
         ("Traded", "Contracted into European supply chains")]
_w = (11.89 - 3 * 0.42) / 4
for i, (t, b) in enumerate(steps):
    x = M + i * (_w + 0.42)
    rect(s, x, 4.10, _w, 1.05, WHITE, GREEN)
    txt(s, x + 0.14, 4.22, _w - 0.28, 0.30, t, S_LABEL, True, INK, SANS,
        PP_ALIGN.CENTER, caps=True, space=0.9)
    txt(s, x + 0.14, 4.56, _w - 0.28, 0.52, b, S_CAP, False, BODY, SANS,
        PP_ALIGN.CENTER, line=1.25)
    if i < 3:
        arrow(s, x + _w + 0.08, 4.52, 0.26, 0.22)
txt(s, M, 5.60, 11.4, 0.9,
    "We did not add sustainability to a trading business. We added a trading business "
    "to a restoration project.", S_SUB, True, GREEN, SERIF, line=1.22)
footer(s, "02")

# ------------------------------------------------------------------ 4 CIRCULARITY
s = slide()
header(s, "03", "Circularity", "Where the circularity actually is.")
txt(s, M, 2.52, 11.4, 0.4,
    "A spice company is not an obvious circular business, so we will be precise.",
    S_BODY, False, MUTED, SANS)
pillars = [("Circular land use",
            "Degraded and post-mining land restored into production instead of clearing "
            "forest to expand. Audited by GIZ under aGROWforests."),
           ("Residue returned to soil",
            "Composting runs at our LKC and Taman Sari motherplants, plus two communal "
            "units in Ulu Belu. Over 10 tonnes distributed so far."),
           ("Verification, not assertion",
            "Plot polygons and every transaction recorded in TAPAK, so a restoration or "
            "deforestation-free claim can be checked by a third party."),
           ("Value kept at origin",
            "Cocoa processed into powder and nibs in Lampung rather than exported as raw "
            "beans, so processing value stays in the producing region.")]
cw3 = (11.89 - 3 * 0.30) / 4
for i, (t, b) in enumerate(pillars):
    x = M + i * (cw3 + 0.30)
    rect(s, x, 3.05, cw3, 0.045, GOLD)
    txt(s, x, 3.25, cw3, 0.66, t, S_SUB, True, INK, SANS, line=1.14)
    txt(s, x, 4.02, cw3, 2.0, b, S_BODY, False, BODY, SANS, line=1.34)
txt(s, M, 6.38, 11.4, 0.5,
    "ICIF category 03, Circular Food and Agriculture, with a second fit in category 04, "
    "Bio Material and Biomass Innovation.", S_LABEL, True, GOLD, SANS)
footer(s, "03")

# ------------------------------------------------------------------ 5 BY-PRODUCTS
s = slide()
header(s, "04", "From waste to worth", "A buyer asked for the pod, not the bean.")
txt(s, M, 2.58, 6.4, 1.5,
    "An overseas buyer travelled to Lampung, inspected our gardens and processing line, "
    "and enquired about black pepper, robusta green beans, cocoa beans and processed "
    "cocoa, and cocoa pods.", S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 3.72, 6.4, 1.0,
    "A buyer asking for the pod is evidence that what a conventional exporter treats as "
    "a disposal cost already has a market.", S_SUB, True, GREEN, SERIF, line=1.22)
rect(s, M, 4.95, 6.4, 1.78, RGBColor(0xF7, 0xF2, 0xE4), GOLD)
txt(s, M + 0.22, 5.09, 3.7, 0.26, "COMPOSTING ALREADY RUNNING", S_CAP, True, GOLD,
    SANS, space=1.1)
txt(s, M + 0.22, 5.39, 3.6, 1.16,
    "LKC and Taman Sari motherplant, plus two communal units in Ulu Belu. "
    "Farmers are trained to make their own.",
    S_BODY, False, BODY, SANS, line=1.30)
txt(s, M + 4.05, 5.32, 2.10, 0.56, "10+ MT", S_STAT, True, GREEN, SERIF)
txt(s, M + 4.05, 5.91, 2.20, 0.48, "COMPOST DISTRIBUTED TO FARMERS", S_CAP, False,
    MUTED, SANS, caps=True, space=0.9, line=1.25)
photo(s, 7.55, 2.58, 5.06, 2.05, "cacao", "ops_cacao_winnowing.jpg", "Cacao winnowing")
photo(s, 7.55, 4.72, 5.06, 2.05, "processing", "ops_cacao_roasting.jpg",
      "Downstream processing in Lampung")
footer(s, "04")

# ------------------------------------------------------------------ 6 MODEL
s = slide()
header(s, "05", "The model", "One company from the plot to the container.")
_nw, _ng = 2.62, 0.47
chain = [("Farmers", "1,250 registered"), ("Buying stations", "17 verified"),
         ("Gudang Natar", "2,000 tonnes"), ("Export container", "Lot-level record")]
for i, (t, sub) in enumerate(chain):
    x = M + i * (_nw + _ng)
    node(s, x, 2.62, _nw, 0.92, t, sub, GREEN if i == 3 else WHITE, GREEN,
         WHITE if i == 3 else INK, RGBColor(0xC7, 0xD8, 0xCD) if i == 3 else BODY)
    if i < 3:
        arrow(s, x + _nw + 0.09, 2.97, _ng - 0.18, 0.22)
rect(s, M, 3.78, 11.89, 0.42, RGBColor(0xF7, 0xF2, 0xE4))
rect(s, M, 3.78, 11.89, 0.028, GOLD)
txt(s, M + 0.16, 3.88, 11.5, 0.26,
    "TAPAK records farmer identity, plot coordinates, volume and receipts at every step",
    S_LABEL, True, GOLD, SANS, PP_ALIGN.CENTER, space=0.6)
_w2, _g2 = 3.62, 0.33
for i, (t, b) in enumerate([
        ("We organise the farmers", "1,250 households registered, trained and bought "
         "from directly, with no collector layer in between."),
        ("We own the middle", "17 verified buying stations and our own 2,000-tonne "
         "facility, so consolidation and quality control are not outsourced."),
        ("We record as we go", "Captured at the moment of purchase, not reconstructed "
         "afterwards for an audit.")]):
    card(s, M + i * (_w2 + _g2), 4.48, _w2, 2.25, t, b)
footer(s, "05")

# ------------------------------------------------------------------ 7 OPERATIONS
s = slide()
header(s, "06", "Operations", "Built and running, not proposed.", S_STAT)
ops = [("ops_natar_warehouse.jpg", "Natar warehouse, 2,000 t"),
       ("ops_cleaning_grading.jpg", "Cleaning and grading line"),
       ("ops_quality_control.jpg", "Quality control"),
       ("ops_cacao_roasting.jpg", "Cacao roasting"),
       ("ops_field_school.jpg", "Field school"),
       ("ops_training_quality.jpg", "Farmer training")]
pw, ph, gx, gy = 3.86, 1.86, 0.16, 0.16
for i, (fn, lb) in enumerate(ops):
    photo(s, M + (i % 3) * (pw + gx), 2.58 + (i // 3) * (ph + gy), pw, ph, lb, fn, lb)
txt(s, M, 6.62, 11.4, 0.32,
    "Facilities commissioned between 2024 and 2026. Warehouse capacity 2,000 tonnes.",
    S_LABEL, False, MUTED, SANS)
footer(s, "06")

# ------------------------------------------------------------------ 8 TECHNOLOGY
s = slide()
header(s, "07", "Technology", "TAPAK: every lot traced to a mapped plot.")
txt(s, M, 2.58, 6.4, 0.34, "TRACEABILITY AND ACCOUNTABILITY OF PROFESSIONAL AGRI-KGF",
    S_LABEL, True, GOLD, SANS, space=0.9)
txt(s, M, 3.12, 6.4, 1.5,
    "Our own platform, live and in production use. Every purchase records farmer "
    "identity, plot polygon coordinates, volume, digital receipts and warehouse lot "
    "movement.", S_BODY, False, BODY, SANS, line=1.38)
txt(s, M, 4.62, 6.4, 1.7,
    "An investor or buyer asking which farms a container came from receives a plot-level "
    "answer, and can be granted dashboard access to verify it independently rather than "
    "taking our word for it.", S_BODY, False, BODY, SANS, line=1.38)
photo(s, 7.55, 2.58, 5.06, 3.95, "TAPAK PLOT MAP, PERSONAL DATA MASKED")
footer(s, "07")

# ------------------------------------------------------------------ 9 EUROPE
s = slide()
header(s, "08", "Europe", "Europe will require what we already built.")
txt(s, M, 2.58, 11.4, 0.95,
    "From the point EU deforestation rules apply, plot-level traceability stops being a "
    "differentiator and becomes a condition of market access. Suppliers who have not "
    "built it face a cost we have largely already absorbed.",
    S_BODY, False, BODY, SANS, line=1.38)
_w2, _g2 = 3.62, 0.33
euro = [("Already exporting", "Contracted to Verstegen Spices and Sauces, Netherlands, "
         "against European quality standards."),
        ("Due diligence underway", "Plot polygons collected and validated with Verstegen "
         "and Fairfood for EU deforestation compliance."),
        ("Audited by a European buyer", "Our Natar facility is inspected against the "
         "requirements of the buyer, not against our own checklist.")]
for i, (t, b) in enumerate(euro):
    card(s, M + i * (_w2 + _g2), 3.70, _w2, 2.15, t, b)
txt(s, M, 6.05, 11.4, 0.76,
    "Our two closest partners, Verstegen and Fairfood, are both Dutch. Amsterdam is where "
    "this relationship already lives.", S_SUB, True, GREEN, SERIF, line=1.2)
footer(s, "08")

# ------------------------------------------------------------------ 10 TRACTION
s = slide()
header(s, "09", "Traction", "Already shipping to the Netherlands.")
for i, (v, l) in enumerate([("80-100 MT", "Pepper contracted, 2026"),
                            ("300 MT/mo", "Robusta, ceiling 720"),
                            ("2,000 MT", "Warehouse capacity"),
                            ("1,250", "Farmer households")]):
    statblock(s, M + i * 3.0, 2.62, 2.85, v, l)
rect(s, M, 3.90, 11.89, 0.012, RULE)
tr = [("Anchor buyer", "Verstegen Spices and Sauces, Netherlands. Contracted with 80 per "
       "cent payment on goods ready for shipment."),
      # Conditional award confirmed by Sander de Jong, 30 July 2026, and clarifications
      # submitted to the EC on 11 August. Say "conditionally" and say the amount is the
      # consortium's, not ours: the contract is not signed and KGF is one co-applicant.
      ("Programme", "Lead local implementer of aGROWforests, funded and audited by GIZ. "
       "Its successor aGROWForests+ is conditionally awarded up to €3m by the European "
       "Commission."),
      # The letter runs the other way round from how this deck used to describe it.
      # The Governor is asking KGF to help bring investment in, not endorsing KGF's
      # own fundraising. Corrected against the original, 24 Aug 2026.
      ("Government", "The Governor of Lampung has asked us in writing to help attract "
       "investors into agricultural and plantation development. Letter of May 2025.")]
yy = 4.15
for t, b in tr:
    rect(s, M, yy, 0.03, 0.72, GOLD)
    txt(s, M + 0.24, yy, 2.9, 0.32, t, S_BODY, True, INK, SANS)
    txt(s, M + 3.30, yy, 8.3, 0.72, b, S_BODY, False, BODY, SANS, line=1.30)
    yy += 0.86
txt(s, M, 6.70, 11.4, 0.26,
    "Realised revenue figures available to qualified investors on request.",
    S_LABEL, False, MUTED, SANS)
footer(s, "09")

# ------------------------------------------------------------------ 11 ICIF FIT
s = slide()
header(s, "10", "Delegation fit", "Why we fit this delegation.")
crit = [("Export-ready", "Shipping to the Netherlands under contract today."),
        ("Investment-ready", "A written provincial mandate to attract investors, plus "
         "donor-compliance financial systems."),
        ("Scalable", "The plant is underused. Growth needs working capital, not new land "
         "or new machinery."),
        ("Innovation-driven", "TAPAK, our own plot-level traceability platform, live in "
         "production."),
        ("Sustainability-focused", "GIZ-funded land restoration, EUDR preparation, and "
         "on-site composting."),
        ("Open to collaboration", "Existing consortium with Verstegen, Fairfood and PT CAN.")]
cw4 = (11.89 - 0.34) / 2
for i, (t, b) in enumerate(crit):
    x = M + (i % 2) * (cw4 + 0.34)
    y = 2.58 + (i // 2) * 1.34
    rect(s, x, y, 0.03, 1.20, GOLD)
    txt(s, x + 0.24, y, cw4 - 0.30, 0.38, t, S_SUB, True, INK, SANS)
    txt(s, x + 0.24, y + 0.44, cw4 - 0.30, 0.82, b, S_BODY, False, BODY, SANS, line=1.30)
txt(s, M, 6.62, 11.4, 0.26,
    "Measured against the six participant criteria published in the ICIF prospectus.",
    S_LABEL, False, MUTED, SANS)
footer(s, "10")

# --------------------------------------------------------- 12 GROUND CAPACITY
# Added 25 Aug 2026. The audience we are actually addressing is an organisation
# that needs a delivery partner in Lampung, not one that needs another supplier.
# What such an organisation buys is the ground base: registered farmers, mapped
# plots, buying stations, a resident team. Existing partners appear here as
# referees rather than as the destination.
s = slide()
header(s, "11", "Ground capacity", "What a new programme would plug into.")
txt(s, M, 2.55, 11.4, 0.8,
    "Our current partners are references, not the limit of who we can work with. An "
    "organisation bringing a programme to Lampung does not have to build a farmer base "
    "first.", S_BODY, False, BODY, SANS, line=1.38)
# Widest value goes last so it has the whole right margin to run into.
for i, (v, l) in enumerate([("1,250", "Farmer households"),
                            ("≈600 ha", "Under management"),
                            ("17", "Buying stations"),
                            ("5", "Field facilitators"),
                            ("2,000 MT", "Facility at Natar")]):
    statblock(s, M + i * 2.38, 3.45, 2.25, v, l)
rect(s, M, 4.55, 11.89, 0.012, RULE)
_gc = [("Registered, not estimated",
        "Every farmer has an identity record and a mapped plot."),
       ("Resident, not visiting",
        "Fifteen staff, resident across all three regencies."),
       # The trading business is the answer to the question every programme funder
       # asks, which is what happens after the funding stops.
       ("We buy, not just deliver",
        "We are the off-taker too, not only a delivery agent.")]
_gw2, _gg2 = 3.62, 0.33
for i, (t, b) in enumerate(_gc):
    card(s, M + i * (_gw2 + _gg2), 4.68, _gw2, 1.68, t, b)
txt(s, M, 6.40, 6.0, 0.26, "Pesawaran · Tanggamus · Lampung Barat",
    S_LABEL, True, GOLD, SANS, space=0.8)
# Stated as an estimate on purpose. 600 ha is 1,250 farmers at an assumed 0.5 ha
# average, not a measured total. Saying so, and pointing at the polygons that
# would settle it, is stronger than printing a derived number as a fact to an
# audience that will ask how it was arrived at.
txt(s, M, 6.66, 8.2, 0.26,
    "Area estimated at 0.5 ha average holding. TAPAK holds the plot polygons to compute "
    "it exactly.", S_CAP, False, MUTED, SANS)
txt(s, M + 7.7, 6.48, 4.2, 0.26, "aGROWforests implementer, audited by GIZ",
    S_LABEL, True, GREEN, SANS)
footer(s, "11")

# ------------------------------------------------------------------ 13 THE ASK
s = slide()
header(s, "12", "The ask", "What we are looking for in Amsterdam.")
# Reframed 25 Aug 2026. This page used to lead with working capital for KGF. It is
# not what we are after and, on the programme routes, not even possible: develoPPP
# requires an applicant domiciled in the EU, EFTA or an OECD-DAC country, which rules
# KGF out as applicant and casts it as implementer. So the ask is for new programmes
# in Lampung and for the European partner who can carry the application.
asks = [("1", "New programmes for Lampung",
         "Not investment in KGF. New projects across commodities and forestry in the "
         "province, with us delivering them on the ground."),
        ("2", "A European partner to apply with",
         "Programmes like GIZ develoPPP need an applicant domiciled in the EU or "
         "OECD-DAC. We are not eligible, and do not need to be."),
        ("3", "European buyers and distributors",
         "Robusta coffee and processed cocoa are uncommitted. Our premium pepper is "
         "already contracted to a Dutch buyer."),
        ("4", "Circular processing partners",
         "Routes for coffee husk and cocoa pod husk that we could adopt in Lampung.")]
yy = 2.62
for num, t, b in asks:
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(M), Inches(yy), Inches(0.44), Inches(0.44))
    circ.fill.solid(); circ.fill.fore_color.rgb = GREEN; circ.line.fill.background()
    circ.shadow.inherit = False
    pc = circ.text_frame.paragraphs[0]; pc.alignment = PP_ALIGN.CENTER
    rc = pc.add_run(); rc.text = num
    rc.font.size = Pt(S_LABEL); rc.font.bold = True; rc.font.color.rgb = WHITE
    rc.font.name = SANS
    txt(s, M + 0.70, yy + 0.02, 3.5, 0.60, t, S_BODY, True, INK, SANS, line=1.2)
    txt(s, M + 4.35, yy + 0.02, 7.3, 0.76, b, S_BODY, False, BODY, SANS, line=1.30)
    yy += 0.98
rect(s, M, 6.42, 11.89, 0.012, RULE)
txt(s, M, 6.56, 11.4, 0.36,
    "We cannot cover the delegate fee. The next page sets out the alternative.",
    S_SUB, True, GREEN, SERIF)
footer(s, "12")

# ------------------------------------------------- 13 SPONSORED PARTICIPATION
# Added 24 Aug 2026. The organisers know KGF cannot fund the IDR 75,000,000 fee and
# asked for a deck so they could construct a solution, so this page exists to be
# lifted out and shown to whoever would pay for the seat.
s = slide()
header(s, "13", "Sponsored participation", "We cannot fund the seat. We can fill it.")
txt(s, M, 2.58, 11.4, 0.8,
    "We told the organisers plainly that the IDR 75,000,000 delegate fee is beyond us. "
    "Rather than withdraw, we set out here what a sponsored seat would actually be "
    "funding.", S_BODY, False, BODY, SANS, line=1.38)
_sw = (11.89 - 0.34) / 2
_spon = [("A provincial mandate, not a company trip",
          "The Governor of Lampung asked us in writing to help bring investment into "
          "the province."),
         ("A case that shows well on a stage",
          "Post-mining land restored into a traded, deforestation-free supply chain, "
          "with the data to show it."),
         # The strongest de-risker available to a sponsor: they are not being asked to
         # judge the case themselves, the European Commission has just judged it.
         ("An EU grant, conditionally awarded",
          "aGROWForests+ selected for up to €3m by the European Commission. KGF is a "
          "co-applicant."),
         ("Dutch counterparts already in place",
          "Verstegen and Fairfood are both Dutch. The mission deepens partnerships we "
          "already hold.")]
for i, (t, b) in enumerate(_spon):
    x = M + (i % 2) * (_sw + 0.34)
    y = 3.52 + (i // 2) * 1.30
    rect(s, x, y, 0.03, 1.14, GOLD)
    txt(s, x + 0.24, y, _sw - 0.30, 0.38, t, S_SUB, True, INK, SANS)
    txt(s, x + 0.24, y + 0.44, _sw - 0.30, 0.76, b, S_BODY, False, BODY, SANS, line=1.30)
rect(s, M, 6.02, 11.89, 0.012, RULE)
txt(s, M, 6.18, 11.4, 0.76,
    "What we bring instead of a fee is a case the province, the programme funder and the "
    "European buyer will each vouch for.", S_SUB, True, GREEN, SERIF, line=1.2)
footer(s, "13")

# ------------------------------------------------------------------ 14 TEAM
s = slide()
header(s, "14", "Team", "The people who run it.")
team = [("team_1_faizal.png", "Faizal Riza", "Chief Executive Officer"),
        ("team_2_arif.png", "Arif Rachman", "COO / Project Director"),
        ("team_3_rafiq.png", "Muhammad Rafiq", "Technical Manager"),
        ("team_4_heri.png", "Heri Adi Prasetya", "Operations Manager - IT Dev"),
        ("team_5_nico.png", "Nico Setyo Utomo", "Data and Management"),
        ("team_6_yanfa.png", "Yanfa Ghiyats Ghifari", "Senior Facilitator")]
cw2 = 3.86
for i, (fn, n, role) in enumerate(team):
    x = M + (i % 3) * (cw2 + 0.16); yy = 2.62 + (i // 3) * 2.08
    photo(s, x + (cw2 - 1.30) / 2, yy, 1.30, 1.30, "portrait", fn)
    txt(s, x, yy + 1.40, cw2, 0.28, n, S_BODY, True, INK, SANS, PP_ALIGN.CENTER)
    txt(s, x, yy + 1.68, cw2, 0.26, role, S_CAP, False, MUTED, SANS,
        PP_ALIGN.CENTER, caps=True, space=0.8)
txt(s, M, 6.70, 11.4, 0.26,
    "A resident team in Lampung, not a head office at a distance. 15 internal staff, "
    "including five field facilitators.", S_LABEL, False, MUTED, SANS)
footer(s, "14")

# ------------------------------------------------------------------ 14 PARTNERS
s = slide()
header(s, "15", "Partners", "We do not do this alone.")
GROUPS = [("Market", "Buyer and national supply",
           [("logo_verstegen.png", "Verstegen"), (None, "PT CAN")]),
          ("Programme", "Funders and platforms",
           [("logo_giz.png", "GIZ"), ("logo_ssii.png", "SSI-I"), (None, "Solidaridad")]),
          ("Research", "Applied science partners",
           [("logo_brin.png", "BRIN"), ("logo_sith_itb.png", "SITH ITB")]),
          ("Institutional", "Government and national",
           [("logo_kemenperin.png", "Kemenperin"), (None, "Bank Indonesia"), (None, "ASTRA")])]
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
    txt(s, x, 5.42, gw, 1.20, "\n".join(n for _, n in logos), S_BODY, False, BODY,
        SANS, line=1.42)
txt(s, M, 6.72, 11.4, 0.28,
    "KGF is the field implementer and off-taker inside the aGROWforests consortium.",
    S_LABEL, False, MUTED, SANS)
footer(s, "15")

# ------------------------------------------------------------------ 15 CLOSING
s = slide()
rect(s, 0, 0, 13.33, 7.5, GREEN)
# photograph kept near its natural proportion on the left so the farmer stays visible
photo(s, 0, 0, 6.20, 7.5, "closing", "closing_bg.jpg")
scrim(s, 4.70, 0, 1.50, 7.5, flip=True)
RX = 7.05
photo(s, RX, 0.62, 0.76, 0.76, "logo", "logo_small.png", fit="contain")
txt(s, RX, 2.00, 5.60, 1.60, "From waste to worth," + chr(10) + "and back to the soil.",
    S_STAT, True, WHITE, SERIF, line=1.10)
txt(s, RX, 3.78, 5.40, 0.42, "PT Klumbayan Gold Farm", S_SUB, True,
    RGBColor(0xC7, 0xD8, 0xCD), SANS)
rect(s, RX, 4.34, 5.20, 0.012, RGBColor(0x4A, 0x6B, 0x5C))
txt(s, RX, 4.56, 5.60, 1.15,
    "Jln. Wolter Monginsidi No. 159" + chr(10) +
    "Bandar Lampung, Lampung, Indonesia" + chr(10) +
    "Warehouse: Gudang Natar, Lampung Selatan",
    S_BODY, False, RGBColor(0xD9, 0xE1, 0xDA), SANS, line=1.40)
txt(s, RX, 5.88, 5.60, 1.05,
    "Arif Rachman, COO / Project Director" + chr(10) +
    "arif@klumbayanfarm.com" + chr(10) + "+62 853 7887 0007",
    S_BODY, False, WHITE, SANS, line=1.40)
txt(s, RX, 7.00, 5.60, 0.30, "KLUMBAYANFARM.COM", S_LABEL, True, GOLD, SANS, space=1.6)

prs.save(OUT)
print("saved", OUT, "| slides:", len(prs.slides._sldIdLst))
if PLACEHOLDERS:
    print("")
    print("MUST BE FILLED BEFORE THIS DECK IS ISSUED:")
    for pg, what in PLACEHOLDERS:
        print("  page %-3s %s" % (pg, what))
