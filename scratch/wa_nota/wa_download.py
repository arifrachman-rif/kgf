#!/usr/bin/env python3
"""Download image/media bubbles from a WhatsApp chat within a date range.

Walks history upward (WhatsApp virtualises the list, so rows must be handled
while they are in the DOM) and, for each media bubble stamped inside the range,
opens the viewer and saves the file.
"""
import argparse, json, os, re, time
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"


def key(ds):
    d, m, y = ds.split("/")
    return (int(y), int(m), int(d))


def get_page(p):
    b = p.chromium.connect_over_cdp(CDP)
    for pg in b.contexts[0].pages:
        if "whatsapp" in pg.url.lower():
            return pg
    return b.contexts[0].pages[0]


def dismiss_dialogs(page):
    """WhatsApp pops "What's new" / permission dialogs that swallow clicks."""
    for _ in range(3):
        if page.locator('div[role="dialog"]').count() == 0:
            return
        for label in ("Continue", "OK", "Not now", "Close"):
            try:
                b = page.get_by_role("button", name=label).first
                if b.is_visible():
                    b.click(timeout=4000); page.wait_for_timeout(800); break
            except Exception:
                pass
        else:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
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
        # Overlays can intercept a real click; dispatch one straight at the node.
        page.evaluate("""(n) => {
          const el = Array.from(document.querySelectorAll('[title]'))
            .find(e => (e.getAttribute('title')||'').trim().startsWith(n.trim()));
          if (el) {
            const t = el.closest('[role="listitem"]') || el.closest('[role="row"]') || el;
            t.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            t.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            t.dispatchEvent(new MouseEvent('click', {bubbles: true}));
          }
        }""", name)
    for _ in range(40):
        page.wait_for_timeout(1500)
        if page.evaluate("document.querySelectorAll('#main [role=\"row\"]').length") > 0:
            return


def mark_pane(page):
    return page.evaluate("""() => {
      document.querySelectorAll('[data-wa-pane]').forEach(e => e.removeAttribute('data-wa-pane'));
      const row = document.querySelector('#main [role="row"]');
      if (!row) return false;
      let el = row.parentElement;
      while (el && el !== document.body) {
        const sty = getComputedStyle(el);
        if ((sty.overflowY === 'auto' || sty.overflowY === 'scroll') && el.clientHeight > 150) {
          el.setAttribute('data-wa-pane','1'); return true;
        }
        el = el.parentElement;
      }
      return false;
    }""")


SCAN = """
() => {
  const out = [];
  document.querySelectorAll('#main [role="row"]').forEach((r, i) => {
    const holder = r.querySelector('[data-id]') || r.closest('[data-id]');
    const img = r.querySelector('img[src^="blob:"], img[src^="data:"]');
    const view = r.querySelector('div[title^="View"], [aria-label*="Open picture" i]');
    if (!img && !view) return;
    const st = r.querySelector('[data-pre-plain-text]');
    out.push({idx: i,
              id: holder ? holder.getAttribute('data-id') : null,
              stamp: st ? st.getAttribute('data-pre-plain-text') : null});
  });
  return JSON.stringify(out);
}
"""


def close_viewer(page):
    for _ in range(4):
        try:
            btn = page.locator('div[role="button"][aria-label="Close"], button[aria-label="Close"]').first
            if btn.is_visible():
                btn.click(); page.wait_for_timeout(800); continue
        except Exception:
            pass
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        page.wait_for_timeout(700)
        if page.locator('button[aria-label="Download"]').count() == 0:
            return


ap = argparse.ArgumentParser()
ap.add_argument("chat")
ap.add_argument("--since", required=True, help="dd/mm/yyyy")
ap.add_argument("--until", default=None, help="dd/mm/yyyy (default: tanpa batas atas)")
ap.add_argument("--out", required=True)
ap.add_argument("--rounds", type=int, default=150)
ap.add_argument("--limit", type=int, default=0)
a = ap.parse_args()

os.makedirs(a.out, exist_ok=True)
done, manifest = set(), []

with sync_playwright() as p:
    page = get_page(p)
    open_chat(page, a.chat)
    mark_pane(page)
    # Opening a chat restores the previous scroll position; after a deep walk
    # that is months back, which would trip the date cutoff immediately.
    for _ in range(10):
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = p.scrollHeight; }")
        page.wait_for_timeout(800)
    mark_pane(page)
    newest = json.loads(page.evaluate(SCAN))
    if newest:
        print("stempel media terbaru terlihat:", newest[-1].get("stamp"), flush=True)

    passed_range = False
    for rnd in range(a.rounds):
        items = json.loads(page.evaluate(SCAN))
        for it in items:
            mid, stamp = it["id"], it["stamp"]
            if not mid or mid in done:
                continue
            ds = None
            if stamp and "]" in stamp:
                ds = stamp.split(",")[-1].split("]")[0].strip()
            if not ds:
                continue
            if key(ds) < key(a.since):
                passed_range = True
                done.add(mid)
                continue
            if a.until and key(ds) > key(a.until):
                done.add(mid)
                continue
            done.add(mid)
            try:
                row = page.locator('#main [role="row"]').nth(it["idx"])
                row.scroll_into_view_if_needed(timeout=10000)
                page.wait_for_timeout(500)
                target = row.locator('img[src^="blob:"], div[title^="View"]').first
                target.click(timeout=10000)
                btn = page.locator('button[aria-label="Download"]').first
                btn.wait_for(state="visible", timeout=20000)
                with page.expect_download(timeout=120000) as di:
                    btn.click()
                d = di.value
                name = d.suggested_filename or (mid[-12:] + ".jpg")
                path = os.path.join(a.out, name)
                n = 1
                while os.path.exists(path):
                    base, ext = os.path.splitext(name)
                    path = os.path.join(a.out, f"{base}_{n}{ext}"); n += 1
                d.save_as(path)
                manifest.append({"id": mid, "date": ds, "stamp": stamp, "file": os.path.basename(path)})
                print(f"  [{ds}] {os.path.basename(path)}", flush=True)
            except Exception as e:
                print(f"  [{ds}] GAGAL {mid[-12:]}: {type(e).__name__}", flush=True)
            finally:
                close_viewer(page)
                mark_pane(page)
            if a.limit and len(manifest) >= a.limit:
                break
        if a.limit and len(manifest) >= a.limit:
            break
        if passed_range:
            print("  (sudah melewati batas bawah tanggal)", flush=True)
            break
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = 800; }")
        page.wait_for_timeout(400)
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = 0; }")
        page.wait_for_timeout(2400)

with open(os.path.join(a.out, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print(f"\n[selesai] {len(manifest)} berkas -> {a.out}")
