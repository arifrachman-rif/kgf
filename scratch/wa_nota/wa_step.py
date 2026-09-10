#!/usr/bin/env python3
"""Step the already-open WhatsApp media viewer forward, saving images in range.

Date labels come in four shapes: "Today at ...", "Yesterday at ...",
"<Weekday> at ..." (within the last week) and "dd/mm/yyyy at ...". Treating a
slash as "older than this week" is wrong: WhatsApp switches to explicit dates
after about two days, so 24-28 Aug all carry slashes.
"""
import argparse, base64, datetime, json, os, re
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "wa_grab.py"), encoding="utf-8").read()
GRAB = _src.split('GRAB = """')[1].split('"""')[0]
ns = {}
exec(compile(_src.split("ap = argparse.ArgumentParser()")[0], "h", "exec"), ns)

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_when(label, today):
    low = (label or "").lower()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", low)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        return datetime.date(y, mo, d)
    if low.startswith("today"):
        return today
    if low.startswith("yesterday"):
        return today - datetime.timedelta(days=1)
    for i, w in enumerate(WEEKDAYS):
        if low.startswith(w):
            delta = (today.weekday() - i) % 7
            return today - datetime.timedelta(days=delta or 7)
    return None


def click_next(page):
    try:
        page.locator('[aria-label="Next"]').first.click(timeout=6000)
        return True
    except Exception:
        pass
    return page.evaluate("""() => {
      const e = document.querySelector('[aria-label="Next"]');
      if (!e) return false;
      ['mousedown','mouseup','click'].forEach(k => e.dispatchEvent(new MouseEvent(k, {bubbles:true})));
      return true;
    }""")


ap = argparse.ArgumentParser()
ap.add_argument("--since", required=True, help="dd/mm/yyyy")
ap.add_argument("--out", required=True)
ap.add_argument("--tag", default="img")
ap.add_argument("--max", type=int, default=300)
ap.add_argument("--today", default=None, help="dd/mm/yyyy override")
a = ap.parse_args()

d, m, y = (int(x) for x in a.since.split("/"))
since = datetime.date(y, m, d)
if a.today:
    d, m, y = (int(x) for x in a.today.split("/"))
    today = datetime.date(y, m, d)
else:
    today = datetime.date.today()

os.makedirs(a.out, exist_ok=True)
manifest, seen, dupes, skipped = [], set(), 0, 0

with sync_playwright() as p:
    page = ns["get_page"](p)
    if page.locator('[aria-label="Download"]').count() == 0:
        print("viewer tidak terbuka — jalankan wa_grab2.py dulu"); raise SystemExit(1)

    for n in range(a.max):
        raw = page.evaluate(GRAB)
        if not raw:
            print("viewer tertutup"); break
        info = json.loads(raw)
        meta = info.get("meta") or []
        sender = meta[0] if meta else "?"
        when = meta[1] if len(meta) > 1 else "?"
        dt = parse_when(when, today)
        if info.get("b64"):
            data = base64.b64decode(info["b64"])
            h = hash(data)
            if h in seen:
                dupes += 1
                if dupes >= 5:
                    print("ujung media"); break
            else:
                dupes = 0
                seen.add(h)
                if dt and dt >= since:
                    fn = f"{a.tag}_{len(manifest):03d}.jpg"
                    with open(os.path.join(a.out, fn), "wb") as f:
                        f.write(data)
                    manifest.append({"file": fn, "sender": sender, "when": when,
                                     "date": dt.isoformat(), "w": info.get("w"),
                                     "h": info.get("h"), "bytes": len(data)})
                    orient = "landscape" if (info.get("w") or 0) > (info.get("h") or 0) else "portrait"
                    print(f"  [{len(manifest)-1:03d}] {when:<24} {sender:<24} {orient:9} {info.get('w')}x{info.get('h')}", flush=True)
                else:
                    skipped += 1
        if not click_next(page):
            print("tidak bisa maju lagi"); break
        page.wait_for_timeout(1600)

mf = os.path.join(a.out, "_manifest.json")
old = []
if os.path.exists(mf):
    try: old = json.load(open(mf, encoding="utf-8"))
    except Exception: old = []
with open(mf, "w", encoding="utf-8") as f:
    json.dump(old + manifest, f, ensure_ascii=False, indent=1)
print(f"\n[selesai] {len(manifest)} disimpan, {skipped} di luar rentang -> {a.out}")
