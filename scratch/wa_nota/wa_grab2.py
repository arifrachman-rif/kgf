#!/usr/bin/env python3
"""Load chat history back to a date, then walk the media viewer FORWARD.

The viewer can only traverse media that is already in the loaded window, so
stepping backwards from the newest image stalls after a handful. Loading the
window first and then stepping forward from the oldest image covers the range
in one pass.
"""
import argparse, base64, json, os
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
GRAB = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_grab.py"),
            encoding="utf-8").read().split('GRAB = """')[1].split('"""')[0]

helpers = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_grab.py"),
               encoding="utf-8").read()
ns = {}
exec(compile(helpers.split("ap = argparse.ArgumentParser()")[0], "h", "exec"), ns)
get_page, open_chat, dismiss_dialogs = ns["get_page"], ns["open_chat"], ns["dismiss_dialogs"]


def key(ds):
    d, m, y = ds.split("/")
    return (int(y), int(m), int(d))


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
        el = el.parentElement;
      }
      return false;
    }""")


def oldest_stamp(page):
    v = page.evaluate("""() => {
      const e = document.querySelector('#main [data-pre-plain-text]');
      return e ? e.getAttribute('data-pre-plain-text') : null;
    }""")
    if v and "]" in v:
        return v.split(",")[-1].split("]")[0].strip()
    return None


ap = argparse.ArgumentParser()
ap.add_argument("chat")
ap.add_argument("--since", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--tag", default="img")
ap.add_argument("--load-rounds", type=int, default=80)
ap.add_argument("--max", type=int, default=300)
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
manifest, seen = [], set()

with sync_playwright() as p:
    page = get_page(p)
    for _ in range(5):
        if page.locator('[aria-label="Download"]').count() == 0:
            break
        page.keyboard.press("Escape"); page.wait_for_timeout(700)
    open_chat(page, a.chat)
    mark_pane(page)

    print("[1/3] memuat riwayat...", flush=True)
    for i in range(a.load_rounds):
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop=800; }")
        page.wait_for_timeout(350)
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop=0; }")
        page.wait_for_timeout(2300)
        os_ = oldest_stamp(page)
        if i % 5 == 0:
            print(f"   putaran {i+1}: tertua {os_}", flush=True)
        if os_ and key(os_) < key(a.since):
            print(f"   sudah mencapai {os_}", flush=True); break

    print("[2/3] membuka gambar tertua...", flush=True)
    idx = json.loads(page.evaluate("""() => {
      const out=[];
      document.querySelectorAll('#main [role="row"]').forEach((r,i)=>{
        if (r.querySelector('img[src^="blob:"]')) out.push(i);
      });
      return JSON.stringify(out);
    }"""))
    if not idx:
        print("tidak ada gambar termuat"); raise SystemExit(1)
    row = page.locator('#main [role="row"]').nth(idx[0])
    row.scroll_into_view_if_needed(timeout=15000)
    page.wait_for_timeout(800)
    row.locator('img[src^="blob:"]').first.click()
    page.wait_for_timeout(3500)

    print("[3/3] melangkah maju...", flush=True)
    dupes = 0
    for n in range(a.max):
        raw = page.evaluate(GRAB)
        if not raw:
            print("   viewer tertutup"); break
        d = json.loads(raw)
        meta = d.get("meta") or []
        sender = meta[0] if meta else "?"
        when = meta[1] if len(meta) > 1 else "?"
        if d.get("b64"):
            data = base64.b64decode(d["b64"])
            h = hash(data)
            if h in seen:
                dupes += 1
                if dupes >= 5:
                    print("   ujung media"); break
            else:
                dupes = 0
                seen.add(h)
                skip = "/" in when          # older than a week -> before this week
                if not skip:
                    fn = f"{a.tag}_{len(manifest):03d}.jpg"
                    with open(os.path.join(a.out, fn), "wb") as f:
                        f.write(data)
                    manifest.append({"file": fn, "sender": sender, "when": when,
                                     "w": d.get("w"), "h": d.get("h"), "bytes": len(data)})
                    print(f"   [{len(manifest)-1:03d}] {when:<22} {sender:<26} {d.get('w')}x{d.get('h')}", flush=True)
        try:
            page.locator('[aria-label="Next"]').first.click(timeout=8000)
        except Exception:
            print("   tidak bisa maju lagi"); break
        page.wait_for_timeout(1700)

with open(os.path.join(a.out, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print(f"\n[selesai] {len(manifest)} gambar pekan ini -> {a.out}")
