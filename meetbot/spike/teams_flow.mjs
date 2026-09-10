#!/usr/bin/env node
// Teams anonymous-join FLOW driver: navigate -> fill name -> click Join now ->
// snapshot every 3s for N seconds, so we can see the post-join surface
// (lobby / error / passcode prompt) as it evolves.
//
// Usage: node teams_flow.mjs --url <url> --port 9412 --name "Bot" --out name
//                            [--nojoin] [--settle ms] [--watch ms]

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
function arg(n, d) { const i = argv.indexOf('--' + n); if (i === -1) return d; const v = argv[i + 1]; return v && !v.startsWith('--') ? v : true; }

const URL_ = String(arg('url', 'https://teams.microsoft.com/meet/1234567890123'));
const PORT = Number(arg('port', 9412));
const NAME = String(arg('name', 'Meetbot Recorder'));
const OUT = String(arg('out', 'flow'));
const SETTLE = Number(arg('settle', 15000));
const WATCH = Number(arg('watch', 45000));
const NOJOIN = argv.includes('--nojoin');
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

if (PORT === 9222) { console.error('refusing port 9222'); process.exit(2); }
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'teams-flow-'));

const child = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--no-sandbox',
  '--disable-dev-shm-usage', '--window-size=1280,900', `--user-agent=${UA}`, '--lang=en-US',
  '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
  'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'], detached: true });
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
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.console = []; this.nav = [];
    ws.addEventListener('message', ev => { const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) { const { resolve, reject } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result); return; }
      if (m.method === 'Page.frameNavigated' && !m.params.frame.parentId) this.nav.push(m.params.frame.url);
      if (m.method === 'Runtime.consoleAPICalled') this.console.push(m.params.args.map(a => a.value ?? a.description ?? a.type).join(' '));
    });
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
    aria: el.getAttribute('aria-label'), ph: el.getAttribute('placeholder'), type: el.getAttribute('type'),
    text: (el.innerText||el.textContent||'').trim().slice(0,140)||null,
    disabled: el.disabled===true||el.getAttribute('aria-disabled')==='true'||null, vis: vis(el) });
  const q = s => Array.from(document.querySelectorAll(s));
  return {
    url: location.href, title: document.title,
    tids: Array.from(new Set(q('[data-tid]').map(e=>e.getAttribute('data-tid')))).sort(),
    visibleTids: Array.from(new Set(q('[data-tid]').filter(vis).map(e=>e.getAttribute('data-tid')))).sort(),
    buttons: q('button,[role=button]').filter(vis).map(d).slice(0,60),
    inputs: q('input,textarea,[role=textbox],[contenteditable=true]').map(d),
    alerts: q('[role=alert],[aria-live=assertive],[aria-live=polite],[role=status]').filter(vis).map(d).slice(0,20),
    headings: q('h1,h2,h3,[role=heading]').filter(vis).map(d).slice(0,20),
    media: { videos: q('video').length, audios: q('audio').length,
             audioSrcs: q('audio').map(a=>({src:(a.src||'').slice(0,80), muted:a.muted, paused:a.paused, tid:a.getAttribute('data-tid')})) },
    body: (document.body?document.body.innerText:'').replace(/\\n{3,}/g,'\\n\\n').trim().slice(0,2500),
  };
})()`;

(async () => {
  const t = await waitTarget();
  const cdp = new Cdp(await connect(t.webSocketDebuggerUrl));
  await cdp.send('Page.enable'); await cdp.send('Runtime.enable'); await cdp.send('Network.enable');
  await cdp.send('Emulation.setUserAgentOverride', { userAgent: UA, acceptLanguage: 'en-US,en', platform: 'Linux x86_64' });
  try { await cdp.send('Browser.grantPermissions', { origin: 'https://teams.microsoft.com',
    permissions: ['audioCapture', 'videoCapture'] }); } catch {}

  const rec = { url: URL_, name: NAME, stages: [] };
  await cdp.send('Page.navigate', { url: URL_ });
  await sleep(SETTLE);
  rec.stages.push({ at: 'settled', t: SETTLE, snap: await cdp.eval(SNAP) });

  if (!NOJOIN) {
    rec.fill = await cdp.eval(`(() => {
      const i = document.querySelector('input[data-tid="prejoin-display-name-input"]');
      if (!i) return 'NO NAME INPUT';
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(i, ${JSON.stringify(NAME)});
      i.dispatchEvent(new Event('input', { bubbles: true }));
      i.dispatchEvent(new Event('change', { bubbles: true }));
      return 'filled -> ' + i.value;
    })()`);
    await sleep(1500);
    rec.stages.push({ at: 'after-fill', snap: await cdp.eval(SNAP) });

    rec.click = await cdp.eval(`(() => {
      const b = document.querySelector('[data-tid="prejoin-join-button"]');
      if (!b) return 'NO JOIN BUTTON';
      if (b.disabled) return 'JOIN DISABLED';
      b.click(); return 'clicked join';
    })()`);

    const step = 5000;
    for (let e = step; e <= WATCH; e += step) {
      await sleep(step);
      rec.stages.push({ at: 'post-join+' + e + 'ms', snap: await cdp.eval(SNAP) });
    }
  }

  rec.navigations = cdp.nav;
  rec.console = cdp.console.slice(0, 150);
  fs.writeFileSync(path.join(OUTDIR, OUT + '.json'), JSON.stringify(rec, null, 2));
  try { const s = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUTDIR, OUT + '_final.png'), Buffer.from(s.data, 'base64')); } catch {}
  fs.writeFileSync(path.join(OUTDIR, OUT + '_final.html'), await cdp.eval('document.documentElement.outerHTML') || '');

  const last = rec.stages[rec.stages.length - 1].snap;
  console.log(JSON.stringify({ out: OUT, fill: rec.fill, click: rec.click, navigations: rec.navigations,
    finalUrl: last.url, finalTitle: last.title, visibleTids: last.visibleTids,
    alerts: last.alerts, body: last.body }, null, 2));

  try { process.kill(-child.pid, 'SIGTERM'); } catch {}
  process.exit(0);
})().catch(e => { console.error('FAILED: ' + e.message); console.error(clog.join('').slice(-1500));
  try { process.kill(-child.pid, 'SIGTERM'); } catch {} process.exit(1); });
