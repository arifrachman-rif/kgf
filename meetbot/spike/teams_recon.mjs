#!/usr/bin/env node
// Teams anonymous-join recon driver.
//
// Launches its OWN Chrome (NEVER 9222 / tln-browser.service), navigates a
// Teams meet URL, records the full redirect chain via CDP Network events, and
// dumps the resulting DOM: data-tid attributes, aria-labels, roles, buttons,
// inputs, and visible text.
//
// Usage: node teams_recon.mjs --url <url> [--port N] [--wait ms] [--out name]
//                             [--click <data-tid>] [--headful]

import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME_PATH ||
  `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`;
const OUTDIR = path.join(HERE, 'teams_recon');
fs.mkdirSync(OUTDIR, { recursive: true });

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return def;
  const v = process.argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}

const URL_ = String(arg('url', 'https://teams.microsoft.com/meet/1234567890123'));
const PORT = Number(arg('port', 9411));
const WAIT = Number(arg('wait', 12000));
const OUT = String(arg('out', 'run'));
const CLICK = arg('click', null);

if (PORT === 9222) { console.error('refusing port 9222'); process.exit(2); }

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'teams-recon-'));
const flags = [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check',
  '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
  '--window-size=1280,900',
  // Teams sniffs UA hard; use a normal desktop Chrome UA rather than HeadlessChrome.
  '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
  '--lang=en-US',
  'about:blank',
];

const child = spawn(CHROME, flags, { stdio: ['ignore', 'pipe', 'pipe'], detached: true });
const chromeLog = [];
child.stdout.on('data', d => chromeLog.push(String(d)));
child.stderr.on('data', d => chromeLog.push(String(d)));

async function waitTarget(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await r.json();
      const p = list.find(t => t.type === 'page' && t.webSocketDebuggerUrl);
      if (p) return p;
    } catch { /* not up */ }
    await sleep(250);
  }
  throw new Error('chrome never came up on ' + PORT);
}

class Cdp {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    this.console = []; this.redirects = []; this.docs = []; this.frames = [];
    ws.addEventListener('message', ev => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id);
        this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
        return;
      }
      if (m.method === 'Network.requestWillBeSent') {
        const p = m.params;
        if (p.redirectResponse) {
          this.redirects.push({
            kind: 'http', status: p.redirectResponse.status,
            from: p.redirectResponse.url, to: p.request.url,
            location: p.redirectResponse.headers?.location || p.redirectResponse.headers?.Location,
          });
        }
        if (p.type === 'Document') this.docs.push({ kind: 'doc-request', url: p.request.url });
      } else if (m.method === 'Network.responseReceived' && m.params.type === 'Document') {
        this.docs.push({ kind: 'doc-response', status: m.params.response.status, url: m.params.response.url });
      } else if (m.method === 'Page.frameNavigated') {
        this.frames.push({ url: m.params.frame.url, parent: m.params.frame.parentId || null });
      } else if (m.method === 'Runtime.consoleAPICalled') {
        this.console.push(m.params.args.map(a => a.value ?? a.description ?? a.type).join(' '));
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((res, rej) => this.pending.set(id, { resolve: res, reject: rej }));
  }
  async eval(expr, timeoutMs = 30000) {
    const r = await this.send('Runtime.evaluate', {
      expression: expr, awaitPromise: true, returnByValue: true, timeout: timeoutMs,
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 800));
    return r.result.value;
  }
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    ws.addEventListener('open', () => resolve(ws));
    ws.addEventListener('error', e => reject(new Error('ws: ' + e.message)));
  });
}

// The DOM harvester. Runs inside the page, walks the main document AND every
// same-origin iframe, and reports the things a selector table is built from.
const HARVEST = `(() => {
  function visible(el) {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  }
  function describe(el) {
    return {
      tag: el.tagName.toLowerCase(),
      tid: el.getAttribute('data-tid'),
      id: el.id || null,
      type: el.getAttribute('type'),
      role: el.getAttribute('role'),
      aria: el.getAttribute('aria-label'),
      ariaLabelledBy: el.getAttribute('aria-labelledby'),
      placeholder: el.getAttribute('placeholder'),
      name: el.getAttribute('name'),
      text: (el.innerText || el.textContent || '').trim().slice(0, 120) || null,
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true' || null,
      visible: visible(el),
      cls: (el.className && typeof el.className === 'string') ? el.className.slice(0, 120) : null,
    };
  }
  function scan(doc, label) {
    const out = { frame: label, url: doc.location ? doc.location.href : null, title: doc.title };
    const q = (sel) => Array.from(doc.querySelectorAll(sel));
    out.allDataTids = Array.from(new Set(q('[data-tid]').map(e => e.getAttribute('data-tid')))).sort();
    out.buttons = q('button, [role=button], a[href]').filter(visible).map(describe).slice(0, 80);
    out.inputs = q('input, textarea, [role=textbox], [contenteditable=true]').map(describe);
    out.headings = q('h1,h2,h3,[role=heading]').filter(visible).map(describe).slice(0, 30);
    out.ariaLive = q('[aria-live], [role=alert], [role=status]').map(describe).slice(0, 30);
    out.bodyText = (doc.body ? (doc.body.innerText || '') : '').replace(/\\n{3,}/g, '\\n\\n').trim().slice(0, 4000);
    out.bodyHtmlLen = doc.body ? doc.body.outerHTML.length : 0;
    return out;
  }
  const res = { top: scan(document, 'top'), frames: [], location: location.href, iframeSrcs: [] };
  for (const f of Array.from(document.querySelectorAll('iframe'))) {
    res.iframeSrcs.push({ src: f.src, tid: f.getAttribute('data-tid'), name: f.name, id: f.id });
    try {
      if (f.contentDocument) res.frames.push(scan(f.contentDocument, f.src || f.name || 'iframe'));
    } catch (e) { res.frames.push({ frame: f.src, error: 'cross-origin: ' + e.message }); }
  }
  return res;
})()`;

(async () => {
  const target = await waitTarget();
  const ws = await connect(target.webSocketDebuggerUrl);
  const cdp = new Cdp(ws);
  await cdp.send('Network.enable');
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Emulation.setUserAgentOverride', {
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    acceptLanguage: 'en-US,en',
    platform: 'Linux x86_64',
  });
  // Grant mic/cam so Teams does not divert into a permissions interstitial.
  try {
    await cdp.send('Browser.grantPermissions', {
      origin: 'https://teams.microsoft.com',
      permissions: ['audioCapture', 'videoCapture'],
    });
  } catch (e) { cdp.console.push('grantPermissions failed: ' + e.message); }

  await cdp.send('Page.navigate', { url: URL_ });
  await sleep(WAIT);

  const snap = {};
  snap.requestedUrl = URL_;
  snap.httpRedirects = cdp.redirects;
  snap.documentTimeline = cdp.docs;
  snap.frameNavigations = cdp.frames;
  snap.beforeClick = await cdp.eval(HARVEST);

  if (CLICK && CLICK !== true) {
    const clicked = await cdp.eval(`(() => {
      const el = document.querySelector(${JSON.stringify(CLICK)});
      if (!el) return 'NOT FOUND: ' + ${JSON.stringify(CLICK)};
      el.click();
      return 'clicked: ' + (el.innerText || el.getAttribute('data-tid'));
    })()`);
    snap.clickResult = clicked;
    await sleep(WAIT);
    snap.afterClick = await cdp.eval(HARVEST);
    snap.afterClickRedirects = cdp.redirects;
    snap.afterClickFrames = cdp.frames;
  }

  snap.console = cdp.console.slice(0, 200);
  snap.finalUrl = await cdp.eval('location.href');

  fs.writeFileSync(path.join(OUTDIR, OUT + '.json'), JSON.stringify(snap, null, 2));

  // Screenshot for the record.
  try {
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTDIR, OUT + '.png'), Buffer.from(shot.data, 'base64'));
  } catch { /* best effort */ }

  // Full HTML of the final surface, for grepping selectors by hand.
  const html = await cdp.eval('document.documentElement.outerHTML');
  fs.writeFileSync(path.join(OUTDIR, OUT + '.html'), html || '');

  console.log(JSON.stringify({
    out: path.join(OUTDIR, OUT + '.json'),
    finalUrl: snap.finalUrl,
    redirects: cdp.redirects.map(r => r.status + ' ' + r.from + ' -> ' + r.to),
    docs: cdp.docs,
    tids: snap.beforeClick?.top?.allDataTids,
    iframes: snap.beforeClick?.iframeSrcs,
    frameTids: (snap.beforeClick?.frames || []).map(f => ({ f: f.frame, tids: f.allDataTids, err: f.error })),
    bodyText: snap.beforeClick?.top?.bodyText,
  }, null, 2));

  try { process.kill(-child.pid, 'SIGTERM'); } catch {}
  fs.rmSync(profile, { recursive: true, force: true });
  process.exit(0);
})().catch(e => {
  console.error('FAILED: ' + e.message);
  console.error(chromeLog.join('').slice(-2000));
  try { process.kill(-child.pid, 'SIGTERM'); } catch {}
  process.exit(1);
});
