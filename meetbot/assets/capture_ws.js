/*
 * meetbot page-side audio capture — WebSocket transport.
 *
 * NOTE ON THE TWO CAPTURE SCRIPTS
 * -------------------------------
 * `assets/capture.js` is the CDP-binding transport described in SPEC §7: it
 * hands base64 i16 frames to `Runtime.addBinding("meetbotAudio")` and has its
 * `__MEETBOT_*__` tokens substituted from the selector table in src/meet.rs.
 * That file is owned by the `meet` module and is the default path.
 *
 * THIS file is the alternative transport: instead of a CDP binding it opens a
 * WebSocket straight to the Rust ingest server (`audio::start_ingest_server`).
 * It exists because the CDP binding serializes every frame through the DevTools
 * protocol on the page's main thread, which is the first thing to stutter in a
 * long call; a raw socket carries binary Float32 with no base64 and no CDP
 * round trip. Both speak 16 kHz mono; pick one per session, never both.
 *
 * Injected into the Google Meet / Teams tab after admission. It taps every
 * <audio>/<video> element the conference renders, mixes them into one
 * MediaStreamDestination, and ships Float32 PCM frames to Rust.
 *
 * Wire format (must stay in sync with src/audio.rs):
 *
 *   binary : [f64 offsetSec LE][f32 sample LE] * N   — one PCM frame
 *   text   : {"type":"hello","sampleRate":16000}     — announced once on open
 *            {"type":"speaker","name":..,"speaking":bool,"t":sec}
 *            {"type":"bye"}                          — clean end of stream
 *
 * `__MEETBOT_INGEST_URL__` is substituted by audio::capture_ws_script() before
 * injection. When the placeholder survives (manual paste into devtools) the
 * script falls back to window.__MEETBOT_INGEST_URL__ then to a default port.
 *
 * Design notes:
 *  - Media elements are tracked in a WeakSet so a MutationObserver re-run, a
 *    Meet re-layout, or a participant rejoining never double-attaches a source.
 *    createMediaElementSource() throws on a second call for the same element,
 *    and a duplicate tap would also double that participant's amplitude.
 *  - Elements whose audio arrives as a MediaStream (Meet's normal case, where
 *    el.srcObject is set and el.src is empty) are tapped with
 *    createMediaStreamSource over the stream's audio tracks. That is more
 *    reliable than createMediaElementSource, which for srcObject-backed
 *    elements can yield silence in headless Chromium.
 *  - Elements tapped with createMediaElementSource are reconnected to
 *    ctx.destination, because that call otherwise steals the element's output.
 */

(function () {
  "use strict";

  if (window.__meetbotWsCapture && window.__meetbotWsCapture.running) {
    return window.__meetbotWsCapture.stats();
  }

  // ---------------------------------------------------------------- config --
  // Split literal so this occurrence is never itself substituted.
  var PLACEHOLDER = "__MEETBOT_INGEST" + "_URL__";
  var INJECTED_URL = "__MEETBOT_INGEST_URL__";
  var INGEST_URL =
    INJECTED_URL !== PLACEHOLDER
      ? INJECTED_URL
      : window.__MEETBOT_INGEST_URL__ || "ws://127.0.0.1:8765/ingest";

  var TARGET_RATE = 16000;
  // 1024 samples @ 16 kHz = 64 ms per frame. Small enough for responsive VAD,
  // large enough that we are not sending 125 websocket messages a second.
  var FRAME_SAMPLES = 1024;
  var RECONNECT_MS = 1000;
  var MAX_RECONNECT_MS = 15000;
  var SCAN_INTERVAL_MS = 2000;
  var SPEAKER_POLL_MS = 400;
  // Drop audio rather than let an unread socket balloon the page's memory.
  var MAX_BUFFERED_BYTES = 4 * 1024 * 1024;

  function log() {
    if (window.__MEETBOT_DEBUG__) {
      console.log.apply(console, ["[meetbot]"].concat([].slice.call(arguments)));
    }
  }

  // ------------------------------------------------------------- ws client --
  var ws = null;
  var wsReady = false;
  var reconnectDelay = RECONNECT_MS;
  var reconnectTimer = null;
  var stopped = false;
  var samplesSent = 0;
  var framesSent = 0;
  var framesDropped = 0;

  function connect() {
    if (stopped) return;
    try {
      ws = new WebSocket(INGEST_URL);
    } catch (e) {
      log("websocket construct failed", e);
      scheduleReconnect();
      return;
    }
    ws.binaryType = "arraybuffer";

    ws.onopen = function () {
      wsReady = true;
      reconnectDelay = RECONNECT_MS;
      log("ingest connected", INGEST_URL);
      sendJSON({ type: "hello", sampleRate: TARGET_RATE, url: location.href });
      // Re-announce the speaker so a reconnect does not lose attribution.
      if (lastSpeaker) {
        sendJSON({ type: "speaker", name: lastSpeaker, speaking: true, t: elapsed() });
      }
    };
    ws.onclose = function () {
      wsReady = false;
      log("ingest closed");
      scheduleReconnect();
    };
    ws.onerror = function (e) {
      // onclose always follows onerror; the reconnect is scheduled there.
      log("ingest error", e);
    };
  }

  function scheduleReconnect() {
    if (stopped || reconnectTimer) return;
    reconnectTimer = setTimeout(function () {
      reconnectTimer = null;
      connect();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_MS);
  }

  function sendJSON(obj) {
    if (!wsReady || !ws || ws.readyState !== 1) return;
    try {
      ws.send(JSON.stringify(obj));
    } catch (e) {
      log("json send failed", e);
    }
  }

  function sendFrame(float32) {
    if (!wsReady || !ws || ws.readyState !== 1 || ws.bufferedAmount > MAX_BUFFERED_BYTES) {
      framesDropped++;
      return;
    }
    var buf = new ArrayBuffer(8 + float32.length * 4);
    // offsetSec is derived from samples actually sent, so it stays monotonic
    // and gap-free even when frames are dropped above.
    new DataView(buf).setFloat64(0, samplesSent / TARGET_RATE, true);
    new Float32Array(buf, 8).set(float32);
    try {
      ws.send(buf);
      samplesSent += float32.length;
      framesSent++;
    } catch (e) {
      framesDropped++;
      log("frame send failed", e);
    }
  }

  // ------------------------------------------------------------ audio graph --
  var ctx = null;
  var mixBus = null; // GainNode every tapped source feeds
  var destination = null; // the single MediaStreamDestination
  var pump = null; // AudioWorkletNode or ScriptProcessorNode
  var attached = new WeakSet();
  var attachedCount = 0;
  var startedAt = Date.now();

  function elapsed() {
    return (Date.now() - startedAt) / 1000;
  }

  function makeContext() {
    var Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) throw new Error("no AudioContext in this page");
    // Asking for a 16 kHz context makes Chromium resample every source for us,
    // so the pump emits exactly the rate Rust expects. Older builds reject the
    // option; fall back to the hardware rate and resample in JS.
    try {
      return new Ctor({ sampleRate: TARGET_RATE, latencyHint: "playback" });
    } catch (e) {
      log("16k context rejected, falling back to default rate", e);
      return new Ctor();
    }
  }

  var WORKLET_SRC = [
    "class MeetbotTap extends AudioWorkletProcessor {",
    "  constructor(options) {",
    "    super();",
    "    const opts = (options && options.processorOptions) || {};",
    "    this.frameSamples = opts.frameSamples || 1024;",
    "    this.buf = new Float32Array(this.frameSamples);",
    "    this.n = 0;",
    "    this.closed = false;",
    "    this.port.onmessage = (e) => { if (e.data === 'stop') this.closed = true; };",
    "  }",
    "  process(inputs) {",
    "    if (this.closed) return false;",
    "    const input = inputs[0];",
    "    if (!input || input.length === 0) return true;",
    "    const chans = input.length;",
    "    const frames = input[0].length;",
    "    for (let i = 0; i < frames; i++) {",
    "      let sum = 0;",
    "      for (let c = 0; c < chans; c++) sum += input[c][i];",
    "      this.buf[this.n++] = sum / chans;",
    "      if (this.n === this.frameSamples) {",
    "        this.port.postMessage(this.buf.slice(0));",
    "        this.n = 0;",
    "      }",
    "    }",
    "    return true;",
    "  }",
    "}",
    "registerProcessor('meetbot-tap', MeetbotTap);",
  ].join("\n");

  // Linear resampler, used only when the AudioContext refused 16 kHz.
  function toTargetRate(samples, fromRate) {
    if (fromRate === TARGET_RATE) return samples;
    var ratio = TARGET_RATE / fromRate;
    var outLen = Math.floor(samples.length * ratio);
    var out = new Float32Array(outLen);
    for (var i = 0; i < outLen; i++) {
      var src = i / ratio;
      var i0 = Math.floor(src);
      var i1 = Math.min(i0 + 1, samples.length - 1);
      var frac = src - i0;
      out[i] = samples[i0] * (1 - frac) + samples[i1] * frac;
    }
    return out;
  }

  // Resampling breaks the pump's frame alignment, so re-chunk to a stable
  // FRAME_SAMPLES before sending.
  var outBuf = new Float32Array(FRAME_SAMPLES);
  var outN = 0;

  function emit(samples) {
    for (var i = 0; i < samples.length; i++) {
      outBuf[outN++] = samples[i];
      if (outN === FRAME_SAMPLES) {
        sendFrame(outBuf);
        outN = 0;
      }
    }
  }

  function startPump() {
    var rate = ctx.sampleRate;
    if (ctx.audioWorklet && typeof AudioWorkletNode === "function") {
      var url = URL.createObjectURL(
        new Blob([WORKLET_SRC], { type: "application/javascript" })
      );
      return ctx.audioWorklet
        .addModule(url)
        .then(function () {
          URL.revokeObjectURL(url);
          pump = new AudioWorkletNode(ctx, "meetbot-tap", {
            numberOfInputs: 1,
            numberOfOutputs: 1,
            outputChannelCount: [1],
            processorOptions: { frameSamples: FRAME_SAMPLES },
          });
          pump.port.onmessage = function (e) {
            emit(toTargetRate(e.data, rate));
          };
          wirePump();
          log("worklet pump running at", rate);
        })
        .catch(function (e) {
          log("AudioWorklet unavailable, using ScriptProcessor", e);
          startScriptProcessor(rate);
        });
    }
    startScriptProcessor(rate);
    return Promise.resolve();
  }

  function startScriptProcessor(rate) {
    // Deprecated, but the only fallback that works everywhere. It runs on the
    // main thread, so keep the buffer large to avoid glitching.
    pump = ctx.createScriptProcessor(4096, 1, 1);
    pump.onaudioprocess = function (ev) {
      emit(toTargetRate(new Float32Array(ev.inputBuffer.getChannelData(0)), rate));
    };
    wirePump();
    log("scriptprocessor pump running at", rate);
  }

  function wirePump() {
    mixBus.connect(pump);
    // The graph must reach ctx.destination for the pump to be pulled, but the
    // bot must never play the meeting back out: terminate through a muted gain.
    var mute = ctx.createGain();
    mute.gain.value = 0;
    pump.connect(mute);
    mute.connect(ctx.destination);
  }

  // ------------------------------------------------------- element tapping --
  function tapElement(el) {
    if (!el || attached.has(el)) return false;

    var source = null;
    try {
      if (el.srcObject && typeof el.srcObject.getAudioTracks === "function") {
        var tracks = el.srcObject.getAudioTracks();
        // Video-only tile: no audio yet. Leave it out of `attached` so a later
        // scan retries once the audio track arrives.
        if (!tracks.length) return false;
        source = ctx.createMediaStreamSource(new MediaStream(tracks));
      } else {
        source = ctx.createMediaElementSource(el);
        // createMediaElementSource re-routes the element away from the speakers;
        // put it back so the page still behaves normally.
        source.connect(ctx.destination);
      }
    } catch (e) {
      // InvalidStateError = already tapped (by us, or by an earlier injection).
      // Mark it so we stop retrying an element that can never be tapped again.
      log("tap failed for element", e && e.name, e && e.message);
      attached.add(el);
      return false;
    }

    try {
      source.connect(mixBus);
    } catch (e) {
      log("mix connect failed", e);
      return false;
    }

    attached.add(el);
    attachedCount++;
    // Autoplay policy: a paused element produces nothing to tap.
    if (el.paused && typeof el.play === "function") {
      var p = el.play();
      if (p && typeof p.catch === "function") p.catch(function () {});
    }
    log("tapped media element", el.tagName, "total", attachedCount);
    return true;
  }

  function scanForMedia(root) {
    var scope = root && root.querySelectorAll ? root : document;
    if (scope.tagName === "AUDIO" || scope.tagName === "VIDEO") tapElement(scope);
    var els = scope.querySelectorAll("audio, video");
    for (var i = 0; i < els.length; i++) tapElement(els[i]);
  }

  // -------------------------------------------------------- speaker events --
  // Meet's DOM is obfuscated and reshuffles between releases, so speaker
  // detection is heuristic and intentionally cheap. Rust treats these events as
  // a hint: with no match the transcript renders "Unknown", never an error.
  // These three lists are substituted by meet.rs::capture_ws_script() from the
  // canonical selector table in src/meet.rs, so this file carries no markup
  // knowledge of its own and there is exactly one place to edit when Google
  // reshuffles the DOM. This file is therefore a template, not standalone JS:
  // it only parses after substitution (meet.rs has a test asserting no token
  // survives), so `node --check` on the raw asset will fail by design.
  var TILE_SELECTORS = __MEETBOT_SPEAKER_TILE_SELECTORS__;
  var SPEAKING_SELECTORS = __MEETBOT_SPEAKING_SELECTORS__;
  var NAME_SELECTORS = __MEETBOT_SPEAKER_NAME_SELECTORS__;
  var lastSpeaker = null;

  function clean(text) {
    if (!text) return null;
    var t = String(text).replace(/\s+/g, " ").trim();
    if (!t || t.length > 80) return null;
    return t;
  }

  function tileName(tile) {
    for (var n = 0; n < NAME_SELECTORS.length; n++) {
      var el;
      try {
        el = tile.querySelector(NAME_SELECTORS[n]);
      } catch (e) {
        continue; /* selector unsupported in this Chrome build */
      }
      if (el) {
        var got = clean(el.textContent);
        if (got) return got;
      }
    }
    return clean(
      tile.getAttribute &&
        (tile.getAttribute("data-participant-name") || tile.getAttribute("aria-label"))
    );
  }

  function tileIsSpeaking(tile) {
    for (var i = 0; i < SPEAKING_SELECTORS.length; i++) {
      try {
        if (tile.querySelector(SPEAKING_SELECTORS[i])) return true;
      } catch (e) {
        /* selector unsupported in this Chrome build */
      }
    }
    return false;
  }

  function pollSpeaker() {
    var tiles = [];
    for (var i = 0; i < TILE_SELECTORS.length && !tiles.length; i++) {
      try {
        tiles = document.querySelectorAll(TILE_SELECTORS[i]);
      } catch (e) {
        tiles = [];
      }
    }
    var speaking = null;
    for (var j = 0; j < tiles.length; j++) {
      if (tileIsSpeaking(tiles[j])) {
        speaking = tileName(tiles[j]);
        if (speaking) break;
      }
    }
    if (speaking === lastSpeaker) return;
    if (lastSpeaker) {
      sendJSON({ type: "speaker", name: lastSpeaker, speaking: false, t: elapsed() });
    }
    if (speaking) {
      sendJSON({ type: "speaker", name: speaking, speaking: true, t: elapsed() });
    }
    lastSpeaker = speaking;
  }

  // ------------------------------------------------------------- lifecycle --
  var observer = null;
  var scanTimer = null;
  var speakerTimer = null;

  function start() {
    ctx = makeContext();
    mixBus = ctx.createGain();
    mixBus.gain.value = 1;
    // Every participant lands on mixBus; mixBus feeds both the single
    // MediaStreamDestination (for any consumer that wants the mixed
    // MediaStream) and the pump that ships PCM to Rust.
    destination = ctx.createMediaStreamDestination();
    mixBus.connect(destination);

    connect();

    var pumping = startPump();
    if (pumping && typeof pumping.catch === "function") {
      pumping.catch(function (e) {
        log("pump start failed", e);
      });
    }

    scanForMedia(document);

    // Participants who join later render new <video>/<audio> nodes; catch both
    // fresh subtrees and srcObject swaps on existing elements.
    observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.type === "childList") {
          for (var j = 0; j < m.addedNodes.length; j++) {
            if (m.addedNodes[j].nodeType === 1) scanForMedia(m.addedNodes[j]);
          }
        } else if (m.type === "attributes" && m.target.nodeType === 1) {
          var t = m.target;
          if (t.tagName === "AUDIO" || t.tagName === "VIDEO") tapElement(t);
        }
      }
    });
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["src", "data-is-speaking"],
    });

    // Belt and braces: Meet sometimes swaps srcObject without a mutation the
    // observer sees, so re-scan on a slow timer too. tapElement is idempotent.
    scanTimer = setInterval(function () {
      scanForMedia(document);
      if (ctx.state === "suspended" && typeof ctx.resume === "function") {
        ctx.resume().catch(function () {});
      }
    }, SCAN_INTERVAL_MS);

    speakerTimer = setInterval(pollSpeaker, SPEAKER_POLL_MS);

    window.addEventListener("beforeunload", stop);
    log("capture started ->", INGEST_URL);
  }

  function stop() {
    if (stopped) return;
    stopped = true;
    if (observer) observer.disconnect();
    if (scanTimer) clearInterval(scanTimer);
    if (speakerTimer) clearInterval(speakerTimer);
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    // Flush the partial frame first, so the meeting's last word is not lost.
    if (outN > 0) {
      sendFrame(outBuf.subarray(0, outN));
      outN = 0;
    }
    try {
      if (pump && pump.port) pump.port.postMessage("stop");
      if (pump && pump.disconnect) pump.disconnect();
      if (mixBus) mixBus.disconnect();
    } catch (e) {
      /* graph already torn down */
    }
    sendJSON({ type: "bye" });
    try {
      if (ws) ws.close();
      if (ctx && ctx.close) ctx.close();
    } catch (e) {
      /* already closed */
    }
    log("capture stopped");
  }

  window.__meetbotWsCapture = {
    running: true,
    url: INGEST_URL,
    stop: stop,
    rescan: function () {
      scanForMedia(document);
      return attachedCount;
    },
    stats: function () {
      return {
        url: INGEST_URL,
        connected: wsReady,
        attachedElements: attachedCount,
        framesSent: framesSent,
        framesDropped: framesDropped,
        secondsSent: samplesSent / TARGET_RATE,
        contextRate: ctx ? ctx.sampleRate : null,
        contextState: ctx ? ctx.state : null,
        // See capture.js: Rust gates on this advancing, not on a fixed sleep.
        ctxTime: ctx ? ctx.currentTime : null,
        speaker: lastSpeaker,
      };
    },
  };

  try {
    start();
  } catch (e) {
    window.__meetbotWsCapture.running = false;
    window.__meetbotWsCapture.error = String((e && e.message) || e);
    console.error("[meetbot] capture failed to start", e);
  }

  return window.__meetbotWsCapture.stats();
})();
