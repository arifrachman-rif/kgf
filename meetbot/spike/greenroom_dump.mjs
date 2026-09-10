// Dump what meetbot's browser actually sees at the Meet green room.
//
// meetbot bails in ~5s with the marker "You can't join this video call" while
// vexa's bot joins the same meeting fine. innerText already respects
// visibility, so this is not a hidden-node false positive — we need the real
// rendered text, plus the sign-in state, to explain the difference.
//
// Zero deps, raw CDP over the DevTools websocket, same pattern as run_probe.mjs.
import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const URL_ = process.argv[2]
const PORT = Number(process.argv[3] || 9345)
const WAIT_MS = Number(process.argv[4] || 9000)
const CHROME = process.env.CHROME_PATH ||
  `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`

if (!URL_) {
  console.error('usage: node greenroom_dump.mjs <meet-url> [port] [wait_ms]')
  process.exit(2)
}

const profile = mkdtempSync(join(tmpdir(), 'greenroom-'))
// STEALTH toggle: pass "stealth" as argv[5] to add the anti-automation flags.
// Google refuses meetbot outright ("You can't join this video call", no green
// room at all) while vexa's Playwright bot reaches awaiting_admission on the
// SAME meeting. Prime suspect is automation detection.
const STEALTH = process.argv[5] === 'stealth'

const args = [
  '--headless=new',
  ...(STEALTH
    ? [
        '--disable-blink-features=AutomationControlled',
        '--lang=en-US',
        '--window-size=1280,720',
      ]
    : []),
  `--remote-debugging-port=${PORT}`,
  '--no-sandbox',
  '--disable-dev-shm-usage',
  '--disable-gpu',
  '--autoplay-policy=no-user-gesture-required',
  '--use-fake-ui-for-media-stream',
  '--use-fake-device-for-media-stream',
  // DUMP_PROFILE lets this run against the signed-in bot profile (pass a COPY —
  // Chrome locks a user-data-dir, and the master must not be mutated).
  `--user-data-dir=${process.env.DUMP_PROFILE || profile}`,
  '--no-first-run',
  '--no-default-browser-check',
  'about:blank',
]

const chrome = spawn(CHROME, args, { detached: true, stdio: 'ignore' })

const sleep = ms => new Promise(r => setTimeout(r, ms))

async function getJSON(path) {
  const r = await fetch(`http://127.0.0.1:${PORT}${path}`)
  return r.json()
}

async function waitForCDP() {
  for (let i = 0; i < 40; i++) {
    try { return await getJSON('/json/version') } catch { await sleep(500) }
  }
  throw new Error('CDP never came up')
}

function cdp(wsUrl) {
  return new Promise((resolve, reject) => {
    // node's built-in WebSocket (node >= 22)
    const ws = new WebSocket(wsUrl)
    let id = 0
    const pending = new Map()
    ws.onopen = () => resolve({
      send(method, params = {}, sessionId) {
        return new Promise((res, rej) => {
          const msgId = ++id
          pending.set(msgId, { res, rej })
          ws.send(JSON.stringify({ id: msgId, method, params, sessionId }))
        })
      },
      close: () => ws.close(),
    })
    ws.onerror = e => reject(new Error('ws error: ' + (e?.message || 'unknown')))
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

const EXPR = `(() => {
  const t = document.body ? document.body.innerText : '';
  const btns = [...document.querySelectorAll('button, [role=button]')]
    .map(b => (b.innerText || b.getAttribute('aria-label') || '').trim())
    .filter(Boolean).slice(0, 25);
  const inputs = [...document.querySelectorAll('input')]
    .map(i => ({ type: i.type, ph: i.placeholder, al: i.getAttribute('aria-label') }));
  return JSON.stringify({
    url: location.href,
    title: document.title,
    text: t.slice(0, 2500),
    buttons: btns,
    inputs,
  }, null, 2);
})()`

try {
  const v = await waitForCDP()
  const conn = await cdp(v.webSocketDebuggerUrl)
  const { targetId } = await conn.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await conn.send('Target.attachToTarget', { targetId, flatten: true })
  await conn.send('Page.enable', {}, sessionId)
  await conn.send('Page.navigate', { url: URL_ }, sessionId)
  await sleep(WAIT_MS)
  const r = await conn.send('Runtime.evaluate', { expression: EXPR, returnByValue: true }, sessionId)
  console.log(r.result.value)
  conn.close()
} finally {
  try { process.kill(-chrome.pid, 'SIGKILL') } catch {}
  try { rmSync(profile, { recursive: true, force: true }) } catch {}
}
