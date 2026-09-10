# meetbot

A single Rust binary that sends a bot into a Google Meet call, captures the
room audio, transcribes it with the local whisper server, and serves the result
over the same HTTP API the Python client already speaks.

`SPEC.md` is the frozen contract. Where this README and the spec disagree, the
spec wins — except for the three integration corrections recorded in
[Deviations from SPEC](#deviations-from-spec).

---

## What this replaces

It is a drop-in replacement for the **self-hosted Vexa Lite stack** — the
`vexa-lite`, `vexa-postgres` and `vexa-minio` Docker containers that currently
serve `http://localhost:8056`.

| | vexa-lite (old) | meetbot (new) |
| :-- | :-- | :-- |
| Runtime | 3 Docker containers | 1 static binary |
| Port | 8056 | 8060 |
| Store | Postgres + MinIO | one SQLite file |
| Transcription | its own worker | the same whisper server on the Windows host |
| API key | `meeting-recorder/vexa_token.env` | **the same file, unchanged** |
| Google Meet | yes | yes |
| Microsoft Teams | yes | yes — anonymous join, **pre-join verified, in-call unverified** |

The client, `meeting-recorder/vexa_bots.py`, keeps its wire behaviour unchanged:
it reads its base URL from `VEXA_API_BASE` and its key from that token file, so
cutting over is setting two environment variables and rolling back is unsetting
them. It did need one additive edit, `MEETBOT=1` mode, so that the vexa-only
container maintenance it performs (`ensure_env_url()`, the `docker start` /
`docker restart` branches) is skipped when it is talking to meetbot. With both
variables unset the client behaves exactly as it always has.

**The vexa containers are deliberately left running, and meetbot never touches
them.** They are the rollback path. Do not stop them, and do not treat vexa as
decommissioned.

Start at [Operator runbook](#operator-runbook) for the cutover, the checks, the
rollback, and what is still unverified about Teams.

---

## Building and running

Cargo is not on the default PATH in this WSL environment:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
cd <meetbot>
cargo build --release
```

Run it in the foreground:

```bash
./target/release/meetbot serve --config config.toml
```

Check it is alive (no key needed for `/`):

```bash
curl localhost:8060/
# {"service":"meetbot","status":"ok","version":"0.1.0"}
```

`/health` additionally reports whether the whisper server and the Chromium
binary are actually reachable, which is the first thing to check when a
recording comes back empty:

```bash
curl -H "X-API-Key: $(grep VEXA_API_KEY \
  <second-brain>/meeting-recorder/vexa_token.env \
  | cut -d= -f2)" localhost:8060/health
```

### Configuration

Everything lives in `config.toml`, which is commented. The fields worth knowing:

- `whisper_host` — leave commented out. The WSL gateway IP moves on every
  reboot, so meetbot re-resolves it from `ip route show default` per call.
- `cdp_port` — leave commented out to launch a fresh browser per session.
  Setting it to `9222` attaches to the systemd `tln-browser.service` instead.
  **Attach only; never stop or restart that unit.**
- `capture_transport` — `"cdp"` (default) or `"websocket"`. See
  [Audio capture](#audio-capture).
- `stale_after_hours` — vestigial, gates nothing. See the deviations section.
- `require_whisper_for_bots` — `true` by default (and when omitted). `POST
  /bots` returns 503 when transcription is requested and whisper is down, so a
  dead whisper raises a `send_failed` + fail heartbeat instead of producing a
  silently empty transcript. Set it to `false` to accept the bot anyway, which
  is what vexa did. See the deviations section for the tradeoff.
- `api_key_file` — read at boot. If the file does not exist, meetbot mints a
  random key, writes it there with mode `0600`, and logs it once at WARN. An
  existing key is never rewritten.

### As a systemd user service

`meetbot.service` ships in this directory but is **not installed**. To install:

```bash
cp <meetbot>/meetbot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now meetbot.service
journalctl --user -u meetbot -f
```

`TimeoutStopSec=120` is deliberate and must stay above the 90-second shutdown
grace in `src/main.rs`. On SIGTERM meetbot finalizes in-flight sessions —
draining audio, flushing the segmenter, awaiting whisper, inserting segments,
and only then writing the terminal status. If systemd SIGKILLs first, the row
is still closed out as `failed`, but a partial transcript is lost.

---

## Operator runbook

Written to be followed at 22:00 with no thinking. Copy the commands verbatim.

### Read this first: what meetbot cannot do yet

> **Teams is supported, but only its first half is verified.** meetbot drives the
> Teams anonymous-join flow (`src/teams.rs`, SPEC §1.3.1): the five-hop redirect
> chain, the base64 `coords` check, the display name, the `?p=` passcode and the
> join click were all verified against live captures. What was **never observed
> live** is everything after the join click — the lobby, the in-call DOM, host
> denial and call-ended copy. There was no real Teams meeting available during
> recon, so those selector groups are explicit guesses, fenced off below a
> `NOT VERIFIED` divider in `teams::selectors`.
>
> What that means in practice. If the inferred selectors are wrong, the bot waits
> out `admission_timeout_min` and finishes `completed` with zero segments, filed
> as `skipped_not_admitted` — the same outcome as genuinely not being let in.
> Wrong selectors degrade to "not admitted", never to a false transcript. But it
> is still a silent-ish failure, so:
>
> * check `journalctl -u meetbot` after the first real Teams call. A failed Teams
>   join logs the stage, the selector groups that missed, and whether each was
>   ever observed live — `[VERIFIED]` means Microsoft changed their markup,
>   `[INFERRED]` means our guess was wrong from the start.
> * `meetbot doctor <teams-id> [--passcode <p>]` dry-runs the whole dance and
>   prints the same breakdown without joining anything for real.
> * audio capture from a real Teams call is untested (recon gap G).
>
> Closing the gaps needs one real Teams meeting you host, with
> `spike/teams_flow.mjs` pointed at the live URL — it snapshots every 3 s and
> captures the lobby / admitted / ended DOM in a single run. Until then, keep
> vexa as the rollback for Teams specifically.

The second limitation, stated plainly: **no bot has ever been admitted to a real
meeting through meetbot.** The join dance, the DB, the API and the crash recovery
are all verified, but live audio capture, speaker attribution and the whisper
path are not. See [Verified](#verified).

### 1. Cut over

meetbot must already be running. Start it if it is not:

```bash
systemctl --user start meetbot.service && curl -s localhost:8060/
```

Then the cutover itself, which is two environment variables:

```bash
export VEXA_API_BASE=http://localhost:8060
export MEETBOT=1
```

`VEXA_API_BASE` is what actually routes the client. `MEETBOT=1` is the explicit
mode flag: it tells `vexa_bots.py` to skip the vexa-only container maintenance in
`ensure_env_url()` and `ensure_vexa_api()`, which would otherwise rewrite
`~/tools/vexa/.env` and run `docker restart vexa-lite` on a WSL gateway-IP
change. Under meetbot both are pointless (meetbot resolves the gateway IP itself
on every whisper call) and harmful (they bounce the container that is your
rollback path).

Setting `MEETBOT=1` is belt-and-braces: the client also infers meetbot mode from
`VEXA_API_BASE` naming port 8060. Set it anyway. It is the signal that survives
someone moving the port.

To make the cutover stick for cron, edit the crontab line so it carries both
variables. **Back the crontab up first**, always:

```bash
crontab -l > ~/crontab.bak.$(date +%F-%H%M)
crontab -e
```

The line to change (it is the only `vexa_bots.py` entry):

```cron
# before
*/5 * * * * cd <second-brain> && python3 meeting-recorder/vexa_bots.py auto >> /tmp/vexa_auto.log 2>&1
# after
*/5 * * * * cd <second-brain> && VEXA_API_BASE=http://localhost:8060 MEETBOT=1 python3 meeting-recorder/vexa_bots.py auto >> /tmp/vexa_auto.log 2>&1
```

The API key does not change. meetbot reads the same `vexa_token.env`.

### 2. Confirm meetbot is actually handling meetings

Run these in order. Each one answers a different question.

**Is meetbot up and are its dependencies healthy?**

```bash
KEY=$(grep VEXA_API_KEY <second-brain>/meeting-recorder/vexa_token.env | cut -d= -f2)
curl -s localhost:8060/
curl -s -H "X-API-Key: $KEY" localhost:8060/health
```

Want `"status":"ok"`, `whisper.reachable: true`, `chromium.present: true`. A
`degraded` here means every recording will come back empty.

**Is the client pointed at meetbot, and is the gating live?**

```bash
cd <second-brain>
VEXA_API_BASE=http://localhost:8060 MEETBOT=1 \
  python3 meeting-recorder/vexa_bots.py selftest
```

`selftest OK` means the mode detection and the vexa-container gating are intact.
It sends no bots and touches no network. Run it after any edit to the client.

**Is the next cron tick going to do the right thing?**

```bash
VEXA_API_BASE=http://localhost:8060 MEETBOT=1 \
  python3 meeting-recorder/vexa_bots.py auto --dry-run
```

Prints every calendar meeting it can see with `JOIN NOW` or `in ±N min`, and
sends nothing. Any line whose id starts with `teams/` is a meeting meetbot will
silently drop. See the limitation above.

**Is a bot in a call right now?**

```bash
curl -s -H "X-API-Key: $KEY" localhost:8060/bots/status
```

`sessions[].phase` walks `joining → waiting_room → in_call → finalizing`.
`segment_count` climbing while `phase` is `in_call` is the one observation that
proves audio is genuinely flowing. If it stays at 0 for several minutes of a
meeting with people talking, stop and roll back.

**Did the last cron tick work?**

```bash
tail -40 /tmp/vexa_auto.log
journalctl --user -u meetbot -n 60 --no-pager
```

**Did the meeting produce a real transcript?**

```bash
python3 meeting-recorder/vexa_bots.py status | tail -10
```

`drafted` is the good outcome. `skipped_not_admitted` on a meeting you know had
people in it means the bot never got in: on Google Meet suspect the selectors and
run `doctor`, on Teams it is the known limitation and expected.

### 3. Roll back

One command, and it is safe at any time. vexa never stopped running.

```bash
unset VEXA_API_BASE MEETBOT
```

For cron, restore the backup you took in step 1:

```bash
crontab ~/crontab.bak.<the one you made>
crontab -l | grep vexa_bots      # verify the line is back to plain `python3 ...`
```

Confirm vexa took over again:

```bash
docker ps --filter name=vexa      # vexa-lite, vexa-postgres, vexa-minio all Up
curl -s localhost:8056/
python3 meeting-recorder/vexa_bots.py auto --dry-run
```

Optionally stop meetbot; it is not required, the two listen on different ports
and meetbot idle costs nothing:

```bash
systemctl --user stop meetbot.service
```

Nothing else needs undoing. meetbot never writes to vexa's Postgres or MinIO.
The one thing rollback does **not** do is migrate data: meetings recorded through
meetbot stay in meetbot's SQLite file. **Pull anything you still need before you
roll back**, or point the variable back at 8060 for the length of the pull.

### 4. vexa stays running

The `vexa-lite`, `vexa-postgres` and `vexa-minio` containers stay up and
untouched. They are the rollback path, and rollback is only credible if they were
never stopped, never restarted, and never had their config rewritten underneath
them. That is precisely why `MEETBOT=1` gates the two maintenance paths in the
client.

Do not `docker stop`, `docker rm`, or edit `~/tools/vexa/.env` as part of any
meetbot work. Decommissioning vexa is a **separate, deliberate decision** to be
taken only after meetbot has recorded real meetings cleanly for a sustained
period **and** Teams support exists. Until both are true, vexa is not redundant
infrastructure, it is the only thing recording Teams.

### Setup / token sanity check

Optional, and only needed if `vexa_token.env` is missing or you want to exercise
the admin-compat endpoints:

```bash
VEXA_API_BASE=http://localhost:8060 MEETBOT=1 python3 vexa_bots.py setup
```

meetbot echoes the API key it is already configured with, so the rewritten file
stays valid for vexa too. Only `VEXA_USER_ID` changes.

If `vexa_token.env` has been **lost entirely**, do not run `setup` first — it
cannot help, because `POST /admin/users/{uid}/tokens` only echoes the key
meetbot read out of that same file. Just start meetbot: it mints a key, writes
`VEXA_API_KEY=` into `api_key_file` at mode `0600`, and logs it once:

```bash
journalctl --user -u meetbot | grep "minted a new one"
```

Then run `setup` if you also want `VEXA_USER_ID` refreshed.

> **Gotcha, hit during integration.** `vexa_bots.py` reads the admin key from
> `ADMIN_TOKEN=` in `~/tools/vexa/.env`, a *file*, not an environment variable.
> `admin_token` in `config.toml` must therefore match that value exactly, or
> `setup` fails with `401 invalid api key`. It is set correctly today; if you
> ever rotate vexa's `.env`, rotate `config.toml` with it.

---

## Audio capture

Getting audio out of a headless browser is the fragile part, so two details are
load-bearing and neither is cosmetic:

1. **`--autoplay-policy=no-user-gesture-required` is mandatory.** Without it the
   page's `AudioContext` stays `suspended` forever and every recording is
   silent. `--headless=new` is required too; the legacy `--headless` renderer
   has no WebAudio at all. xvfb is *not* needed and buys nothing.
2. **The user agent must not say `HeadlessChrome`.** Meet serves a degraded,
   audio-less page to headless user agents, so meetbot presents a plain desktop
   Chrome UA.

After injecting the tap, meetbot waits until the page's
`AudioContext.currentTime` is observed to **advance** across two probes, rather
than sleeping a fixed interval. A context can report `state === "running"` in
headless while the render graph is never pumped; `currentTime` is the only
witness that separates a live graph from a stalled one. It advances whenever the
graph runs, so silence in the room does not trip the gate — it tests the tap,
never speech. If this check fails, suspect the autoplay flag first.

Two transports carry the PCM back to Rust, selected by `capture_transport`:

- **`cdp`** (default, the SPEC §7 path) — base64 frames over
  `Runtime.addBinding`. This is what the acceptance tests exercise.
- **`websocket`** — `assets/capture_ws.js` streams to a loopback ingest socket.
  A fallback for if audio starts backing up behind DOM traffic on the shared CDP
  session. It is the less exercised path; leave it alone unless the CDP tap
  misbehaves on a real call.

Both taps are **templates, not standalone JS**: the speaker-attribution
selectors are substituted from the one canonical table in `src/meet.rs`, so a
DOM fix is applied once and lands in both. Consequently `node --check` on the
raw asset files fails by design.

---

## Selector maintenance (`doctor`)

Google and Microsoft both reshuffle their DOM without warning. When that happens
the failure is quiet and expensive: the bot waits out `admission_timeout_min` and
every meeting is filed as `skipped_not_admitted` with an empty transcript.

`doctor` is the tool for that day. It dry-runs the whole join dance against a
real meeting id, prints the stage that broke, and **never touches the database or
records anything**:

```bash
# Google Meet
./target/release/meetbot doctor abc-defg-hij --config config.toml

# Microsoft Teams (the platform is inferred from the id shape)
./target/release/meetbot doctor 1234567890123 --passcode AbCd1234EfGh
```

Healthy output:

```
  [ ok ] config     loaded config.toml
  [ ok ] meeting id https://meet.google.com/abc-defg-hij
  [ ok ] browser    $HOME/.cache/.../chrome
  [ ok ] whisper    http://172.25.32.1:8083/v1/audio/transcriptions
  [ ok ] launch     chromium up, CDP attached
  [ ok ] join       name filled and join clicked
  [ ok ] admission  host denied entry — the denial DOM was detected

RESULT: join dance intact — every selector matched.
```

It exits non-zero when a stage fails. Useful flags: `--headed` to watch a real
window, `--wait <sec>` to change waiting-room patience, `--platform` to force
`google_meet` / `teams` when the id shape is ambiguous, `--passcode` for a Teams
meeting that needs one.

On a Teams failure `doctor` additionally prints the five join stages with a hint
each, and a table of every Teams selector group marked `VERIFIED` or
`INFERRED (never observed live)`. Read that column before editing anything: an
INFERRED group that misses was always a guess, a VERIFIED one that misses means
Microsoft changed their markup.

**Procedure when a stage fails**

1. Run `doctor` against a meeting id you control. The first `[FAIL]` line names
   the stage, and the `error:` / `caused by:` chain under it carries the
   selector group that did not match.
2. Open `src/meet.rs` (Google Meet) or `src/teams.rs` (Microsoft Teams) and find
   the `selectors` module — every string that platform's markup is matched
   against lives there and nowhere else. The assets carry no markup knowledge of
   their own.
3. Re-run `doctor --headed` to see what the page actually renders, and add the
   new selector to the relevant list. **Add, don't replace** — the lists are
   tried in order, so keeping the old entry means the fix still works for users
   on the previous Meet rollout.
4. `cargo test` — there are tests asserting no template token survives
   substitution and that both taps carry the same selectors.
5. Re-run `doctor` until the dance is intact, then restart the service.

**Which selectors break, and how badly**

| Selector list | If it goes stale |
| :-- | :-- |
| `IN_CALL_MARKERS` | **Worst case.** The bot never notices it was admitted, waits out the timeout, and every meeting is recorded as skipped with no audio. |
| `JOIN_BUTTON_TEXTS`, `NAME_INPUT` | The bot never gets into the green room; the session fails fast and loudly. |
| `SPEAKING_INDICATORS`, `SPEAKER_NAME`, `SPEAKER_TILE` | **Degraded, never fatal.** Speaker attribution is best-effort: segments render as "Unknown" but the audio and transcript are unaffected. This is the least stable entry in the table and the most likely to drift. |
| `DENIED_TEXTS`, `CALL_ENDED_TEXTS`, `REMOVED_TEXTS` | The bot sits in a dead call until the lonely-grace or admission timeout closes it. Wasteful, not incorrect. |

---

## Semantics worth not breaking

The one thing to get right (SPEC §0.1): **a meeting the bot was never admitted
to must finish `completed` with `segments: []` and `start_time: null` — not
`failed`.** The client distinguishes "nobody let the bot in" from "the recorder
is broken" on exactly that, and files the former as `skipped_not_admitted`
without raising an alert. Marking it `failed` produces a false alarm on every
meeting the bot is not invited into.

Related: nothing may be left non-terminal across a restart. The client polls a
non-terminal row forever, so meetbot fails every live row on startup.

---

## Deviations from SPEC

Four integration decisions where the spec was wrong, ambiguous, or silent.
All are annotated at the code and in `SPEC.md`.

1. **Startup sweep is unconditional** (SPEC §2, corrected to v1.1). The spec said
   to fail non-terminal rows "older than `stale_after`" and, in the next
   sentence, to never leave a row non-terminal across a restart. Those conflict:
   a session killed ten minutes into a call is not six hours old, so an
   age-gated sweep leaves it non-terminal and the client polls it forever,
   failing acceptance test 9. The sweep now takes every non-terminal row, which
   is sound because sessions exist only in the server's memory — at startup no
   such row can still have an owner. `stale_after_hours` is kept for config
   compatibility but gates nothing. It was deliberately *not* repurposed as a
   periodic sweep, since an age-gated sweep against a running server would fail
   a legitimately long call mid-recording.

2. **Two capture transports** (SPEC §7.1, added). Two taps were written against
   the spec. Rather than delete one, both ship behind `capture_transport`, with
   the spec's CDP binding as the default and the only path the acceptance tests
   exercise. See [Audio capture](#audio-capture).

3. **Whisper request details.** The multipart filename is `chunk.wav` and the
   response format is `verbose_json`, where the spec prose says `audio.wav` and
   `json`. The frozen `Transcription` type is unchanged; the extra fields are
   exposed through additive API surface, so no sibling module is affected.

4. **The 503 on a dead whisper is a deviation from vexa, now a flag**
   (SPEC §1.3.2). Vexa accepted the bot regardless of whisper's health; meetbot
   refuses with 503. Keeping it is a real bet: the Python client probes whisper
   itself before it POSTs, so if whisper flaps in between, meetbot 503s,
   `cmd_auto` records `send_failed`, and the meeting is **missed entirely** —
   vexa would have joined and captured audio. It is still the default
   (`require_whisper_for_bots = true`) because that failure is loud: a fail
   heartbeat the same evening. The alternative degrades to `completed` with zero
   segments, which the client files as `skipped_not_admitted` with an **ok**
   heartbeat — a missing MOM nobody notices. Set the flag to `false` on a host
   where whisper flaps and joining unreliably beats not joining.

Two smaller judgement calls, both preserved as written:

- The DB schema follows SPEC §5's 17-column table, and `idx_meetings_key` is
  **non-unique** as §5 specifies. A unique index keyed on `start_time` would be
  actively wrong: §2.1 requires `start_time` to stay NULL until the bot reaches
  `InCall`, and §1.5 presupposes multiple rows per meeting key.
- An unsupported platform in a `POST /bots` body returns **400** (SPEC §1.3),
  while an unknown `{platform}` path segment returns **404** (SPEC §1). 403 is
  reserved for the concurrency ceiling.

---

## Verified

Against a live server on 8061 with real Chromium and the real whisper server:

- API acceptance tests 1–4, 9 and 10: liveness, auth (401), zombie guard (404),
  duplicate bot (409), bad platform (400), concurrency ceiling (403 with the
  exact spec string), crash recovery, and `vexa_bots.py setup`.
- Crash recovery specifically: a live `active` row, SIGKILLed and restarted,
  came back `failed` — the case the old age-gated sweep would have missed.
- **Acceptance test 5 (the critical §0.1 semantic) through the real client:**
  `vexa_bots.py pull` against a never-admitted meeting printed
  `SKIPPED: ... (not admitted / no audio)` and wrote `skipped_not_admitted` —
  no transcript file, no MOM, heartbeat `ok`.
- `DELETE /bots/...` on a registered session returned 200 `stopping` and drove
  the row terminal.
- Graceful SIGTERM finalized an in-flight session and exited cleanly, leaving no
  non-terminal rows and no orphaned Chromium.
- `doctor` completed the full join dance against **real Google Meet**, matching
  the live join, name-entry and denial selectors.
- 87 unit tests pass; `cargo build` and `cargo build --release` are warning-free.

**Not verified.** No bot has been admitted to a real meeting, so end-to-end
audio capture, speaker attribution, and the whisper transcription path are
unproven on live traffic. `IN_CALL_MARKERS` and the speaker selectors in
particular have never been matched against a real in-call DOM. Record a
throwaway meeting and confirm a non-empty transcript before pointing the cron
jobs at meetbot.
