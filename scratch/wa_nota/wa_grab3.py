#!/usr/bin/env python3
"""Load history back to --since, open the NEWEST image, step backwards.

Complements wa_grab2 (which walks forward from the oldest): forward walking
stops when the loaded window runs out, so the newest slice of the range needs
a backward pass from the most recent media.
"""
import argparse, base64, datetime, json, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
_g = open(os.path.join(HERE, "wa_grab.py"), encoding="utf-8").read()
GRAB = _g.split('GRAB = """')[1].split('"""')[0]
ns = {}
exec(compile(_g.split("ap = argparse.ArgumentParser()")[0], "h", "exec"), ns)
_s = open(os.path.join(HERE, "wa_step.py"), encoding="utf-8").read()
ns2 = {}
exec(compile(_s.split("ap = argparse.ArgumentParser()")[0], "h2", "exec"), ns2)
parse_when = ns2["parse_when"]


def key(ds):
    d, m, y = ds.split("/"); return (int(y), int(m), int(d))


def mark_pane(page):
    return page.evaluate("""() => {
      document.querySelectorAll('[data-wa-pane]').forEach(e => e.removeAttribute('data-wa-pane'));
      const row = document.querySelector('#main [role="row"]');
      if (!row) return false;
      let el = row.parentElement;
      while (el && el !== document.body) {
        const s = getComputedStyle(el);
        if ((s.overflowY==='auto'||s.overflowY==='scroll') && el.clientHeight>150) {
          el.setAttribute('data-wa-pane','1'); return true; }
        el = el.parentElement; }
      return false; }""")


def oldest_stamp(page):
    v = page.evaluate("""() => { const e=document.querySelector('#main [data-pre-plain-text]');
      return e ? e.getAttribute('data-pre-plain-text') : null; }""")
    return v.split(",")[-1].split("]")[0].strip() if v and "]" in v else None


ap = argparse.ArgumentParser()
ap.add_argument("chat")
ap.add_argument("--since", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--tag", default="img")
ap.add_argument("--today", required=True)
ap.add_argument("--load-rounds", type=int, default=60)
ap.add_argument("--max", type=int, default=300)
a = ap.parse_args()

d, m, y = (int(x) for x in a.since.split("/")); since = datetime.date(y, m, d)
d, m, y = (int(x) for x in a.today.split("/")); today = datetime.date(y, m, d)
os.makedirs(a.out, exist_ok=True)
manifest, seen, dupes = [], set(), 0

with sync_playwright() as p:
    page = ns["get_page"](p)
    for _ in range(5):
        if page.locator('[aria-label="Download"]').count() == 0: break
        page.keyboard.press("Escape"); page.wait_for_timeout(700)
    ns["open_chat"](page, a.chat)
    mark_pane(page)

    print("[1/3] memuat riwayat...", flush=True)
    for i in range(a.load_rounds):
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop=800; }")
        page.wait_for_timeout(350)
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop=0; }")
        page.wait_for_timeout(2300)
        os_ = oldest_stamp(page)
        if i % 5 == 0: print(f"   putaran {i+1}: tertua {os_}", flush=True)
        if os_ and key(os_) < key(a.since):
            print(f"   sudah mencapai {os_}", flush=True); break

    print("[2/3] membuka gambar terbaru...", flush=True)
    # jump to the newest message, then pick the last image row
    for _ in range(12):
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop=p.scrollHeight; }")
        page.wait_for_timeout(900)
    idx = json.loads(page.evaluate("""() => { const out=[];
      document.querySelectorAll('#main [role="row"]').forEach((r,i)=>{
        if (r.querySelector('img[src^="blob:"]')) out.push(i); });
      return JSON.stringify(out); }"""))
    if not idx:
        print("tidak ada gambar termuat"); raise SystemExit(1)
    row = page.locator('#main [role="row"]').nth(idx[-1])
    row.scroll_into_view_if_needed(timeout=15000); page.wait_for_timeout(800)
    row.locator('img[src^="blob:"]').first.click()
    page.wait_for_timeout(3500)

    print("[3/3] melangkah mundur...", flush=True)
    for n in range(a.max):
        raw = page.evaluate(GRAB)
        if not raw: print("   viewer tertutup"); break
        info = json.loads(raw)
        meta = info.get("meta") or []
        sender = meta[0] if meta else "?"
        when = meta[1] if len(meta) > 1 else "?"
        dt = parse_when(when, today)
        if dt and dt < since:
            print(f"   {when} sudah sebelum {a.since}, berhenti"); break
        if info.get("b64"):
            data = base64.b64decode(info["b64"]); h = hash(data)
            if h in seen:
                dupes += 1
                if dupes >= 5: print("   ujung media"); break
            else:
                dupes = 0; seen.add(h)
                fn = f"{a.tag}_{len(manifest):03d}.jpg"
                open(os.path.join(a.out, fn), "wb").write(data)
                w, hh = info.get("w"), info.get("h")
                manifest.append({"file": fn, "sender": sender, "when": when,
                                 "date": dt.isoformat() if dt else None,
                                 "w": w, "h": hh, "bytes": len(data)})
                print(f"   [{len(manifest)-1:03d}] {when:<24} {sender:<24} {'landscape' if (w or 0)>(hh or 0) else 'portrait':9} {w}x{hh}", flush=True)
        try:
            page.locator('[aria-label="Previous"]').first.click(timeout=6000)
        except Exception:
            ok = page.evaluate("""() => { const e=document.querySelector('[aria-label="Previous"]');
              if(!e) return false; ['mousedown','mouseup','click'].forEach(k=>e.dispatchEvent(new MouseEvent(k,{bubbles:true}))); return true; }""")
            if not ok: print("   tidak bisa mundur lagi"); break
        page.wait_for_timeout(1600)

mf = os.path.join(a.out, "_manifest.json")
old = json.load(open(mf, encoding="utf-8")) if os.path.exists(mf) else []
json.dump(old + manifest, open(mf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n[selesai] {len(manifest)} gambar -> {a.out}")
