#!/usr/bin/env python3
"""WhatsApp Web toolkit over CDP: find, dump, list-docs, download, send.

Runs INSIDE WSL, against the Chrome instance started by browser-service on
port 9222. The logged-in profile lives at ~/.config/antigravity-chrome-data
inside WSL, not on the Windows side.

Why this exists alongside wa_manager.py: wa_manager only sends, and it picks a
chat with get_by_title(name).first, which can land on a GROUP that merely
mentions the person ("X is also in this group"). Sending a private message to a
group is not recoverable, so `send` here verifies the opened conversation
before typing anything.

Selector notes learned the hard way:
  - The composer and search box sit behind Meta's Lexical shadow root. CSS
    selectors miss them; get_by_role("textbox") pierces it.
  - Mouse-wheel scrolling does not trigger WhatsApp's lazy history load. The
    real scroll container has to be found and driven via scrollTop.
  - A document bubble exposes only a "View" affordance. The Download button
    lives in the full-screen viewer that opens on top of the chat.
  - The first [title] in a chat header is the "Profile details" button, not the
    contact. The chat name is the first line of the header's own innerText.

Usage:
  wa_tools.py find "Yuyun"
  wa_tools.py dump "Hariyadi"
  wa_tools.py list-docs "Hariyadi"
  wa_tools.py download "Hariyadi" --rows 35,37,38 --out ./wadocs
  wa_tools.py send "Yuyun Kurniawan" --file msg.txt          # dry run
  wa_tools.py send "Yuyun Kurniawan" --file msg.txt --send   # actually sends
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
DOC_EXTS = (".pdf", ".doc", ".docx", ".xls", ".xlsx",
            ".ppt", ".pptx", ".csv", ".zip")


# ---------------------------------------------------------------- connection

def connect():
    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp(CDP)
    except Exception as e:
        sys.exit(
            f"Gagal terhubung ke CDP {CDP}: {e}\n"
            "Jalankan browser-service lebih dulu, sebagai proses persisten:\n"
            "  exec xvfb-run -a python3 "
            ".agent/skills/browser-service/scripts/playwright_cdp_server.py\n"
            "Catatan: menjalankannya dengan '&' di dalam `wsl -- bash -lc` akan "
            "mati begitu perintah selesai."
        )
    ctx = browser.contexts[0]
    page = None
    for pg in ctx.pages:
        if "whatsapp" in pg.url.lower():
            page = pg
            break
    if page is None:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://web.whatsapp.com")
        page.wait_for_load_state("networkidle", timeout=60000)
    return p, browser, page


def dismiss_viewer(page):
    """A viewer left open from an earlier run covers the app and eats clicks."""
    for _ in range(4):
        if page.locator('iframe[data-testid="pdf-viewer-iframe"]').count() == 0:
            return
        try:
            close = page.locator('button[aria-label="Close"]').first
            if close.is_visible():
                close.click()
            else:
                page.keyboard.press("Escape")
        except Exception:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
        page.wait_for_timeout(1500)


def search(page, query):
    dismiss_viewer(page)
    tb = page.get_by_role("textbox")
    tb.first.wait_for(state="visible", timeout=60000)
    tb.first.fill(query)
    page.wait_for_timeout(3000)
    return tb


def open_chat(page, name, exact=True):
    search(page, name)
    hit = page.get_by_title(name, exact=exact).first
    try:
        hit.wait_for(state="visible", timeout=20000)
    except Exception:
        hit = page.get_by_text(name).first
        hit.wait_for(state="visible", timeout=20000)
    hit.click()
    page.wait_for_timeout(3500)


def chat_header(page):
    return page.evaluate("""
    () => {
      const h = document.querySelector('#main header');
      if (!h) return null;
      const lines = (h.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
      return {name: lines[0] || '', lines, text: lines.join(' | ').slice(0, 240)};
    }
    """)


def mark_scroll_pane(page):
    page.evaluate("""() => {
      const m = document.querySelector('#main');
      if (!m) return;
      let best = null, h = 0;
      m.querySelectorAll('div').forEach(d => {
        if (d.scrollHeight > d.clientHeight + 50 && d.clientHeight > 200 && d.scrollHeight > h) {
          h = d.scrollHeight; best = d;
        }
      });
      if (best) best.setAttribute('data-claude-pane', '1');
    }""")


def load_history(page, rounds=40, quiet=False):
    """Drive the real scroll container until the row count stops growing."""
    mark_scroll_pane(page)
    prev, stable = -1, 0
    for i in range(rounds):
        page.evaluate("""() => {
          const p = document.querySelector('[data-claude-pane="1"]');
          if (p) p.scrollTop = 0;
        }""")
        page.wait_for_timeout(900)
        rows = page.evaluate(
            '() => document.querySelectorAll(\'#main [role="row"]\').length')
        if rows == prev:
            stable += 1
            if stable >= 4:
                if not quiet:
                    print(f"[wa] riwayat habis di {rows} pesan", flush=True)
                break
        else:
            stable = 0
        prev = rows
    page.wait_for_timeout(1200)


# -------------------------------------------------------------------- commands

def cmd_find(page, args):
    search(page, args.query)
    titles = page.evaluate("""
    () => {
      const seen = new Set();
      document.querySelectorAll('[title]').forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        if (e.closest('#main')) return;
        const t = e.getAttribute('title');
        if (t && t.length < 60) seen.add(t);
      });
      return Array.from(seen);
    }
    """)
    exact = page.get_by_title(args.query, exact=True).count()
    print(f"[{args.query}] cocok persis: {exact}")
    print("judul yang terlihat di panel samping:")
    for t in titles:
        print("  -", t)


def cmd_dump(page, args):
    open_chat(page, args.chat, exact=False)
    load_history(page, args.rounds)
    rows = page.evaluate("""
    () => Array.from(document.querySelectorAll('#main [role="row"]')).map((r, i) => ({
      i,
      img: !!r.querySelector('img[src^="blob:"], img[src^="data:"]'),
      t: (r.innerText || '').replace(/\\n+/g, ' | ').trim().slice(0, 220)
    }))
    """)
    print(f"[wa] {len(rows)} pesan\n")
    for r in rows:
        print(f"[{r['i']:>3}] {'IMG ' if r['img'] else '    '}{r['t']}")


def cmd_list_docs(page, args):
    open_chat(page, args.chat, exact=False)
    load_history(page, args.rounds)
    # Matching on the filename extension alone is not enough: WhatsApp shows
    # some attachments with the extension stripped (e.g. "DOC-20260225-WA0016."),
    # so those get missed. Also accept the metadata line WhatsApp renders under
    # every document bubble ("40 pages - PDF - 2 MB") and the document icon.
    docs = page.evaluate("""
    (exts) => {
      const out = [];
      const meta = /\\d+\\s*pages?\\s*[^A-Za-z0-9]/i;
      document.querySelectorAll('#main [role="row"]').forEach((row, idx) => {
        const text = (row.innerText || '').trim();
        if (!text) return;
        const lower = text.toLowerCase();
        const byExt  = exts.some(e => lower.includes(e));
        const byMeta = meta.test(text);
        const byIcon = !!row.querySelector('span[data-icon*="document" i]');
        if (!byExt && !byMeta && !byIcon) return;
        const lines = text.split('\\n').map(s => s.trim()).filter(Boolean);
        const name = lines.find(l => exts.some(e => l.toLowerCase().includes(e)))
                  || lines.find(l => !meta.test(l) && l.length > 6 && !/^\\d/.test(l))
                  || lines[0];
        out.push({idx, name, how: byExt ? 'ext' : (byIcon ? 'icon' : 'meta'),
                  block: lines.slice(0, 8).join(' | ')});
      });
      return out;
    }
    """, list(DOC_EXTS))
    print(f"\n[wa] {len(docs)} lampiran dokumen:\n")
    seen = set()
    for d in docs:
        if d["name"] in seen:
            continue
        seen.add(d["name"])
        print(f"  [{d['idx']}] {d['name']}   ({d['how']})")
        print(f"        {d['block']}")


def cmd_download(page, args):
    os.makedirs(args.out, exist_ok=True)
    open_chat(page, args.chat, exact=False)
    load_history(page, args.rounds)

    for idx in [int(x) for x in args.rows.split(",")]:
        print(f"\n=== baris {idx} ===", flush=True)
        try:
            row = page.locator('#main [role="row"]').nth(idx)
            row.scroll_into_view_if_needed(timeout=15000)
            page.wait_for_timeout(600)
            trigger = row.locator('div[title^="View"]').first
            print(f"  {trigger.get_attribute('title') or ''}", flush=True)
            trigger.click()
            page.wait_for_timeout(6000)

            btn = page.locator('button[aria-label="Download"]').first
            btn.wait_for(state="visible", timeout=30000)
            with page.expect_download(timeout=180000) as di:
                btn.click()
            d = di.value
            target = os.path.join(args.out, d.suggested_filename or f"row{idx}.pdf")
            d.save_as(target)
            print(f"  tersimpan -> {os.path.basename(target)} "
                  f"({os.path.getsize(target)/1e6:.1f} MB)", flush=True)
        except Exception as e:
            print(f"  GAGAL: {e}", flush=True)
        finally:
            dismiss_viewer(page)
            page.wait_for_timeout(1500)

    print("\nisi folder:", sorted(os.listdir(args.out)))


GROUP_MARKERS = ("is also in this group", "participants", "anggota",
                 "click here for group info", "group info", "you,")


def cmd_send(page, args):
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            message = f.read().strip("\n")
    else:
        message = args.message
    if not message:
        sys.exit("pesan kosong")

    open_chat(page, args.chat, exact=True)

    header = chat_header(page)
    if not header:
        sys.exit("*** DIBATALKAN: header percakapan tidak terbaca")
    print(f"nama chat   : {header['name']!r}")
    print(f"header text : {header['text']!r}")

    if header["name"] != args.chat:
        sys.exit(f"*** DIBATALKAN: nama chat {header['name']!r} != {args.chat!r}")
    low = header["text"].lower()
    for marker in GROUP_MARKERS:
        if marker in low:
            sys.exit(f"*** DIBATALKAN: terdeteksi GRUP (penanda {marker!r})")

    print("\nVERIFIKASI LOLOS: chat personal, nama cocok persis.", flush=True)

    if not args.send:
        print(f"\n[dry-run] tidak mengirim ({len(message)} karakter). "
              "Tambahkan --send untuk benar-benar mengirim.")
        return

    box = page.get_by_role("textbox").last
    box.click()
    page.wait_for_timeout(500)

    # A draft left over from an aborted send would be typed in front of this
    # message, so clear the box before touching it.
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    page.wait_for_timeout(300)

    lines = message.split("\n")
    for i, line in enumerate(lines):
        if line:
            # Per-keystroke typing makes Lexical re-render on every character,
            # which takes minutes on a message this long and blows past every
            # timeout. insert_text fires one insertion event instead.
            page.keyboard.insert_text(line)
            # Lexical swallows insertions that arrive while it is still
            # reconciling the previous one, so let it settle between lines.
            page.wait_for_timeout(250)
        if i < len(lines) - 1:
            # Enter sends, so newlines have to be Shift+Enter.
            page.keyboard.down("Shift")
            page.keyboard.press("Enter")
            page.keyboard.up("Shift")
            page.wait_for_timeout(150)
    page.wait_for_timeout(1500)

    # Never press Enter on a box that does not hold the whole message: a
    # half-typed send cannot be taken back.
    typed = box.inner_text().strip()
    expected = message.strip()
    if len(typed) < len(expected) * 0.98:
        sys.exit(f"*** DIBATALKAN: kotak pesan hanya memuat {len(typed)} dari "
                 f"{len(expected)} karakter, tidak dikirim")
    print(f"kotak pesan : {len(typed)}/{len(expected)} karakter", flush=True)

    box.press("Enter")
    page.wait_for_timeout(5000)
    print("PESAN TERKIRIM.", flush=True)


# ------------------------------------------------------------------------ cli

def main():
    ap = argparse.ArgumentParser(description="WhatsApp Web toolkit (CDP)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find", help="cari kontak / grup berdasarkan nama")
    f.add_argument("query")

    for name, helptext in (("dump", "tampilkan semua pesan yang termuat"),
                           ("list-docs", "daftar lampiran dokumen di chat")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("chat")
        s.add_argument("--rounds", type=int, default=40)

    d = sub.add_parser("download", help="unduh lampiran berdasarkan nomor baris")
    d.add_argument("chat")
    d.add_argument("--rows", required=True, help="mis. 35,37,38 (dari list-docs)")
    d.add_argument("--out", default="./wadocs")
    d.add_argument("--rounds", type=int, default=40)

    s = sub.add_parser("send", help="kirim pesan, dengan verifikasi target")
    s.add_argument("chat", help="nama kontak PERSIS seperti di header chat")
    s.add_argument("--message")
    s.add_argument("--file", help="baca isi pesan dari berkas (mendukung multi-baris)")
    s.add_argument("--send", action="store_true",
                   help="tanpa flag ini hanya verifikasi, tidak mengirim")

    args = ap.parse_args()
    p, browser, page = connect()
    try:
        {"find": cmd_find, "dump": cmd_dump, "list-docs": cmd_list_docs,
         "download": cmd_download, "send": cmd_send}[args.cmd](page, args)
    finally:
        # Leave the shared browser running for the next call.
        p.stop()


if __name__ == "__main__":
    main()
