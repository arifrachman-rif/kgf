// What does Meet actually show AFTER we click "Ask to join"?
//
// meetbot now reaches the green room and clicks the join control, then reports
// `admission denied` 1.5s later with the marker "You can't join this video
// call". 1.5s is far too fast for a human to decline, so it is either a genuine
// auto-decline or meetbot false-positiving on stale/transient DOM while it is
// really sitting in the waiting room. Meet reuses the same copy for both, which
// is exactly why this needs eyes on the real page.
//
// Applies the two fixes proven necessary to reach the green room at all:
// navigator.webdriver must be false (--disable-blink-features=AutomationControlled,
// since chromiumoxide/puppeteer both append --enable-automation) and the UA must
// not carry the HeadlessChrome token.
import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const URL_ = process.argv[2]
const PORT = Number(process.argv[3] || 9351)
const NAME = process.argv[4] || 'Notetaker'
const CHROME = process.env.CHROME_PATH ||
  `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`

const profile = mkdtempSync(join(tmpdir(), 'knock-'))
const chrome = spawn(CHROME, [
  '--headless=new',
  '--disable-blink-features=AutomationControlled',
  `--remote-debugging-port=${PORT}`,
  '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
  '--autoplay-policy=no-user-gesture-required',
  '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
  '--lang=en-US', '--window-size=1280,720',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  'about:blank',
], { detached: true, stdio: 'ignore' })

const sleep = ms => new Promise(r => setTimeout(r, ms))
const getJSON = async p => (await fetch(`http://127.0.0.1:${PORT}${p}`)).json()

async function waitForCDP() {
  for (let i = 0; i < 40; i++) {
    try { return await getJSON('/json/version') } catch { await sleep(500) }
  }
  throw new Error('CDP never came up')
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl)
    let id = 0
    const pending = new Map()
    ws.onopen = () => resolve({
      send: (method, params = {}, sessionId) => new Promise((res, rej) => {
        const msgId = ++id
        pending.set(msgId, { res, rej })
        ws.send(JSON.stringify({ id: msgId, method, params, sessionId }))
      }),
      close: () => ws.close(),
    })
    ws.onerror = e => reject(new Error('ws: ' + (e?.message || '?')))
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data)
      if (m.id && pending.has(m.id)) {
        const { res, rej } = pending.get(m.id)
        pending.delete(m.id)
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result)
      }
    }
  })
}

const SNAP = `(() => {
  const t = document.body ? document.body.innerText : '';
  const btns = [...document.querySelectorAll('button,[role=button]')]
    .map(b => (b.innerText || b.getAttribute('aria-label') || '').trim())
    .filter(Boolean).slice(0, 20);
  return JSON.stringify({ url: location.href, text: t.slice(0, 700), buttons: btns });
})()`

const FILL_AND_KNOCK = `(async () => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const inp = document.querySelector('input[type=text], input[aria-label*="name" i], input[placeholder*="name" i]');
  if (inp) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(inp, ${JSON.stringify(NAME)});
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
  }
  const want = ['ask to join', 'join now', 'request to join'];
  const btn = [...document.querySelectorAll('button,[role=button]')]
    .find(b => want.includes(norm(b.innerText || b.getAttribute('aria-label'))));
  if (btn) { btn.click(); return 'clicked: ' + norm(btn.innerText || btn.getAttribute('aria-label')); }
  return 'NO JOIN BUTTON FOUND (name filled: ' + !!inp + ')';
})()`

try {
  const v = await waitForCDP()
  const c = await connect(v.webSocketDebuggerUrl)
  const { targetId } = await c.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await c.send('Target.attachToTarget', { targetId, flatten: true })
  await c.send('Page.enable', {}, sessionId)
  await c.send('Network.enable', {}, sessionId)
  // Strip the HeadlessChrome token — independently fatal on its own.
  const ua = v['User-Agent'].replace(/HeadlessChrome/g, 'Chrome')
  await c.send('Network.setUserAgentOverride', { userAgent: ua }, sessionId)
  await c.send('Page.navigate', { url: URL_ }, sessionId)
  await sleep(9000)

  const before = await c.send('Runtime.evaluate', { expression: SNAP, returnByValue: true }, sessionId)
  console.log('=== BEFORE KNOCK ===\n' + before.result.value + '\n')

  const click = await c.send('Runtime.evaluate',
    { expression: FILL_AND_KNOCK, awaitPromise: true, returnByValue: true }, sessionId)
  console.log('=== KNOCK: ' + click.result.value + ' ===\n')

  // Sample repeatedly: meetbot declares denial at ~1.5s, so watch that window
  // and well past it to see whether the state is transient or terminal.
  for (const t of [1500, 3000, 5000, 10000, 20000]) {
    await sleep(t === 1500 ? 1500 : t - (t === 3000 ? 1500 : t === 5000 ? 3000 : t === 10000 ? 5000 : 10000))
    const s = await c.send('Runtime.evaluate', { expression: SNAP, returnByValue: true }, sessionId)
    console.log(`=== +${t}ms ===\n` + s.result.value + '\n')
  }
  c.close()
} finally {
  try { process.kill(-chrome.pid, 'SIGKILL') } catch {}
  try { rmSync(profile, { recursive: true, force: true }) } catch {}
}
