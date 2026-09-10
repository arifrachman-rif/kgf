#!/usr/bin/env python3
"""Scan a WhatsApp chat for image/document attachments, with patient loading.

Unlike wa_tools.list-docs this also reports IMAGE bubbles, because purchase
notes ("nota") arrive as photos, not documents.
"""
import argparse, json, sys, time
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"


def get_page(p):
    b = p.chromium.connect_over_cdp(CDP)
    ctx = b.contexts[0]
    for pg in ctx.pages:
        if "whatsapp" in pg.url.lower():
            return pg
    return ctx.pages[0]


def open_chat(page, name):
    tb = page.get_by_role("textbox")
    tb.first.wait_for(state="visible", timeout=60000)
    tb.first.fill(name)
    page.wait_for_timeout(3500)
    page.get_by_title(name, exact=False).first.click()
    # wait until the message pane actually has rows
    for _ in range(40):
        page.wait_for_timeout(1500)
        if page.evaluate("document.querySelectorAll('#main [role=\"row\"]').length") > 0:
            break


def pane(page):
    return page.evaluate("""() => {
      const m = document.querySelector('#main'); if (!m) return false;
      let best=null,h=0;
      m.querySelectorAll('div').forEach(d=>{
        if(d.scrollHeight>d.clientHeight+50 && d.clientHeight>200 && d.scrollHeight>h){h=d.scrollHeight;best=d;}
      });
      if(!best) return false; best.setAttribute('data-wa-pane','1'); return true;
    }""")


def rows(page):
    return page.evaluate("document.querySelectorAll('#main [role=\"row\"]').length")


def scroll_up(page, rounds, quiet_limit=4):
    pane(page)
    last, quiet = rows(page), 0
    for i in range(rounds):
        page.evaluate("""() => { const p=document.querySelector('[data-wa-pane]'); if(p) p.scrollTop = 0; }""")
        page.wait_for_timeout(2500)
        n = rows(page)
        print(f"  scroll {i+1}: rows={n}", flush=True)
        if n <= last:
            quiet += 1
            if quiet >= quiet_limit:
                print("  (tidak bertambah, berhenti)", flush=True)
                break
        else:
            quiet = 0
        last = n


def collect(page):
    return page.evaluate("""() => {
      const out=[];
      document.querySelectorAll('#main [role="row"]').forEach((r,i)=>{
        const img = r.querySelector('img[src^="blob:"], img[src^="data:"]');
        const view = r.querySelector('div[title^="View"], [aria-label*="Open picture" i]');
        const txt = (r.innerText||'').split(String.fromCharCode(10)).map(x=>x.trim()).filter(Boolean).join(' | ').slice(0,200);
        if (img || view) out.push({i, img: !!img, view: !!view, t: txt});
      });
      return JSON.stringify(out);
    }""")


ap = argparse.ArgumentParser()
ap.add_argument("chat")
ap.add_argument("--rounds", type=int, default=40)
a = ap.parse_args()

with sync_playwright() as p:
    page = get_page(p)
    open_chat(page, a.chat)
    print(f"[chat] {a.chat} — rows awal: {rows(page)}", flush=True)
    scroll_up(page, a.rounds)
    items = json.loads(collect(page))
    print(f"\n[hasil] {rows(page)} pesan, {len(items)} bubble media\n")
    for it in items:
        kind = "IMG" if it["img"] else "MEDIA"
        print(f"  [{it['i']:>4}] {kind:5} {it['t']}")
