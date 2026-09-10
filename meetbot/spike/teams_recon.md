# Teams anonymous-join RECON

**Date:** 2026-07-19 (WIB). **Method:** own headless Chromium (Playwright build
`chromium-1228`) on debug ports 9431/9441/9442/9443. Port 9222
(`tln-browser.service`) was never touched. No vexa container was touched.

Drivers used (all in `<meetbot>/spike/`):

| Script | Purpose |
| :-- | :-- |
| `teams_recon.mjs` | navigate + dump redirect chain + full DOM harvest |
| `teams_flow.mjs` | navigate → fill name → click Join → snapshot every 5 s |
| `teams_probe.mjs` | **new this pass** — narrow A/B probes (UA mode, name gating) |

Raw evidence in `<meetbot>/spike/teams_recon/`
(`*.json` snapshots, `*.html` full DOM, `*.png` screenshots).

> **Read the honesty section (§8) before implementing.** The pre-join and
> rejection surfaces are fully verified. Everything about the lobby, admission
> and host-denial is **inferred** — there was no real meeting to join.

---

## 1. What meetbot actually receives

From `<second-brain>/meeting-recorder/vexa_bots.py`:

```python
TEAMS_RE    = re.compile(r"teams\.microsoft\.com/meet/(\d{10,20})")
PASSCODE_RE = re.compile(r"Passcode:\s*([A-Za-z0-9]+)")
```

- `native_meeting_id` — **digits only, 10–20 of them**. Scraped from the
  calendar `hangoutLink` + `description`. `parse_meet()` (line 268) re-derives
  it with `re.search(r"(\d{10,20})", s)` and returns platform `"teams"`.
- `passcode` — optional, `[A-Za-z0-9]+`, scraped from the literal text
  `Passcode: <value>` in the calendar description. Passed to `POST /bots` as
  the `passcode` field.

So meetbot's Teams join path gets exactly: a numeric meeting code, and
optionally an alphanumeric passcode. It never sees the original invite URL.

---

## 2. The redirect chain (VERIFIED)

Navigating to `https://teams.microsoft.com/meet/1234567890123`:

```
1. GET  /meet/1234567890123
        → 302 → /dl/launcher/launcher.html?url=%2F_%23%2Fmeet%2F1234567890123%3Fanon%3Dtrue
                                          &type=meet&directDl=true&msLaunch=true&enableMobilePage=true
2. launcher.html (200) runs JS, silently probes MSAL:
        GET login.microsoftonline.com/common/oauth2/v2.0/authorize?...&prompt=none
        → 302 → /v2/authv2                (anonymous: no token, silent failure is EXPECTED)
3. → /v2/?meetingjoin=true               (SPA shell, tids: pre-core-title-bar*)
4. → /meet/1234567890123?anon=true&launchAgent=join_launcher_web&lightExperience=true&correlationId=<uuid>
        → 302 → /dl/launcher/launcher.html?... (second bounce)
5. → FINAL: /light-meetings/launch?anon=true&launchAgent=join_launcher_web
            &lightExperience=true&correlationId=<uuid>&agent=web
            &coords=<BASE64>&deeplinkId=<uuid>
```

Five document navigations, two of them full HTTP 302s. Settles in **~10–15 s**.
The `prompt=none` MSAL bounce failing is normal for anonymous and is not an error.

### 2.1 The `coords` parameter — this is what broke the current code

`coords` is **URL-encoded base64 of a JSON object**. Decoded:

```json
// no passcode
{ "meetingUrl": "https://teams.microsoft.com/meet/1234567890123?anon=true&launchAgent=join_launcher_web&lightExperience=true&correlationId=74ccaec3-...&anon=true",
  "meetingCode": "1234567890123" }

// with ?p=AbCd1234EfGh on the original URL
{ "meetingUrl": "https://teams.microsoft.com/meet/1234567890123?p=AbCd1234EfGh&anon=true&...",
  "meetingCode": "1234567890123",
  "passcode":    "AbCd1234EfGh" }
```

**Implication for meetbot.** The existing "is the meeting code a substring of
the URL?" check fails because the code is base64-wrapped. The fix is not to drop
the check — it is to decode it:

```
url_contains_code(url, code) :=
      url.contains(code)                                   // /meet/<code> stage
   || base64_decode(query_param(url, "coords")).contains(code)   // light-meetings stage
```

Both `meetingUrl` and `meetingCode` inside the decoded JSON carry the code, so a
plain substring test on the decoded blob is sufficient and needs no JSON parser.

### 2.2 Passing the passcode (VERIFIED)

Appending `?p=<passcode>` to the `/meet/<id>` URL propagates all the way
through: it lands in `coords.passcode` **and** pre-fills the passcode field on
the retry screen (verified: `meeting-passcode-input` had `value="AbCd1234EfGh"`).

**Recommendation: supply the passcode as `?p=` on the initial navigation** rather
than typing it into a field. It is carried by the platform through the whole
redirect chain, so no DOM interaction is needed in the happy path.

---

## 3. There is NO "Continue on this browser" page (VERIFIED, contradicts the brief)

The recon brief assumed a launcher choice between "Continue on this browser" and
"Open the Teams app". **That surface does not appear.** Grepping every captured
HTML for `continue on this browser`, `join on the web instead`, `use the web
app`, `joinOnWeb`, `continueOnBrowser` returns **zero hits**.

`launcher.html` auto-forwards to the web client with no user interaction. The
only `data-tid`s it ever exposes are window-chrome (`pre-core-title-bar`,
`…-close-button`, `…-maximize-button`, `…-minimize-button`).

**Do not implement a click-through for it.** If Microsoft reintroduces it, the
symptom will be the flow stalling on `/dl/launcher/launcher.html` instead of
reaching `/light-meetings/launch`.

---

## 4. The pre-join surface (VERIFIED)

Final URL `/light-meetings/launch?…`, `document.title` =
`"Microsoft Teams meeting | Microsoft Teams"`.

**No iframes.** `iframeSrcs: []` — everything is in the top-level document.
(Contrast with older Teams builds that used a nested calling frame. Confirmed
across all five captures.)

Full visible `data-tid` set:

```
auth-sign-in-link                      prejoin-cancel-button
button-custom-video-backgrounds        prejoin-display-name-input
calling-prejoin-render-content-container prejoin-header-content
calling-prejoin-screen                 prejoin-join-button
calling-prejoin-v2-computer-audio-renderer-test  prejoin-meeting-details-content
calling-prejoin-v2-no-audio-renderer-test        prejoin-v2-video-actions
calling-prejoin-v2-phone-audio-renderer-test     prejoin-v2-video-preview
calling-slot-background                prejoin-v2-video-preview-container
meeting-branding-v0-provider           selected-microphone-display
meeting-branding-v9-provider           selected-speaker-display
meeting-header-title                   speaker-toggle
prejoin-audio-common-header-computer-audio       toggle-mute
prejoin-audio-common-header-computer-no-audio    toggle-video
prejoin-audio-common-header-phone-audio          video-flyout-open-button
```

Key elements, real DOM:

```html
<!-- display name -->
<input type="text" data-tid="prejoin-display-name-input"
       placeholder="Type your name"
       class="fui-Input__input r12stul0 …">

<!-- join -->
<button type="button" id="prejoin-join-button" data-tid="prejoin-join-button"
        aria-label="Join now">Join now</button>

<!-- meeting title (generic for a non-existent meeting) -->
<span dir="auto" aria-hidden="true" data-tid="meeting-header-title"
      title="Microsoft Teams meeting">Microsoft Teams meeting</span>

<!-- mic / camera -->
<input type="checkbox" role="switch" data-tid="toggle-mute"  id="switch-rn">
<input type="checkbox" role="switch" data-tid="toggle-video" id="switch-rq" disabled>
```

Visible body text on the pre-join screen:

```
Microsoft Teams meeting
Your camera is turned off
Background filters
Computer microphone and speaker controls
Computer audio / Phone audio / No audio / Don't use audio
Cancel
Join now
Sign in
Need help?
```

### 4.1 Behavioural facts the implementer needs

| Fact | Evidence |
| :-- | :-- |
| **The pre-join screen renders for ANY meeting id.** A 2-digit id (`/meet/99`) produces an identical pre-join screen. | `P_short_id.json` |
| **Reaching pre-join proves nothing about the meeting existing.** Validation happens *only* after clicking Join. | §5 |
| **`prejoin-join-button` is NEVER disabled** — not with an empty name, not with an invalid id. `disabled` and `aria-disabled` are both absent in every capture. | `P_ua_default.json`, `P_fillname.json` |
| ⇒ **Do not gate on the button being enabled.** Wait for it to *exist* and be visible. | — |
| **The name input is a controlled React input.** Setting `.value` directly does not stick; you must use the native setter then dispatch `input`. | `teams_probe.mjs` fill worked, value read back `"Meetbot Recorder"` |
| **`meeting-header-title` is generic** (`"Microsoft Teams meeting"`) for a non-existent meeting. Presumed to carry the real subject for a real one — **unverified**. | §8 |
| **UA spoofing is NOT required.** | §4.2 |

React-safe fill (this exact form is verified to work):

```js
const set = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, 'value').set;
set.call(input, name);
input.dispatchEvent(new Event('input',  { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

### 4.2 User-agent: spoofing is not needed (VERIFIED)

Run with Chrome's real headless UA
(`…HeadlessChrome/149.0.0.0 Safari/537.36`, no `--user-agent` flag, no
`Emulation.setUserAgentOverride`) → **identical** redirect chain, identical
final URL, identical `data-tid` set, identical pre-join screen.

Teams does not block headless on this path. Keep the code simpler and skip the
UA override; if a future block appears, the fallback is a desktop UA string
(`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36`),
which is verified to work equally.

---

## 5. Rejection surface: unknown meeting (VERIFIED)

After filling the name and clicking `prejoin-join-button` on a non-existent id,
the entire pre-join tree is **replaced** (not overlaid) within **< 5 s**, and the
state is stable through at least 30 s. URL does **not** change.

New `data-tid` set — note the pre-join tids are all gone:

```
button-container            calling-retry-screen
calling-retry-cancelbutton  calling-retry-screen-alert-container
calling-retry-rejoinbutton  meeting-code-input
meeting-branding-v0-provider  meeting-passcode-input
meeting-branding-v9-provider
```

Real DOM:

```html
<div data-tid="calling-retry-screen-alert-container" role="alert" aria-atomic="true"
     aria-labelledby="calling-retry-screen-title calling-retry-screen-description">
  <h2 id="calling-retry-screen-description">
    We couldn't find a meeting matching this ID and passcode.
  </h2>
</div>

<input type="text" id="meeting-id-input-field-id" data-tid="meeting-code-input"
       aria-label="Meeting ID" placeholder="Type a meeting ID"
       required minlength="2" maxlength="255"
       value="1234567890123">            <!-- PREFILLED with the code -->

<input type="text" data-tid="meeting-passcode-input"
       aria-label="Meeting Passcode" placeholder="Type a meeting passcode"
       minlength="1" maxlength="255"
       value="AbCd1234EfGh">              <!-- PREFILLED from ?p= -->

<button data-tid="calling-retry-rejoinbutton" disabled>Rejoin call</button>
<button data-tid="calling-retry-cancelbutton">Dismiss</button>
```

Visible body text, verbatim:

```
We couldn't find a meeting matching this ID and passcode.
Rejoin call
Dismiss
```

**This is the passcode-entry surface.** There is no separate "this meeting
requires a passcode" prompt on the anonymous path — a missing or wrong passcode
lands here, on the same retry screen, with the same alert text. Teams does not
distinguish "no such meeting" from "wrong passcode" in the UI (almost certainly
deliberate, to prevent meeting-id enumeration).

**Implication:** meetbot cannot tell `bad id` from `bad passcode` from
`meeting already ended`. All three are the same DOM. Per SPEC §0.1 all of them
are a **non-admission**, so the correct terminal state is
`status = "completed"`, `segments = []` → the client classifies it
`skipped_not_admitted`. That is the right outcome and needs no disambiguation.

`calling-retry-rejoinbutton` is `disabled` even when both fields are prefilled,
so **do not attempt an automated retry through this screen.** Treat
`calling-retry-screen` as terminal.

---

## 6. Proposed selector table

Mirrors the `meet.rs` discipline: candidate lists, first match wins, new
variants at the front, old ones kept. Anchor order below is deliberate —
`data-tid` first (see §7), `aria-label` second, English text last.

```rust
// ---------------------------------------------------------------------------
// ========================= TEAMS SELECTOR TABLE ============================
// ---------------------------------------------------------------------------
//
//  *** THE ONLY PLACE IN THE CODEBASE THAT KNOWS MICROSOFT TEAMS' DOM. ***
//
//  Anchor rules (same as Meet, one addition):
//    * PREFER `data-tid`. Teams ships it as a deliberate test hook; it is
//      stable across the Fluent-UI class churn (`fui-Input__input r12stul0 …`
//      rotates per release and is worthless). See spike/teams_recon.md §7 for
//      the evidence behind this preference — it is a strong empirical
//      correlation, not a Microsoft guarantee.
//    * Then `aria-label`, then visible ENGLISH text.
//    * Teams has NO `?hl=en` equivalent. UI language follows Accept-Language,
//      so the browser MUST be launched with `--lang=en-US` AND
//      `Network.setExtraHTTPHeaders{Accept-Language: en-US,en}` for the text
//      fallbacks below to hold.
// ---------------------------------------------------------------------------
pub mod selectors {
    /// **Pre-join.** Guest display-name field. Controlled React input —
    /// must be filled via the native value setter + `input` event.
    pub const NAME_INPUT: &[&str] = &[
        "input[data-tid='prejoin-display-name-input']",
        "input[placeholder='Type your name']",
        "input[aria-label*='name' i][type='text']",
    ];

    /// **Pre-join.** Join button. NEVER carries `disabled` — gate on presence
    /// and visibility only, never on enabled-ness.
    pub const JOIN_BUTTON: &[&str] = &[
        "button[data-tid='prejoin-join-button']",
        "button#prejoin-join-button",
        "button[aria-label='Join now']",
    ];

    /// **Pre-join.** Root of the green room. Presence == pre-join reached.
    /// NOTE: appears for ANY meeting id, including nonexistent ones.
    pub const PREJOIN_ROOT: &[&str] = &[
        "[data-tid='calling-prejoin-screen']",
        "[data-tid='calling-prejoin-render-content-container']",
        "[data-tid='prejoin-header-content']",
    ];

    /// **Pre-join.** Meeting subject. Generic "Microsoft Teams meeting" when
    /// the meeting does not exist. UNVERIFIED against a real meeting.
    pub const MEETING_TITLE: &[&str] = &[
        "[data-tid='meeting-header-title']",
    ];

    /// **Pre-join.** Mic / camera toggles (role=switch checkboxes).
    /// Read `.checked`; click the LABEL, not the input.
    pub const MIC_TOGGLE:    &[&str] = &["input[data-tid='toggle-mute']"];
    pub const CAMERA_TOGGLE: &[&str] = &["input[data-tid='toggle-video']"];

    /// **Rejection (TERMINAL).** Unknown meeting id, wrong passcode, or ended
    /// meeting — Teams renders the same screen for all three and does not
    /// disambiguate. Replaces the pre-join tree entirely. `calling-retry-
    /// rejoinbutton` is disabled: do NOT retry through it.
    pub const RETRY_SCREEN: &[&str] = &[
        "[data-tid='calling-retry-screen']",
        "[data-tid='calling-retry-screen-alert-container']",
        "#calling-retry-screen-description",
    ];

    /// **Rejection.** Text inside RETRY_SCREEN, for logging only — never
    /// branch on it (see §5).
    pub const RETRY_SCREEN_TEXT: &[&str] = &[
        "We couldn't find a meeting matching this ID and passcode",
        "We couldn't find a meeting",
    ];

    /// **Rejection.** Prefilled echo of what Teams parsed from `coords`.
    /// Useful as a diagnostic: if `meeting-code-input.value != native_id`,
    /// the redirect chain mangled the code.
    pub const RETRY_CODE_INPUT:     &[&str] = &["input[data-tid='meeting-code-input']"];
    pub const RETRY_PASSCODE_INPUT: &[&str] = &["input[data-tid='meeting-passcode-input']"];

    // ---- BELOW THIS LINE: NOT VERIFIED. See spike/teams_recon.md §8. -------

    /// **Lobby / waiting room.** INFERRED — no real meeting was available.
    /// Text anchors are best-effort from the shipped Teams strings.
    /// MUST be re-verified against a live meeting before shipping.
    pub const LOBBY_ROOT: &[&str] = &[
        "[data-tid='calling-lobby-screen']",
        "[data-tid='lobby-screen']",
        "Someone in the meeting should let you in soon",
        "When the meeting starts, we'll let people know you're waiting",
    ];

    /// **Admitted / in-call.** INFERRED. The reliable non-DOM signal is a
    /// live inbound WebRTC audio track; prefer that over any of these.
    pub const IN_CALL_ROOT: &[&str] = &[
        "[data-tid='calling-screen']",
        "[data-tid='call-status-container']",
        "[data-tid='toggle-mute']",   // in-call mic control, distinct from pre-join
    ];

    /// **Host denied entry.** INFERRED.
    pub const DENIED_TEXT: &[&str] = &[
        "You weren't admitted to the meeting",
        "Sorry, you were denied access to the meeting",
        "someone in the meeting denied your request to join",
    ];

    /// **Call ended / removed.** INFERRED.
    pub const CALL_ENDED_TEXT: &[&str] = &[
        "The meeting has ended",
        "You've been removed from the meeting",
        "Call ended",
    ];
}
```

---

## 7. Is `data-tid` really more stable than Meet's class names?

The brief asked me to verify this rather than assume it. **Verdict: yes, but
with a caveat — and the evidence is correlational, not a guarantee.**

Supporting:
- Every functional element carries a semantic, human-readable `data-tid`
  (`prejoin-join-button`, `meeting-passcode-input`). These read as deliberate
  test hooks, not build artefacts.
- The co-located class names are unambiguously generated Fluent-UI hashes
  (`fui-Input__input r12stul0 ___etraft0 f1w2t2ij f1oo480s …`) and rotate per
  release. They are worthless as anchors — same conclusion as Meet.
- `data-tid` values were byte-identical across five captures, two different
  user-agents, three meeting ids, and both with and without a passcode.

Caveats the implementer must not gloss over:
- All captures are from a **single ~2-hour window on one day**. I have no
  longitudinal evidence. "Stable across releases" is an inference from the
  naming convention, not something I observed.
- Teams *does* version its tids (`meeting-branding-v0-provider` **and**
  `meeting-branding-v9-provider` ship side by side;
  `calling-prejoin-v2-video-preview`). So tids **do** churn — with a `-vN`
  suffix. Selector entries should therefore avoid the version segment where
  possible, and the candidate-list convention from `meet.rs` matters just as
  much here.
- One tid varied across runs for non-UI reasons: `get-user-media-wrapper`
  appears only when real media devices are enumerated (present under RDP
  audio, absent under `--use-fake-device-for-media-stream`). Do not treat its
  absence as a state signal.

Net: anchor on `data-tid` first, keep `aria-label` and English text as
fallbacks, keep the candidate lists.

---

## 8. Verified vs inferred — read this before implementing

### Directly observed (high confidence)

| # | Finding |
| :-- | :-- |
| 1 | Full redirect chain `/meet/<id>` → launcher → MSAL silent probe → `/v2/` → `/light-meetings/launch` |
| 2 | `coords` = URL-encoded base64 JSON with `meetingUrl` / `meetingCode` / `passcode` |
| 3 | `?p=<passcode>` propagates into `coords.passcode` and prefills the passcode field |
| 4 | No "Continue on this browser" interstitial exists |
| 5 | No iframes — everything top-level |
| 6 | Complete pre-join `data-tid` inventory + `outerHTML` of name input, join button, title, toggles |
| 7 | Pre-join renders for ANY id (2-digit included); no validation before join |
| 8 | `prejoin-join-button` is never `disabled` |
| 9 | Name input is a controlled React input; native-setter fill verified working |
| 10 | UA spoofing not required — real HeadlessChrome UA reaches the same surface |
| 11 | Rejection surface: `calling-retry-screen` + `role=alert` "We couldn't find a meeting matching this ID and passcode.", stable ≥30 s, pre-join tree fully replaced |
| 12 | `meeting-code-input` prefilled with the code; `calling-retry-rejoinbutton` disabled |
| 13 | Bad id, bad passcode and (presumably) ended meeting are indistinguishable in the DOM |

### NOT observed — inferred, guessed, or unknown (treat as TODO)

| # | Gap | Risk |
| :-- | :-- | :-- |
| A | **Lobby / waiting-room DOM.** `LOBBY_ROOT` selectors are guesses. | **HIGH** — admission detection is the core of the join path |
| B | **Successful admission / in-call DOM.** `IN_CALL_ROOT` is a guess. | **HIGH** |
| C | **Host-denial surface.** `DENIED_TEXT` is a guess. | MEDIUM — SPEC §0.1 maps denial and timeout to the same terminal state, so getting this wrong is not fatal |
| D | **Call-ended / removed-by-host surface.** Guess. | MEDIUM — affects `stopped` + partial transcript |
| E | **Whether a real meeting shows a distinct "enter passcode" prompt** before join, rather than only the post-join retry screen. | MEDIUM — if it exists, `?p=` may already satisfy it |
| F | **Whether `meeting-header-title` carries the real subject.** | LOW — cosmetic |
| G | **Audio capture from a real Teams call.** Entirely untested. The external whisper ASR is down, and there was no meeting. | **HIGH** — separate spike |
| H | **Longitudinal `data-tid` stability.** One-day sample only. | MEDIUM |

### Recommended next step

Gaps A, B and G cannot be closed by recon; they need **one real Teams meeting**
that the operator hosts, with the bot joining as a guest while the flow driver
snapshots every 3 s. `teams_flow.mjs` already does exactly this — point it at a
live meeting URL and it will produce the lobby/admitted/ended DOM in one run.
Until then, `LOBBY_ROOT`, `IN_CALL_ROOT`, `DENIED_TEXT` and `CALL_ENDED_TEXT`
should be treated as unverified scaffolding, not as working selectors.

---

## 9. Suggested join algorithm (from verified behaviour only)

```
1. navigate https://teams.microsoft.com/meet/<native_id>[?p=<passcode>]
   browser flags: --lang=en-US, and grant audioCapture/videoCapture for
   https://teams.microsoft.com so no permission interstitial appears.
2. wait (≤30 s) for URL to reach /light-meetings/launch
   AND for any PREJOIN_ROOT selector to be visible.
3. verify the code survived the chain:
   url.contains(code) || base64_decode(query("coords")).contains(code)
   → on failure: Failed (this is the check that is currently breaking).
4. fill NAME_INPUT via native setter + input/change events.
5. optionally set mic/camera off via MIC_TOGGLE / CAMERA_TOGGLE labels.
6. click JOIN_BUTTON (presence only — never wait for enabled).
7. poll every ~1 s up to admission_timeout_min:
     RETRY_SCREEN visible      → TERMINAL. Admission::Denied.
                                 (SPEC §0.1 → status "completed", segments [])
     LOBBY_ROOT visible        → still knocking, keep polling      [UNVERIFIED]
     IN_CALL_ROOT / inbound
       WebRTC audio track      → Admission::Admitted               [UNVERIFIED]
     timeout                   → Admission::TimedOut
                                 (SPEC §0.1 → status "completed", segments [])
```

Step 7's admitted/lobby branches rest on unverified selectors. Prefer the
**inbound WebRTC audio track** as the admission signal — it is a protocol-level
fact rather than a DOM guess, and it degrades gracefully when Microsoft
reshuffles markup.
