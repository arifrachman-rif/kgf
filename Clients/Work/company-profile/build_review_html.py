"""Build a single self-contained HTML review page from an exported slide deck.

Images are embedded as data URIs so the file can be opened from anywhere, or sent
to someone, without the pictures breaking. Text-only slides stay PNG so the type
stays crisp; photo-heavy slides are re-encoded to JPEG so the file does not become
unmanageable.

  python Clients/Work/company-profile/build_review_html.py <pngDir> <out.html> "<title>"
"""
import sys, os, io, base64
from PIL import Image

PNG_KEEP_UNDER = 300_000          # bytes; above this, re-encode to JPEG

src, out = sys.argv[1], sys.argv[2]
title = sys.argv[3] if len(sys.argv) > 3 else "Deck review"

# Notes rendered above the slides. Keep this to things a reviewer must not miss.
NOTES = [
    ("Say it three ways or not at all",
     "The EU grant is <b>conditionally</b> awarded, the contract is <b>not signed</b>, and the "
     "&euro;3m is the <b>consortium's</b> grant, not KGF's. All three appear on pages 09 and 13. "
     "If a retelling compresses this to &ldquo;KGF has &euro;3m from the EU&rdquo;, it becomes a "
     "liability rather than a credential."),
    ("The Governor's letter runs the other way",
     "It is the Governor <i>asking KGF</i> to help attract investors into Lampung agriculture, not "
     "the Governor endorsing KGF's fundraising. Pages 09, 10 and 13 were rewritten to match the "
     "original. The reference number is handwritten and still unconfirmed, so no number is printed."),
    ("&asymp;600 ha is derived, not measured",
     "1,250 farmers at an assumed 0.5 ha average. Page 11 prints the assumption underneath it. "
     "The exact figure is computable from the TAPAK plot polygons and is worth producing."),
    ("Still open",
     "Residue and by-product tonnages, gap #9. This does not block sending the deck to the "
     "organisers, but it is what the circular economy forum itself will ask about."),
    ("Check before presenting",
     "There is an open complaint from Sander de Jong contesting findings in GIZ Audit NLD-1022 P2. "
     "It may not touch KGF, but this deck uses &ldquo;audited by GIZ&rdquo; as a credential in "
     "three places."),
]


def encode(path):
    size = os.path.getsize(path)
    if size <= PNG_KEEP_UNDER:
        return "image/png", base64.b64encode(open(path, "rb").read()).decode()
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "JPEG", quality=88, optimize=True)
    return "image/jpeg", base64.b64encode(buf.getvalue()).decode()


names = sorted((f for f in os.listdir(src) if f.lower().endswith(".png")),
               key=lambda n: int("".join(c for c in n if c.isdigit())))

CSS = """
:root{--ink:#141d18;--green:#1f4034;--gold:#9a7526;--body:#3d4a43;--muted:#6c7a72;
--rule:#b9c7be;--paper:#f4f2ed}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--body);
font:16px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif}
header{background:var(--green);color:#fff;padding:34px 40px 30px}
header h1{margin:0 0 6px;font:700 30px/1.2 Georgia,serif}
header p{margin:0;color:#c7d8cd;font-size:14px;letter-spacing:.04em}
main{max-width:1180px;margin:0 auto;padding:28px 24px 70px}
.notes{background:#fff;border:1px solid var(--rule);border-left:4px solid var(--gold);
padding:22px 26px;margin:0 0 34px}
.notes h2{margin:0 0 14px;font:700 13px/1 "Segoe UI",sans-serif;letter-spacing:.14em;
text-transform:uppercase;color:var(--gold)}
.notes dl{margin:0}
.notes dt{font-weight:700;color:var(--ink);margin-top:14px}
.notes dt:first-of-type{margin-top:0}
.notes dd{margin:3px 0 0;font-size:14.5px}
.slide{margin:0 0 30px;background:#fff;border:1px solid var(--rule);
box-shadow:0 1px 3px rgba(20,29,24,.07)}
.slide img{display:block;width:100%;height:auto}
.cap{display:flex;justify-content:space-between;align-items:center;
padding:9px 14px;border-top:1px solid var(--rule);font-size:11.5px;
letter-spacing:.11em;text-transform:uppercase;color:var(--muted)}
.cap b{color:var(--green)}
footer{max-width:1180px;margin:0 auto;padding:0 24px 60px;font-size:13px;color:var(--muted)}
@media print{body{background:#fff}.slide{break-inside:avoid;box-shadow:none}.notes{break-after:page}}
"""

parts = [f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{CSS}</style>
<header><h1>{title}</h1>
<p>PT KLUMBAYAN GOLD FARM &nbsp;&middot;&nbsp; {len(names)} SLIDES &nbsp;&middot;&nbsp; INTERNAL REVIEW COPY</p>
</header><main>"""]

parts.append('<section class="notes"><h2>Read before reviewing</h2><dl>')
for h, b in NOTES:
    parts.append(f"<dt>{h}</dt><dd>{b}</dd>")
parts.append("</dl></section>")

for i, n in enumerate(names, 1):
    mime, b64 = encode(os.path.join(src, n))
    label = "Cover" if i == 1 else ("Closing" if i == len(names) else f"Page {i - 1:02d}")
    parts.append(
        f'<figure class="slide" id="s{i}"><img loading="lazy" alt="{label}" '
        f'src="data:{mime};base64,{b64}">'
        f'<figcaption class="cap"><span><b>{label}</b></span>'
        f'<span>{i} / {len(names)}</span></figcaption></figure>')

parts.append("</main><footer>Generated from the built .pptx. Not for circulation outside KGF "
             "until the notes above are cleared.</footer></html>")

io_out = "".join(parts)
open(out, "w", encoding="utf-8").write(io_out)
print("saved", out, "|", len(names), "slides |", f"{os.path.getsize(out)/1048576:.1f} MB")
