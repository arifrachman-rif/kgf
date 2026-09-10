#!/usr/bin/env python3
"""Grab chat images by stepping the WhatsApp media viewer backwards.

Why not the Download button: Chrome runs inside WSL while this script runs on
Windows, so Playwright's download artifact lands in the WSL filesystem and
save_as() writes 0 bytes. Reading the blob: URL through the page and shipping
base64 over the protocol avoids the filesystem boundary entirely.

Stop rule: WhatsApp labels media from the last 7 days as Today / Yesterday /
weekday, and anything older with an explicit dd/mm/yyyy. Hitting a label with
a slash therefore means we have walked past "this week".
"""
import argparse, base64, json, os, re, time
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"

GRAB = """
async () => {
  const dl = document.querySelector('[aria-label="Download"]');
  if (!dl) return null;
  let el = dl, host = null;
  for (let i=0;i<12 && el;i++){ el = el.parentElement; if (el && el.innerText && el.innerText.length>10) { host = el; break; } }
  const lines = host ? host.innerText.split(String.fromCharCode(10)).map(s=>s.trim()).filter(Boolean) : [];
  const imgs = Array.from(document.querySelectorAll('img[src^="blob:"]'));
  if (!imgs.length) return JSON.stringify({meta: lines.slice(0,2), b64: null});
  imgs.sort((a,b) => (b.naturalWidth*b.naturalHeight) - (a.naturalWidth*a.naturalHeight));
  const img = imgs[0];
  const res = await fetch(img.src);
  const bytes = new Uint8Array(await res.arrayBuffer());
  let bin = '';
  const CH = 0x8000;
  for (let i=0;i<bytes.length;i+=CH) bin += String.fromCharCode.apply(null, bytes.subarray(i, i+CH));
  return JSON.stringify({meta: lines.slice(0,2), w: img.naturalWidth, h: img.naturalHeight, b64: btoa(bin)});
}
"""


def get_page(p):
    b = p.chromium.connect_over_cdp(CDP)
    for pg in b.contexts[0].pages:
        if "whatsapp" in pg.url.lower():
            return pg
    return b.contexts[0].pages[0]


def dismiss_dialogs(page):
    for _ in range(3):
        if page.locator('div[role="dialog"]').count() == 0:
            return
        for label in ("Continue", "OK", "Not now", "Close"):
            try:
                b = page.get_by_role("button", name=label).first
                if b.is_visible():
                    b.click(timeout=4000); page.wait_for_timeout(700); break
            except Exception:
                pass
        else:
            try: page.keyboard.press("Escape")
            except Exception: pass
            page.wait_for_timeout(600)


def open_chat(page, name):
    dismiss_dialogs(page)
    tb = page.get_by_role("textbox")
    tb.first.wait_for(state="visible", timeout=60000)
    tb.first.fill(name)
    page.wait_for_timeout(3500)
    dismiss_dialogs(page)
    try:
        page.get_by_title(name, exact=False).first.click(timeout=15000)
    except Exception:
        page.evaluate("""(n) => {
          const el = Array.from(document.querySelectorAll('[title]'))
            .find(e => (e.getAttribute('title')||'').trim().startsWith(n.trim()));
          if (el) { const t = el.closest('[role="listitem"]') || el;
            ['mousedown','mouseup','click'].forEach(k => t.dispatchEvent(new MouseEvent(k, {bubbles:true}))); }
        }""", name)
    for _ in range(40):
        page.wait_for_timeout(1500)
        if page.evaluate("document.querySelectorAll('#main [role=\"row\"]').length") > 0:
            return


def open_latest_image(page):
    idx = json.loads(page.evaluate("""() => {
      const out=[];
      document.querySelectorAll('#main [role="row"]').forEach((r,i)=>{
        if (r.querySelector('img[src^="blob:"]')) out.push(i);
      });
      return JSON.stringify(out);
    }"""))
    if not idx:
        return False
    row = page.locator('#main [role="row"]').nth(idx[-1])
    row.scroll_into_view_if_needed(timeout=15000)
    page.wait_for_timeout(800)
    row.locator('img[src^="blob:"]').first.click()
    page.wait_for_timeout(3500)
    return page.locator('[aria-label="Download"]').count() > 0


ap = argparse.ArgumentParser()
ap.add_argument("chat")
ap.add_argument("--out", required=True)
ap.add_argument("--max", type=int, default=200)
ap.add_argument("--tag", default="img")
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
manifest, seen_hashes = [], set()
dupes = 0

with sync_playwright() as p:
    page = get_page(p)
    # A viewer left open from an earlier run covers the app and eats every click.
    for _ in range(5):
        if page.locator('[aria-label="Download"]').count() == 0:
            break
        page.keyboard.press("Escape")
        page.wait_for_timeout(700)
    open_chat(page, a.chat)
    if not open_latest_image(page):
        print("tidak ada gambar di jendela chat yang termuat"); raise SystemExit(1)

    for n in range(a.max):
        raw = page.evaluate(GRAB)
        if not raw:
            print("viewer tertutup, berhenti"); break
        d = json.loads(raw)
        meta = d.get("meta") or []
        sender = meta[0] if meta else "?"
        when = meta[1] if len(meta) > 1 else "?"
        if "/" in when:
            print(f"  label tanggal eksplisit ({when}) -> sudah lewat pekan ini, berhenti"); break
        if d.get("b64"):
            data = base64.b64decode(d["b64"])
            h = hash(data)
            if h in seen_hashes:
                # A click that did not register looks identical to the end of
                # history; only treat a run of repeats as the real end.
                dupes += 1
                if dupes >= 4:
                    print("  (gambar berulang 4x, ujung riwayat) berhenti"); break
                try:
                    page.locator('[aria-label="Previous"]').first.click(timeout=8000)
                    page.wait_for_timeout(2200)
                except Exception:
                    print("  tidak bisa mundur lagi, berhenti"); break
                continue
            dupes = 0
            seen_hashes.add(h)
            fn = f"{a.tag}_{n:03d}.jpg"
            with open(os.path.join(a.out, fn), "wb") as f:
                f.write(data)
            manifest.append({"file": fn, "sender": sender, "when": when,
                             "w": d.get("w"), "h": d.get("h"), "bytes": len(data)})
            print(f"  [{n:03d}] {when:<22} {sender:<28} {d.get('w')}x{d.get('h')}  {len(data)//1024}KB", flush=True)
        try:
            page.locator('[aria-label="Previous"]').first.click(timeout=8000)
        except Exception:
            print("  tidak bisa mundur lagi, berhenti"); break
        page.wait_for_timeout(1800)

with open(os.path.join(a.out, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print(f"\n[selesai] {len(manifest)} gambar -> {a.out}")
