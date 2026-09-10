#!/usr/bin/env node
// Headless WebAudio go/no-go driver.
//
// Launches its OWN Chrome (never touches the one on 9222), loads
// audio_probe.html, and runs three probes over CDP:
//   oscillator     - control: does the render graph advance at all
//   mediaElement   - the real case: <audio> -> MediaElementSource -> Analyser
//   worklet        - the capture case: same graph pulled by an AudioWorkletProcessor
//
// Usage: node run_probe.mjs [--port N] [--mode headless-new|headless-old|xvfb]
//                           [--autoplay] [--keep]

import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import http from 'node:http';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME_PATH ||
  `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`;

// Serve over http rather than file://. A file:// document has a null origin, and
// Chrome refuses to load an AudioWorklet module from a blob: URL under it
// ("Not allowed to load local resource: blob:null/..."), which would fail the
// worklet probe for reasons that have nothing to do with headless audio.
const httpServer = http.createServer((req, res) => {
  const body = fs.readFileSync(path.join(HERE, 'audio_probe.html'));
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(body);
});
const HTTP_PORT = 18080 + Math.floor(Math.random() * 900);
httpServer.listen(HTTP_PORT, '127.0.0.1');
const PAGE = `http://127.0.0.1:${HTTP_PORT}/audio_probe.html`;

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return def;
  const v = process.argv[i + 1];
  return v && !v.startsWith('--') ? v : true;
}
const PORT = Number(arg('port', 9333));
const MODE = String(arg('mode', 'headless-new'));
const AUTOPLAY = process.argv.includes('--autoplay');
const KEEP = process.argv.includes('--keep');

if (PORT === 9222) {
  console.error('refusing to use port 9222 (production tln-browser.service)');
  process.exit(2);
}

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'meetbot-spike-'));

const baseFlags = [
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-gpu',
  '--no-sandbox',
  '--disable-dev-shm-usage',
  // Without a real output device Chrome may fall back to a null audio sink.
  // We do NOT pass --mute-audio: that is exactly the thing under test.
];
if (AUTOPLAY) baseFlags.push('--autoplay-policy=no-user-gesture-required');
if (process.argv.includes('--mute-audio')) baseFlags.push('--mute-audio');

let cmd, args;
if (MODE === 'headless-new') {
  cmd = CHROME; args = ['--headless=new', ...baseFlags, PAGE];
} else if (MODE === 'headless-old') {
  cmd = CHROME; args = ['--headless=old', ...baseFlags, PAGE];
} else if (MODE === 'xvfb') {
  cmd = 'xvfb-run';
  args = ['-a', '-s', '-screen 0 1280x720x24', CHROME, ...baseFlags, PAGE];
} else {
  console.error('unknown mode: ' + MODE);
  process.exit(2);
}

// detached:true puts the child in its own process group so we can signal the
// whole tree. Required for xvfb mode: killing the xvfb-run wrapper alone leaves
// the real Chrome orphaned and holding its debug port.
const child = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'], detached: true });
const chromeLog = [];
child.stdout.on('data', d => chromeLog.push(String(d)));
child.stderr.on('data', d => chromeLog.push(String(d)));

async function waitForPageTarget(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await r.json();
      const page = list.find(t => t.type === 'page' && t.webSocketDebuggerUrl);
      if (page) return page;
    } catch { /* not up yet */ }
    await sleep(250);
  }
  throw new Error('chrome debug endpoint never came up on ' + PORT);
}

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.consoleLines = [];
    ws.addEventListener('message', ev => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
      } else if (msg.method === 'Runtime.consoleAPICalled') {
        this.consoleLines.push(msg.params.args.map(a => a.value ?? a.description ?? a.type).join(' '));
      } else if (msg.method === 'Log.entryAdded') {
        this.consoleLines.push('[log] ' + msg.params.entry.text);
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  async eval(expr, timeoutMs = 30000) {
    const r = await this.send('Runtime.evaluate', {
      expression: expr, awaitPromise: true, returnByValue: true, timeout: timeoutMs,
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result.value;
  }
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    ws.addEventListener('open', () => resolve(ws));
    ws.addEventListener('error', e => reject(new Error('ws error: ' + e.message)));
  });
}

function verdict(r) {
  if (!r || r.error) return 'ERROR';
  if (r.probe === 'media_element_worklet') {
    return (r.nonZeroQuanta > 0 && r.peakAbs > 0.01) ? 'AUDIO FLOWS' : 'SILENT';
  }
  return (r.nonZeroFrames > 0 && r.peakAbs > 0.01) ? 'AUDIO FLOWS' : 'SILENT';
}

(async () => {
  const out = {
    mode: MODE, autoplayFlag: AUTOPLAY, port: PORT,
    launchArgv: [cmd, ...args].join(' '),
    results: {}, verdicts: {}, chromeVersion: null, console: [],
  };
  const stage = s => { out.lastStage = s; process.stderr.write('[stage] ' + s + '\n'); };
  try {
    stage('wait-for-target');
    const target = await waitForPageTarget();
    try {
      const v = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json();
      out.chromeVersion = v.Browser;
    } catch {}

    stage('connect-ws');
    const cdp = new Cdp(await connect(target.webSocketDebuggerUrl));
    await cdp.send('Runtime.enable');
    await cdp.send('Log.enable');
    await cdp.send('Page.enable');

    stage('navigate');
    // The page may have been given as a startup arg, but navigate explicitly so
    // this works regardless of how the target came up.
    await cdp.send('Page.navigate', { url: PAGE });
    await cdp.eval(`new Promise(r => {
      if (document.readyState === 'complete' && window.probeOscillator) return r(1);
      const t = setInterval(() => { if (window.probeOscillator) { clearInterval(t); r(1); } }, 100);
    })`, 15000);

    stage('probe-oscillator');
    out.results.oscillator   = await cdp.eval('probeOscillator({ms:2000})', 20000);
    stage('probe-media-element');
    out.results.mediaElement = await cdp.eval('probeMediaElement({ms:3000})', 30000);
    stage('probe-worklet');
    out.results.worklet      = await cdp.eval('probeWorklet({ms:3000})', 30000);
    stage('done');
    for (const [k, v] of Object.entries(out.results)) out.verdicts[k] = verdict(v);
    out.console = cdp.consoleLines;
  } catch (e) {
    out.fatal = String(e && e.stack || e);
  } finally {
    out.chromeStderrTail = chromeLog.join('').split('\n').filter(Boolean).slice(-25);
    if (!KEEP) { try { process.kill(-child.pid, 'SIGKILL'); } catch { try { child.kill('SIGKILL'); } catch {} } }
    try { httpServer.close(); } catch {}
    console.log(JSON.stringify(out, null, 2));
    if (!KEEP) { try { fs.rmSync(profile, { recursive: true, force: true }); } catch {} }
    process.exit(0);
  }
})();
