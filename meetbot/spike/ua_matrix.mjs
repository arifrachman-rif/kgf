// Bisect why Meet refuses meetbot but admits vexa on the SAME live meeting.
//
// Varies one axis at a time: headless mode, UA override, and the automation
// flags. Dumps the rendered green room plus the fingerprint Meet actually
// cross-checks (navigator.webdriver, userAgentData, WebGL renderer) so a
// refusal can be attributed rather than guessed.
//
// usage: node ua_matrix.mjs <meet-url> <variant> [port]
//   variants: baseline | ua149 | ua149-headful | ua149-headful-stealth
import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const URL_ = process.argv[2]
const VARIANT = process.argv[3] || 'baseline'
const PORT = Number(process.argv[4] || 9345)
const CHROME = process.env.CHROME_PATH ||
  `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`
const UA149 =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.55 Safari/537.36'

if (!URL_) {
  console.error('usage: node ua_matrix.mjs <meet-url> <variant> [port]')
  process.exit(2)
}

const profile = mkdtempSync(join(tmpdir(), 'uamatrix-'))
const common = [
  `--remote-debugging-port=${PORT}`,
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-dev-shm-usage',
  '--autoplay-policy=no-user-gesture-required',
  '--use-fake-ui-for-media-stream',
  '--use-fake-device-for-media-stream',
  `--user-data-dir=${profile}`,
  '--no-first-run',
  '--no-default-browser-check',
  '--lang=en-US',
  '--window-size=1920,1080',
]
// vexa's GPU story: headful under Xvfb with software GL, NOT --disable-gpu
// alone. A missing/blocked WebGL renderer is itself a bot signal.
const vexaGpu = ['--disable-gpu', '--in-process-gpu', '--use-gl=angle', '--use-angle=swiftshader-webgl']

const VARIANTS = {
  baseline: ['--headless=new', '--disable-gpu'],
  ua149: ['--headless=new', '--disable-gpu', `--user-agent=${UA149}`],
  // chromiumoxide injects --enable-automation unconditionally (DEFAULT_ARGS),
  // which sets navigator.webdriver = true. This variant reproduces meetbot.
  'ua149-automation': ['--headless=new', '--disable-gpu', `--user-agent=${UA149}`, '--enable-automation'],
  // ...and this one tests the proposed antidote.
  'ua149-automation-blinkfix': [
    '--headless=new', '--disable-gpu', `--user-agent=${UA149}`, '--enable-automation',
    '--disable-blink-features=AutomationControlled',
  ],
  // Was the stale-version UA load-bearing on its own, or only the Headless
  // token? Chrome/128 is not a headless UA but contradicts the 149 Client-Hints.
  ua128: [
    '--headless=new', '--disable-gpu',
    '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    '--disable-blink-features=AutomationControlled',
  ],
  // meetbot's live chrome carries four flags that come from neither its own
  // LAUNCH_FLAGS nor chromiumoxide's DEFAULT_ARGS. Do they re-trip the gate?
  'ua149-ozone': [
    '--headless=new', '--disable-gpu', `--user-agent=${UA149}`,
    '--enable-automation', '--disable-blink-features=AutomationControlled',
    '--noerrdialogs', '--ozone-platform=headless',
    '--ozone-override-screen-size=800,600', '--use-angle=swiftshader-webgl',
  ],
  'ua149-headful': [...vexaGpu, `--user-agent=${UA149}`],
  'ua149-headful-stealth': [
    ...vexaGpu,
    `--user-agent=${UA149}`,
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--disable-infobars',
    '--incognito',
  ],
}
const extra = VARIANTS[VARIANT]
if (!extra) {
  console.error(`unknown variant ${VARIANT}; have: ${Object.keys(VARIANTS).join(', ')}`)
  process.exit(2)
}

const headful = !extra.includes('--headless=new')
const args = [...extra, ...common, 'about:blank']
const bin = headful ? 'xvfb-run' : CHROME
const argv = headful ? ['-a', '-s', '-screen 0 1920x1080x24', CHROME, ...args] : args

const chrome = spawn(bin, argv, { detached: true, stdio: 'ignore' })
const sleep = ms => new Promise(r => setTimeout(r, ms))

async function getJSON(path) {
  const r = await fetch(`http://127.0.0.1:${PORT}${path}`)
  return r.json()
}
async function waitForCDP() {
  for (let i = 0; i < 60; i++) {
    try { return await getJSON('/json/version') } catch { await sleep(500) }
  }
  throw new Error('CDP never came up')
}
function cdp(wsUrl) {
  return new Promise((resolve, reject) => {
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

const EXPR = `(async () => {
  const t = document.body ? document.body.innerText : '';
  const btns = [...document.querySelectorAll('button, [role=button]')]
    .map(b => (b.innerText || b.getAttribute('aria-label') || '').trim())
    .filter(Boolean).slice(0, 20);
  const inputs = [...document.querySelectorAll('input')]
    .map(i => ({ type: i.type, ph: i.placeholder, al: i.getAttribute('aria-label') }));
  let gl = null;
  try {
    const c = document.createElement('canvas').getContext('webgl');
    const d = c.getExtension('WEBGL_debug_renderer_info');
    gl = { vendor: c.getParameter(d.UNMASKED_VENDOR_WEBGL), renderer: c.getParameter(d.UNMASKED_RENDERER_WEBGL) };
  } catch (e) { gl = 'unavailable: ' + e.message }
  let uad = null;
  try { uad = await navigator.userAgentData.getHighEntropyValues(['platform','platformVersion','uaFullVersion','fullVersionList']) } catch (e) { uad = 'none' }
  return JSON.stringify({
    url: location.href, title: document.title,
    text: t.slice(0, 900), buttons: btns, inputs,
    webdriver: navigator.webdriver,
    ua: navigator.userAgent,
    uaData: uad, webgl: gl,
    languages: navigator.languages,
  }, null, 2);
})()`

try {
  const v = await waitForCDP()
  const conn = await cdp(v.webSocketDebuggerUrl)
  const { targetId } = await conn.send('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await conn.send('Target.attachToTarget', { targetId, flatten: true })
  await conn.send('Page.enable', {}, sessionId)
  // Reproduce meetbot's belt-and-braces CDP override, which is applied on top
  // of the (already correct) --user-agent launch flag.
  if (process.env.CDP_UA_OVERRIDE === '1') {
    await conn.send('Network.setUserAgentOverride', { userAgent: UA149 }, sessionId)
  }
  await conn.send('Page.navigate', { url: URL_ }, sessionId)
  await sleep(12000)
  const r = await conn.send('Runtime.evaluate', {
    expression: EXPR, returnByValue: true, awaitPromise: true,
  }, sessionId)
  console.log(`===== VARIANT: ${VARIANT} =====`)
  console.log(r.result.value)
  conn.close()
} finally {
  try { process.kill(-chrome.pid, 'SIGKILL') } catch {}
  try { rmSync(profile, { recursive: true, force: true }) } catch {}
}
