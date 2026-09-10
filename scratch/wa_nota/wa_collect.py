#!/usr/bin/env python3
"""Walk a WhatsApp chat upward, accumulating media bubbles by stable data-id.

WhatsApp virtualises the message list: the DOM holds ~100 rows and recycles
them while scrolling, so counting rows never grows. The only reliable way to
enumerate a long history is to scroll and accumulate keyed by data-id.
"""
import argparse, json, time
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"

COLLECT_JS = """
() => {
  const out = [];
  document.querySelectorAll('#main [role="row"]').forEach(r => {
    const holder = r.querySelector('[data-id]') || r.closest('[data-id]');
    const id = holder ? holder.getAttribute('data-id') : null;
    const img = r.querySelector('img[src^="blob:"], img[src^="data:"]');
    const view = r.querySelector('div[title^="View"], [aria-label*="Open picture" i]');
    const lines = (r.innerText || '').split(String.fromCharCode(10))
                    .map(x => x.trim()).filter(Boolean);
    // WhatsApp stamps every bubble with "[h:mm am, dd/mm/yyyy] Sender: " —
    // the only place the full date lives; innerText shows just the time.
    const stampEl = r.querySelector('[data-pre-plain-text]');
    out.push({
      id: id,
      media: !!(img || view),
      stamp: stampEl ? stampEl.getAttribute('data-pre-plain-text') : null,
      text: lines.join(' | ').slice(0, 200)
    });
  });
  return JSON.stringify(out);
}
"""


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
    """Find the scroll container by walking up from a real message row.

    Picking "the div with the largest scrollHeight" breaks right after a chat
    opens: only a handful of messages are loaded, so the message pane is barely
    scrollable and some sidebar div wins instead.
    """
    return page.evaluate("""() => {
      document.querySelectorAll('[data-wa-pane]').forEach(e => e.removeAttribute('data-wa-pane'));
      const row = document.querySelector('#main [role="row"]');
      if (!row) return false;
      let el = row.parentElement;
      while (el && el !== document.body) {
        const sty = getComputedStyle(el);
        if ((sty.overflowY === 'auto' || sty.overflowY === 'scroll') && el.clientHeight > 150) {
          el.setAttribute('data-wa-pane', '1');
          return true;
        }
        el = el.parentElement;
      }
      return false;
    }""")


ap = argparse.ArgumentParser()
ap.add_argument("chat")
ap.add_argument("--rounds", type=int, default=80)
ap.add_argument("--out", default=None)
ap.add_argument("--until", default=None, help="berhenti setelah melewati tanggal dd/mm/yyyy")
a = ap.parse_args()

def _key(ds):
    d, m, y = ds.split('/')
    return (int(y), int(m), int(d))


seen = {}
order = []

with sync_playwright() as p:
    page = get_page(p)
    open_chat(page, a.chat)
    mark_pane(page)
    # Re-opening a chat can restore the previous scroll position, which would
    # start the walk in the middle of history. Force it to the newest message.
    for _ in range(6):
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = p.scrollHeight; }")
        page.wait_for_timeout(900)

    def harvest():
        new = 0
        for it in json.loads(page.evaluate(COLLECT_JS)):
            k = it["id"] or ("txt:" + it["text"])
            if k not in seen:
                seen[k] = it
                order.append(k)
                new += 1
        return new

    harvest()
    stale = 0
    for i in range(a.rounds):
        # Pinning scrollTop at 0 never re-fires WhatsApp's lazy loader: it only
        # fires on a downward-then-upward transition. Nudge down, then go up.
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = 800; }")
        page.wait_for_timeout(400)
        page.evaluate("() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = 0; }")
        page.wait_for_timeout(2600)
        n = harvest()
        media = sum(1 for v in seen.values() if v["media"])
        print(f"  scroll {i+1}: +{n} baru, total {len(seen)} pesan, {media} media", flush=True)
        if a.until:
            oldest = None
            for v in seen.values():
                st = v.get("stamp")
                if st and "]" in st:
                    ds = st.split(",")[-1].split("]")[0].strip()
                    if oldest is None or _key(ds) < _key(oldest):
                        oldest = ds
            if oldest and _key(oldest) < _key(a.until):
                print(f"  (sudah melewati {a.until}; tertua terlihat {oldest})", flush=True)
                break
        stale = stale + 1 if n == 0 else 0
        if stale >= 6:
            print("  (riwayat habis)", flush=True)
            break

media = [seen[k] for k in reversed(order) if seen[k]["media"]]
print(f"\n[hasil] {len(seen)} pesan unik, {len(media)} bubble media\n")
for m in media:
    print(f"  {m['id']}\n      {m['text']}")

if a.out:
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump([seen[k] for k in reversed(order)], f, ensure_ascii=False, indent=1)
    print("\ndisimpan:", a.out)
