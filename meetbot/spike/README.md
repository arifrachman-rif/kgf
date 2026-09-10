# Day-1 spike: does headless Chrome pump WebAudio graphs?

**Verdict: YES. `--headless=new` pumps WebAudio graphs built from media elements. The architecture holds. xvfb is NOT required.**

The assumption under test was that headless Chrome, having no audio output device, might never drive the render graph. That fear is **unfounded**. Chrome falls back to a null audio sink that clocks the graph in real time, and PCM flows normally.

But there is a hard prerequisite that is easy to mistake for "headless audio is broken":

> **`--autoplay-policy=no-user-gesture-required` is MANDATORY.** Without it every probe is bit-exact silent — in headless AND under xvfb alike. This is an autoplay-policy failure, not a headless failure.

---

## Environment

| | |
|---|---|
| Chrome | `149.0.7827.55` (playwright chromium-1228) |
| Host | WSL2 Ubuntu, kernel 6.18.33.2-microsoft-standard-WSL2 |
| xvfb | installed (`/usr/bin/xvfb-run`, `/usr/bin/Xvfb`) |
| Date | 2026-07-19 |

Every run used its own Chrome on its own debug port (9333-9370) with a throwaway `--user-data-dir`. **Port 9222 / `tln-browser.service` and the vexa containers were never touched** (verified alive and healthy after the matrix).

---

## Results: 12-cell matrix, 2 repetitions, 100% consistent

| Mode | `--autoplay-policy` | oscillator | `<audio>`→MediaElementSource→Analyser | AudioWorklet |
|---|---|---|---|---|
| `--headless=new` | absent | SILENT | SILENT | SILENT |
| `--headless=new` | **no-user-gesture-required** | **FLOWS** | **FLOWS** | **FLOWS** |
| `--headless=old` | absent | SILENT | SILENT | SILENT |
| `--headless=old` | **no-user-gesture-required** | **FLOWS** | **FLOWS** | **FLOWS** |
| `xvfb-run` (headed) | absent | SILENT | SILENT | SILENT |
| `xvfb-run` (headed) | **no-user-gesture-required** | **FLOWS** | **FLOWS** | **FLOWS** |

The only variable that determines success is the autoplay flag. Headless vs. headed is **irrelevant** to whether audio flows.

### Evidence that the samples are real, not merely non-zero

The test signal is a generated 5s 440 Hz stereo WAV at amplitude **0.8**, played through a real `<audio>` element.

- Measured `peakAbs` = **0.8000107** — matches the source amplitude to 5 decimal places.
- Analyser dominant bin = **431 Hz**. FFT bin width is 44100/2048 = 21.5 Hz, so 431 Hz is the nearest bin to the 440 Hz tone. Correct.
- AudioWorklet saw **128 000 frames in a 3 s window** at 44.1 kHz = 2.90 s of audio. The graph runs in **real time**, not stalled and not free-running.
- `nonZeroQuanta` = 1000/1000 and `nonZeroFrames` = 60/60. No dropouts.
- `element.currentTime` advanced 3.02 s over 3 s wall clock.

### What silence looks like without the flag

```
ctxState:      "suspended"  (stays suspended)
ctx.resume():  TIMEOUT after 2000ms   <-- does NOT reject, it never settles
el.play():     NotAllowedError: play() failed because the user didn't
               interact with the document first
peakAbs:       0
console:       "The AudioContext was not allowed to start."
```

---

## Four gotchas that cost real debugging time

**1. `ctx.resume()` hangs instead of rejecting.**
Under a blocking autoplay policy the promise never settles. An `await ctx.resume()` with no timeout deadlocks the caller forever. My first driver run hit exactly this and hung to the 120 s timeout with no output. **Bound every audio-related await.**

**2. `file://` silently breaks AudioWorklet.**
A `file://` document has a null origin, so Chrome refuses the worklet module: `Not allowed to load local resource: blob:null/...` → `AbortError: Unable to load a worklet's module`. This looks exactly like "headless can't do worklets" but is pure origin policy. **Serve the page over `http://127.0.0.1`.** The harness now runs its own tiny HTTP server for this reason.

**3. The null audio sink has variable spin-up latency — this WILL cause flaky captures.**
Measured `clockStartMs` (time until `ctx.currentTime` first advances) ranged from **25 ms to 2235 ms** across otherwise identical runs. One early run recorded a false SILENT purely because it sampled during spin-up. **Do not start recording on a timer. Gate on `ctx.currentTime` actually advancing** (see `waitForClock` in `audio_probe.html`). This is the single most likely source of "the bot joined but recorded nothing" in production.

**4. `--mute-audio` is safe.** Explicitly tested: it mutes the output sink but does **not** stop the graph (134 400 frames, peak 0.8000). Safe to keep in a bot launcher.

---

## Recommended launch configuration

```
chrome \
  --headless=new \
  --autoplay-policy=no-user-gesture-required \   # MANDATORY
  --remote-debugging-port=<port> \
  --user-data-dir=<throwaway> \
  --no-first-run --no-default-browser-check \
  --disable-gpu --no-sandbox --disable-dev-shm-usage
```

Serve the capture page over `http://127.0.0.1`, never `file://`.

---

## Reproducing

```bash
cd <meetbot>/spike

# single cell
node run_probe.mjs --port 9333 --mode headless-new --autoplay

# full matrix (12 cells, ~6 min); raw JSON lands in results/
REPS=2 ./run_matrix.sh
```

Flags: `--mode headless-new|headless-old|xvfb`, `--autoplay`, `--mute-audio`, `--keep` (leave Chrome running), `--port N` (refuses 9222).

### Files

- `audio_probe.html` — three probes: `probeOscillator` (control: does the graph render at all), `probeMediaElement` (the real case), `probeWorklet` (the capture path). All awaits are bounded.
- `run_probe.mjs` — launches its own Chrome, drives the probes over raw CDP (no dependencies, node 22 global `WebSocket`), emits JSON.
- `run_matrix.sh` — sweeps mode x autoplay x reps.
- `results/` — raw JSON from the matrix run.

The driver spawns Chrome `detached` and kills the **process group**. Without this, `xvfb` mode orphans the real Chrome (killing the `xvfb-run` wrapper leaves its child holding the debug port) — this bit during the spike and is fixed.

---

## Impact on architecture

No change required. The `--headless=new` design stands; drop xvfb from the plan. Two things must be carried into the implementation:

1. Ship `--autoplay-policy=no-user-gesture-required` in the launcher, with a comment explaining that removing it produces silent recordings rather than an error.
2. Gate capture start on the audio clock advancing, not on a fixed sleep.
