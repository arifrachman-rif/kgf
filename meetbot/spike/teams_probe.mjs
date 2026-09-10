#!/usr/bin/env node
// Focused Teams probe: answers narrow questions the flow driver left open.
//   --ua default|spoof   : run with Chrome's real headless UA vs a desktop UA
//   --fillname yes|no    : whether to type a display name before snapshotting
// Never uses port 9222.

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

const argv = process.argv;
const arg = (n, d) => { const i = argv.indexOf('--' + n); if (i === -1) return d; const v = argv[i + 1]; return v && !v.startsWith('--') ? v : true; };

const URL_ = String(arg('url', 'https://teams.microsoft.com/meet/1234567890123'));
const PORT = Number(arg('port', 9441));
const OUT = String(arg('out', 'probe'));
const UAMODE = String(arg('ua', 'spoof'));
const FILLNAME = String(arg('fillname', 'no'));
const SETTLE = Number(arg('settle', 15000));
const SPOOF_UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

if (PORT === 9222) { console.error('refusing port 9222'); process.exit(2); }
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'teams-probe-'));

const flags = ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--no-sandbox',
  '--disable-dev-shm-usage', '--window-size=1280,900', '--lang=en-US',
  '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'];
if (UAMODE === 'spoof') flags.push(`--user-agent=${SPOOF_UA}`);
flags.push('about:blank');

const child = spawn(CHROME, flags, { stdio: ['ignore', 'pipe', 'pipe'], detached: true });
const clog = []; child.stdout.on('data', d => clog.push(String(d))); child.stderr.on('data', d => clog.push(String(d)));

async function waitTarget(t = 20000) {
  const dl = Date.now() + t;
  while (Date.now() < dl) {
    try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find(x => x.type === 'page' && x.webSocketDebuggerUrl); if (p) return p; } catch {}
    await sleep(250);
  }
  throw new Error('no chrome on ' + PORT);
}

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.nav = [];
    ws.addEventListener('message', ev => { const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) { const { resolve, reject } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result); return; }
      if (m.method === 'Page.frameNavigated' && !m.params.frame.parentId) this.nav.push(m.params.frame.url); });
  }
  send(method, params = {}) { const id = ++this.id; this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((res, rej) => this.pending.set(id, { resolve: res, reject: rej })); }
  async eval(e, t = 30000) { const r = await this.send('Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true, timeout: t });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 600)); return r.result.value; }
}
const connect = u => new Promise((res, rej) => { const ws = new WebSocket(u);
  ws.addEventListener('open', () => res(ws)); ws.addEventListener('error', e => rej(new Error('ws ' + e.message))); });

const SNAP = `(() => {
  const vis = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; };
  const d = el => ({ tag: el.tagName.toLowerCase(), tid: el.getAttribute('data-tid'), role: el.getAttribute('role'),
    aria: el.getAttribute('aria-label'), ph: el.getAttribute('placeholder'),
    text: (el.innerText||el.textContent||'').trim().slice(0,140)||null,
    domDisabled: el.disabled===true||null, ariaDisabled: el.getAttribute('aria-disabled'), vis: vis(el) });
  const q = s => Array.from(document.querySelectorAll(s));
  const joinBtn = document.querySelector('[data-tid="prejoin-join-button"]');
  const nameIn  = document.querySelector('[data-tid="prejoin-display-name-input"]');
  const title   = document.querySelector('[data-tid="meeting-header-title"]');
  return {
    url: location.href, title: document.title, ua: navigator.userAgent,
    visibleTids: Array.from(new Set(q('[data-tid]').filter(vis).map(e=>e.getAttribute('data-tid')))).sort(),
    joinButton: joinBtn ? d(joinBtn) : null,
    nameInput: nameIn ? Object.assign(d(nameIn), { value: nameIn.value }) : null,
    meetingHeaderTitle: title ? { text: (title.innerText||'').trim(), html: title.outerHTML.slice(0,400) } : null,
    alerts: q('[role=alert],[aria-live=assertive],[aria-live=polite],[role=status]').filter(vis).map(d).slice(0,20),
    body: (document.body?document.body.innerText:'').replace(/\\n{3,}/g,'\\n\\n').trim().slice(0,2000),
  };
})()`;

(async () => {
  const t = await waitTarget();
  const cdp = new Cdp(await connect(t.webSocketDebuggerUrl));
  await cdp.send('Page.enable'); await cdp.send('Runtime.enable');
  if (UAMODE === 'spoof') {
    await cdp.send('Emulation.setUserAgentOverride', { userAgent: SPOOF_UA, acceptLanguage: 'en-US,en', platform: 'Linux x86_64' });
  }
  try { await cdp.send('Browser.grantPermissions', { origin: 'https://teams.microsoft.com',
    permissions: ['audioCapture', 'videoCapture'] }); } catch {}

  const rec = { url: URL_, uaMode: UAMODE, fillName: FILLNAME, stages: [] };
  await cdp.send('Page.navigate', { url: URL_ });
  await sleep(SETTLE);
  rec.stages.push({ at: 'settled', snap: await cdp.eval(SNAP) });

  if (FILLNAME === 'yes') {
    rec.fillResult = await cdp.eval(`(() => {
      const i = document.querySelector('[data-tid="prejoin-display-name-input"]');
      if (!i) return 'NO INPUT';
      const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      set.call(i, 'Meetbot Recorder');
      i.dispatchEvent(new Event('input', { bubbles: true }));
      i.dispatchEvent(new Event('change', { bubbles: true }));
      return 'filled';
    })()`);
    await sleep(2000);
    rec.stages.push({ at: 'after-fill', snap: await cdp.eval(SNAP) });
  }

  rec.navigations = cdp.nav;
  fs.writeFileSync(path.join(OUTDIR, OUT + '.json'), JSON.stringify(rec, null, 2));
  fs.writeFileSync(path.join(OUTDIR, OUT + '.html'), await cdp.eval('document.documentElement.outerHTML') || '');
  const last = rec.stages[rec.stages.length - 1].snap;
  console.log(JSON.stringify({ uaMode: UAMODE, ua: last.ua, url: last.url, title: last.title,
    joinButton: last.joinButton, nameInput: last.nameInput, meetingHeaderTitle: last.meetingHeaderTitle,
    visibleTids: last.visibleTids, body: last.body, navigations: cdp.nav }, null, 2));
  try { process.kill(-child.pid, 'SIGTERM'); } catch {}
  fs.rmSync(profile, { recursive: true, force: true });
  process.exit(0);
})().catch(e => { console.error('FAILED: ' + e.message); console.error(clog.join('').slice(-1500));
  try { process.kill(-child.pid, 'SIGTERM'); } catch {} process.exit(1); });
