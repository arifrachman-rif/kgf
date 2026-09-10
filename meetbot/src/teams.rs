//! Microsoft Teams anonymous-join support: the selector table, the URL/`coords`
//! parsing the redirect chain forces on us, and the diagnostic vocabulary the
//! join state machine logs with.
//!
//! Contract: `SPEC.md` §1.3.1 and §7. Sibling of [`crate::meet`], which owns the
//! browser, the audio tap and every piece of shared machinery. **This module
//! contains no browser code at all** — it is markup knowledge plus pure
//! functions, so all of it is unit-testable without a Chrome.
//!
//! # Why Teams needs its own URL logic
//!
//! `https://teams.microsoft.com/meet/<id>` does not stay put. It performs five
//! document navigations in ~10-15 s and settles on
//! `/light-meetings/launch?...&coords=<BASE64>&...`. The meeting id is **not**
//! present in plain text in that final URL: it is base64-encoded inside the
//! `coords` query parameter. A plain `url.contains(code)` therefore reads the
//! successful landing as "navigated away from the meeting", which is exactly the
//! bug that made every Teams meeting finish as a silent zero-segment skip.
//! [`url_contains_code`] is the fix.
//!
//! # Verification status
//!
//! Everything in this file is annotated **VERIFIED** or **INFERRED** against
//! `spike/teams_recon.md`. VERIFIED means it was observed in a live capture on
//! 2026-07-19. INFERRED means nobody has ever seen it — there was no real Teams
//! meeting to join, so the lobby, the in-call surface, host denial and
//! call-ended copy are all scaffolding. Treat an INFERRED selector that does not
//! match as a fact about *our guess*, not about the meeting.

// ---------------------------------------------------------------------------
// ========================= TEAMS SELECTOR TABLE ============================
// ---------------------------------------------------------------------------
//
//  *** THE ONLY PLACE IN THE CODEBASE THAT KNOWS MICROSOFT TEAMS' DOM. ***
//
//  Structured exactly like `meet::selectors`. When the bot stops joining Teams,
//  stops noticing it was admitted, or stops noticing the call ended, the fix
//  belongs HERE and nowhere else.
//
//  Rules for editing:
//    * PREFER `data-tid`. Teams ships a semantic, human-readable `data-tid` on
//      every functional element (`prejoin-join-button`, `meeting-passcode-input`)
//      and they read as deliberate test hooks. The co-located class names are
//      generated Fluent-UI hashes (`fui-Input__input r12stul0 ___etraft0 ...`)
//      that rotate per release and are worthless as anchors — the same
//      conclusion `meet.rs` reached about Meet's minified classes.
//      CAVEAT, do not gloss over it: that preference rests on a single ~2-hour
//      capture window on one day. It is a strong empirical correlation, not a
//      Microsoft guarantee. Teams *does* version its tids
//      (`meeting-branding-v0-provider` and `meeting-branding-v9-provider` ship
//      side by side; `calling-prejoin-v2-video-preview`), so avoid the `-vN`
//      segment in a selector wherever the unversioned form works.
//    * Then `aria-label`, then visible ENGLISH text.
//    * Every entry is a CANDIDATE LIST tried in order, first match wins. Add the
//      new variant at the FRONT and keep the old one.
//    * Teams has NO `?hl=en` equivalent. UI language follows `Accept-Language`,
//      so the browser must be launched with `--lang=en-US` AND sent
//      `Network.setExtraHTTPHeaders{Accept-Language: en-US,en}` or every text
//      fallback below silently stops matching. `meet.rs` does both.
//    * `get-user-media-wrapper` is present or absent depending on whether real
//      media devices are enumerated, NOT on UI state. Never use it as a signal.
//
// ---------------------------------------------------------------------------
pub mod selectors {
    // =======================================================================
    // VERIFIED — observed in a live capture (spike/teams_recon.md §4, §5).
    // =======================================================================

    /// **VERIFIED. Pre-join.** Guest display-name field.
    ///
    /// A controlled React input: assigning `.value` does not stick. It must be
    /// written through the prototype's own value setter followed by bubbling
    /// `input` + `change` events, which is what `meet::js::SET_FIELD` does.
    pub const NAME_INPUT: &[&str] = &[
        "input[data-tid='prejoin-display-name-input']",
        "input[placeholder='Type your name']",
        "input[aria-label*='name' i][type='text']",
    ];

    /// **VERIFIED. Pre-join.** The join control.
    ///
    /// LANDMINE: this button is **never** disabled — neither `disabled` nor
    /// `aria-disabled` appears in any capture, not even with an empty name
    /// field. Do NOT gate the click on enabled-ness, and do NOT treat
    /// "button became enabled" as a readiness signal; wait for it to exist and
    /// be visible, nothing more.
    pub const JOIN_BUTTON: &[&str] = &[
        "button[data-tid='prejoin-join-button']",
        "button#prejoin-join-button",
        "button[aria-label='Join now']",
    ];

    /// **VERIFIED. Pre-join.** Root of the green room.
    ///
    /// LANDMINE: this renders for **any** meeting id, including `/meet/99`.
    /// Reaching pre-join proves nothing about the meeting existing. Teams only
    /// validates after the join click.
    pub const PREJOIN_ROOT: &[&str] = &[
        "[data-tid='calling-prejoin-screen']",
        "[data-tid='calling-prejoin-render-content-container']",
        "[data-tid='prejoin-header-content']",
    ];

    /// **VERIFIED (element). Pre-join.** Meeting subject.
    ///
    /// Reads the generic `"Microsoft Teams meeting"` for a non-existent
    /// meeting; whether it carries the real subject for a real one is
    /// unverified. Diagnostic only — nothing branches on it.
    pub const MEETING_TITLE: &[&str] = &["[data-tid='meeting-header-title']"];

    /// **VERIFIED. Pre-join.** Mic toggle (`role=switch` checkbox). Click the
    /// label, never the input.
    pub const MIC_TOGGLE: &[&str] = &["input[data-tid='toggle-mute']"];

    /// **VERIFIED. Pre-join.** Camera toggle (`role=switch` checkbox).
    pub const CAMERA_TOGGLE: &[&str] = &["input[data-tid='toggle-video']"];

    /// **VERIFIED, TERMINAL. Post-join rejection.**
    ///
    /// Replaces the entire pre-join tree (it is not an overlay) within <5 s and
    /// is stable for at least 30 s. The URL does not change.
    ///
    /// CRITICAL SEMANTIC: this same screen IS the passcode-entry surface. On the
    /// anonymous path there is no separate "this meeting needs a passcode"
    /// prompt. Bad meeting id, wrong passcode and (presumably) an ended meeting
    /// are **indistinguishable** here — almost certainly deliberate, to stop
    /// meeting-id enumeration. meetbot cannot disambiguate them and per
    /// `SPEC.md` §0.1 does not need to: all three are a non-admission, so the
    /// terminal state is `completed` with zero segments, which the client files
    /// as `skipped_not_admitted`.
    ///
    /// `calling-retry-rejoinbutton` carries `disabled` **even when both fields
    /// are prefilled**, so there is no automated retry through this screen.
    /// Treat a match here as terminal.
    pub const RETRY_SCREEN: &[&str] = &[
        "[data-tid='calling-retry-screen']",
        "[data-tid='calling-retry-screen-alert-container']",
        "#calling-retry-screen-description",
    ];

    /// **VERIFIED. Rejection copy — LOGGING ONLY.**
    ///
    /// Never branch on this: [`RETRY_SCREEN`] is the signal, and the text is
    /// identical for all three rejection causes. It exists so the log line says
    /// what a human would have read on the screen.
    pub const RETRY_SCREEN_TEXT: &[&str] = &[
        "We couldn't find a meeting matching this ID and passcode",
        "We couldn't find a meeting",
    ];

    /// **VERIFIED. Rejection.** Prefilled echo of the meeting id Teams parsed
    /// out of `coords`. Pure diagnostic: when this disagrees with the
    /// `native_meeting_id` we were given, the redirect chain mangled the code
    /// and the problem is upstream of the DOM.
    pub const RETRY_CODE_INPUT: &[&str] = &["input[data-tid='meeting-code-input']"];

    /// **VERIFIED. Rejection.** Prefilled from `?p=<passcode>`. Diagnostic: it
    /// proves the passcode survived the redirect chain, which is the only way to
    /// tell "we never sent the passcode" from "the passcode was wrong".
    pub const RETRY_PASSCODE_INPUT: &[&str] = &["input[data-tid='meeting-passcode-input']"];

    // =======================================================================
    // ------------------- BELOW THIS LINE: **NOT VERIFIED** -----------------
    //
    //  Nobody has ever seen these. There was no real Teams meeting available
    //  during recon (spike/teams_recon.md §8, gaps A-D). They are scaffolding,
    //  not working code.
    //
    //  Closing them needs exactly one thing: one real Teams meeting the operator hosts,
    //  with `spike/teams_flow.mjs` pointed at the live URL. It snapshots every
    //  3 s and captures the lobby / admitted / ended DOM in a single run.
    //
    //  Until then the join path leans on signals that are NOT DOM guesses:
    //  [`RETRY_SCREEN`] (verified) for rejection, the admission timeout for
    //  everything else. Both terminate correctly under SPEC §0.1.
    // =======================================================================

    /// **INFERRED. Pre-join passcode field.**
    ///
    /// The primary passcode delivery is `?p=<passcode>` on the initial
    /// navigation, which is VERIFIED to propagate into `coords.passcode`. This
    /// list is the belt-and-braces fallback for a real meeting that turns out to
    /// show a passcode prompt before the join click (recon gap E). Filling it is
    /// harmless when it is absent.
    pub const PREJOIN_PASSCODE_INPUT: &[&str] = &[
        "input[data-tid='prejoin-passcode-input']",
        "input[data-tid='meeting-passcode-input']",
        "input[aria-label*='passcode' i]",
        "input[placeholder*='passcode' i]",
    ];

    /// **INFERRED. Lobby / waiting room, CSS anchors.**
    ///
    /// Informational only: admission is decided by [`IN_CALL_ROOT`] /
    /// [`RETRY_SCREEN`] / the timeout, never by this. If it never matches, the
    /// bot simply waits out `admission_timeout` and finishes `completed` with
    /// zero segments — the correct outcome for a bot that was not let in.
    pub const LOBBY_ROOT: &[&str] = &[
        "[data-tid='calling-lobby-screen']",
        "[data-tid='lobby-screen']",
        "[data-tid='calling-lobby-container']",
    ];

    /// **INFERRED. Lobby / waiting room, English copy.**
    pub const LOBBY_TEXTS: &[&str] = &[
        "Someone in the meeting should let you in soon",
        "When the meeting starts, we'll let people know you're waiting",
        "Waiting for someone to let you in",
    ];

    /// **INFERRED. Admitted / in call.** Drives `WaitingRoom -> InCall`, so this
    /// is the single most load-bearing unverified entry in the file.
    ///
    /// LANDMINE: `[data-tid='toggle-mute']` is deliberately **absent** here even
    /// though the in-call toolbar carries it. The pre-join screen carries the
    /// byte-identical tid (VERIFIED), so including it would make the bot report
    /// `Admitted` while it is still standing in the green room, inject the audio
    /// tap into a prejoin page, and record a call it never joined. The generic
    /// [`NOT_IN_CALL`] guard below is the second line of defence against exactly
    /// that class of mistake.
    ///
    /// The reliable non-DOM signal is a live inbound WebRTC audio track. The
    /// audio-clock gate in `meet.rs` already proves the graph is pumping before
    /// capture is declared live, which is the protocol-level half of this.
    pub const IN_CALL_ROOT: &[&str] = &[
        "[data-tid='calling-screen']",
        "[data-tid='call-status-container']",
        "[data-tid='calling-participant-stage']",
        "button[data-tid='hangup-button']",
        "button#hangup-button",
    ];

    /// **VERIFIED as a set, used as a guard.** Selectors whose presence proves
    /// the bot is *not* in the call, whatever [`IN_CALL_ROOT`] thinks.
    ///
    /// Pre-join and the retry screen are both verified surfaces, so this guard
    /// is trustworthy even though [`IN_CALL_ROOT`] is not. It converts the most
    /// likely `IN_CALL_ROOT` mistake (a tid that also exists pre-join) from
    /// "records a fake call" into "waits and times out cleanly".
    pub const NOT_IN_CALL: &[&str] = &[
        "[data-tid='calling-prejoin-screen']",
        "[data-tid='calling-prejoin-render-content-container']",
        "[data-tid='calling-retry-screen']",
    ];

    /// **INFERRED. Host denied entry.** Maps to `Admission::Denied`, which
    /// `SPEC.md` §0.1 sends to the same terminal state as a timeout — so an
    /// error here costs nothing but a log line.
    pub const DENIED_TEXTS: &[&str] = &[
        "You weren't admitted to the meeting",
        "Sorry, you were denied access to the meeting",
        "Someone in the meeting denied your request to join",
        "You've been removed from the lobby",
    ];

    /// **INFERRED. Call ended.** Drives `InCall -> Completed`.
    pub const CALL_ENDED_TEXTS: &[&str] = &[
        "The meeting has ended",
        "Your call has ended",
        "Call ended",
        "You left the meeting",
        "Thanks for joining",
    ];

    /// **INFERRED. Removed by host.** Drives `InCall -> Stopped`, i.e. the audio
    /// captured so far is kept and the client gets a truncation banner. Checked
    /// BEFORE [`CALL_ENDED_TEXTS`] because both kinds of copy render on the same
    /// screen.
    pub const REMOVED_TEXTS: &[&str] = &[
        "You've been removed from the meeting",
        "You were removed from the meeting",
        "Someone removed you from the meeting",
        "An admin has removed you from this meeting",
    ];

    /// **INFERRED. In call.** Hang-up control, CSS anchors.
    pub const LEAVE_BUTTON: &[&str] = &[
        "button[data-tid='hangup-button']",
        "button#hangup-button",
        "button[data-tid='call-end-button']",
        "button[aria-label*='Leave' i]",
    ];

    /// **INFERRED. In call.** Accessible text of the hang-up control, tried
    /// before [`LEAVE_BUTTON`].
    pub const LEAVE_BUTTON_TEXTS: &[&str] = &["Leave", "Leave meeting", "Hang up", "End call"];

    /// **INFERRED. In call.** Participant-count readout. Feeds the lonely-bot
    /// exit; when it never resolves the wall-clock `max_call_duration` cap is
    /// what ends the call, which is why that cap exists.
    pub const PARTICIPANT_COUNT: &[&str] = &[
        "[data-tid='roster-button']",
        "button[aria-label*='participant' i]",
        "button[aria-label*='People' i]",
        "[data-tid='people-count']",
    ];

    /// **INFERRED. In call.** Participant tiles, the fallback count. Must be one
    /// element per human, bot included.
    pub const PARTICIPANT_TILES: &[&str] = &[
        "[data-tid='participant-tile']",
        "[data-tid^='calling-participant-']",
        "[data-cid='calling-participant-stream']",
    ];

    /// **INFERRED. In call.** "This person is talking right now" markers,
    /// consumed by `assets/capture.js` to stamp a speaker onto each frame.
    /// Purely best-effort: when it is stale every segment is attributed to
    /// `Unknown`, which the Python client renders fine.
    pub const SPEAKING_INDICATORS: &[&str] = &[
        "[data-tid='participant-speaking-indicator']",
        "[aria-label*='is speaking' i]",
        "[data-is-speaking='true']",
    ];

    /// **INFERRED. In call.** The tile a [`SPEAKING_INDICATORS`] hit sits in.
    pub const SPEAKER_TILE: &[&str] = &[
        "[data-tid='participant-tile']",
        "[data-tid^='calling-participant-']",
    ];

    /// **INFERRED. In call.** Where a display name lives inside a tile. `:self`
    /// means "read `data-participant-name` / `aria-label` off the tile itself".
    pub const SPEAKER_NAME: &[&str] = &[
        "[data-tid='participant-name']",
        "[data-participant-name]",
        ":self",
    ];
}

// ---------------------------------------------------------------------------
// Diagnostics vocabulary
// ---------------------------------------------------------------------------

/// Whether a selector group has ever been observed against a live Teams surface.
///
/// Carried into the logs and into `meetbot doctor` output so a failure at 22:00
/// says *which* kind of failure it is: a VERIFIED group that stopped matching is
/// Microsoft changing their markup, an INFERRED group that never matched is our
/// guess having been wrong all along. Those need opposite responses.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verified {
    /// Observed in a live capture on 2026-07-19.
    Yes,
    /// Never observed. See `spike/teams_recon.md` §8.
    No,
}

impl Verified {
    pub fn label(self) -> &'static str {
        match self {
            Verified::Yes => "VERIFIED",
            Verified::No => "INFERRED (never observed live)",
        }
    }
}

/// Where in the join dance a failure happened. Logged on every stage
/// transition and named in the error the join path returns, so a real meeting
/// failing overnight leaves an actionable trace instead of a silent skip.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JoinStage {
    /// Waiting out the five-hop redirect chain to `/light-meetings/launch`.
    Redirect,
    /// Pre-join (green room) rendered; filling the name.
    PreJoin,
    /// `coords` decoded and checked against the meeting id we were sent.
    CodeCheck,
    /// Clicking the join button.
    JoinClick,
    /// Post-click: lobby vs admitted vs the retry (rejection) screen.
    Admission,
}

impl JoinStage {
    pub fn as_str(self) -> &'static str {
        match self {
            JoinStage::Redirect => "redirect",
            JoinStage::PreJoin => "prejoin",
            JoinStage::CodeCheck => "code-check",
            JoinStage::JoinClick => "join-click",
            JoinStage::Admission => "admission",
        }
    }

    /// One line of "what this stage does and what to look at when it breaks",
    /// printed by `meetbot doctor`.
    pub fn hint(self) -> &'static str {
        match self {
            JoinStage::Redirect => {
                "navigate /meet/<id> and wait ~10-15s for the 5-hop chain to settle on \
                 /light-meetings/launch. Stalling on /dl/launcher/launcher.html means \
                 Microsoft reintroduced the 'Continue on this browser' interstitial \
                 (it does not exist today) — teams::selectors needs a click-through."
            }
            JoinStage::PreJoin => {
                "the green room must render and expose a display-name field. \
                 teams::selectors::PREJOIN_ROOT / NAME_INPUT (both VERIFIED)."
            }
            JoinStage::CodeCheck => {
                "the meeting id must survive the redirect chain, base64-wrapped inside \
                 the `coords` query parameter. teams::url_contains_code."
            }
            JoinStage::JoinClick => {
                "click teams::selectors::JOIN_BUTTON (VERIFIED). It is NEVER disabled, \
                 so a failure here means the element is absent, not that it was greyed out."
            }
            JoinStage::Admission => {
                "poll for RETRY_SCREEN (VERIFIED, terminal rejection), LOBBY_ROOT / \
                 IN_CALL_ROOT (both INFERRED — never observed live). A timeout here is a \
                 legitimate outcome for a dry run and for a bot that was not let in."
            }
        }
    }
}

/// The CSS selector groups reported in every probe's `diag` map, with their
/// verification status.
///
/// The join path logs this whole map at each stage, so the log line for a failed
/// join says exactly which groups matched and which did not — the difference
/// between "we never reached pre-join" and "we reached it and the name field
/// moved".
pub const DIAG_GROUPS: &[(&str, &[&str], Verified)] = &[
    ("prejoin_root", selectors::PREJOIN_ROOT, Verified::Yes),
    ("name_input", selectors::NAME_INPUT, Verified::Yes),
    ("join_button", selectors::JOIN_BUTTON, Verified::Yes),
    ("meeting_title", selectors::MEETING_TITLE, Verified::Yes),
    ("retry_screen", selectors::RETRY_SCREEN, Verified::Yes),
    ("retry_code_input", selectors::RETRY_CODE_INPUT, Verified::Yes),
    (
        "retry_passcode_input",
        selectors::RETRY_PASSCODE_INPUT,
        Verified::Yes,
    ),
    ("lobby_root", selectors::LOBBY_ROOT, Verified::No),
    ("in_call_root", selectors::IN_CALL_ROOT, Verified::No),
    ("leave_button", selectors::LEAVE_BUTTON, Verified::No),
];

/// `DIAG_GROUPS` without the verification column, in the shape the probe
/// template wants.
pub fn diag_groups() -> Vec<(&'static str, &'static [&'static str])> {
    DIAG_GROUPS.iter().map(|(n, s, _)| (*n, *s)).collect()
}

/// Verification status of a named diag group, for log and doctor output.
pub fn group_verification(name: &str) -> Option<Verified> {
    DIAG_GROUPS
        .iter()
        .find(|(n, _, _)| *n == name)
        .map(|(_, _, v)| *v)
}

// ---------------------------------------------------------------------------
// URL construction and the `coords` redirect
// ---------------------------------------------------------------------------

/// Teams' anonymous-join entry point.
pub const MEET_BASE: &str = "https://teams.microsoft.com/meet";

/// The URL the bot navigates to.
///
/// The passcode rides as `?p=<passcode>` rather than being typed into a field.
/// VERIFIED: Teams carries it through all five hops into `coords.passcode` and
/// prefills the passcode input on the retry screen. That is strictly better than
/// a DOM interaction — there is no field to type into on the happy path, and the
/// platform does the work.
pub fn join_url(native_id: &str, passcode: Option<&str>) -> String {
    match passcode.map(str::trim).filter(|p| !p.is_empty()) {
        Some(p) => format!("{MEET_BASE}/{native_id}?p={}", percent_encode(p)),
        None => format!("{MEET_BASE}/{native_id}"),
    }
}

/// Is the page still on the meeting we sent it to?
///
/// **This is the function the old Teams path got wrong.** After the redirect
/// chain settles, the current URL is
/// `/light-meetings/launch?...&coords=<BASE64>&...` and the meeting id appears
/// nowhere in it as plain text — a naive `url.contains(code)` reads a perfectly
/// healthy landing as "navigated away", reports `Admission::Denied`, and the
/// session finishes `completed` with zero segments, which the Python client
/// files as a green-heartbeat `skipped_not_admitted`. Every Teams meeting
/// vanished that way.
///
/// The fix is to decode, not to drop the check: the decoded `coords` blob is
/// JSON carrying both `meetingUrl` (which embeds the id) and `meetingCode`
/// (which is the id), so a substring test against the decoded bytes is
/// sufficient and needs no JSON parser.
pub fn url_contains_code(url: &str, code: &str) -> bool {
    if code.is_empty() {
        // Nothing to check against: never report a healthy page as navigated
        // away on the strength of an empty expectation.
        return true;
    }
    if url.contains(code) {
        return true;
    }
    decode_coords(url).is_some_and(|blob| blob.contains(code))
}

/// The `coords` query parameter, percent-decoded then base64-decoded, as lossy
/// UTF-8. `None` when the URL has no `coords`, or it is not decodable.
///
/// The payload is a JSON object; we deliberately do not parse it. A substring
/// test over the blob answers every question the join path actually asks, and
/// not parsing means a schema change on Microsoft's side cannot break us.
pub fn decode_coords(url: &str) -> Option<String> {
    let raw = query_param(url, "coords")?;
    let bytes = crate::meet::base64_decode(&raw)?;
    if bytes.is_empty() {
        return None;
    }
    Some(String::from_utf8_lossy(&bytes).into_owned())
}

/// The passcode Teams parsed out of the URL chain, read back from `coords`.
///
/// Diagnostic only, and best-effort: it is how a maintainer tells "we never sent
/// a passcode" apart from "we sent one and it was wrong", which the retry screen
/// itself refuses to distinguish.
pub fn coords_passcode(url: &str) -> Option<String> {
    let blob = decode_coords(url)?;
    let needle = "\"passcode\"";
    let start = blob.find(needle)? + needle.len();
    let rest = &blob[start..];
    let open = rest.find('"')?;
    let after = &rest[open + 1..];
    let close = after.find('"')?;
    let value = &after[..close];
    (!value.is_empty()).then(|| value.to_string())
}

/// Percent-decoded value of `name` from the query string of `url`.
///
/// Hand-rolled rather than pulling in a URL crate: the whole need is one query
/// parameter out of a URL we constructed the base of, and the crate already
/// hand-rolls base64 for the same reason.
pub fn query_param(url: &str, name: &str) -> Option<String> {
    let query = url.split_once('?').map(|(_, q)| q)?;
    // Strip a fragment: Teams' SPA URLs carry `#` segments.
    let query = query.split('#').next().unwrap_or(query);
    for pair in query.split('&') {
        let (key, value) = match pair.split_once('=') {
            Some(kv) => kv,
            None => (pair, ""),
        };
        if key == name {
            return Some(percent_decode(value));
        }
    }
    None
}

/// Percent-decoding, plus `+` as a space (Teams' launcher uses form encoding in
/// places). Invalid escapes are passed through verbatim rather than dropped —
/// this feeds a substring test, so tolerance beats strictness.
pub fn percent_decode(input: &str) -> String {
    let bytes = input.as_bytes();
    let mut out: Vec<u8> = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'+' => {
                out.push(b' ');
                i += 1;
            }
            b'%' if i + 2 < bytes.len() => {
                let hi = (bytes[i + 1] as char).to_digit(16);
                let lo = (bytes[i + 2] as char).to_digit(16);
                match (hi, lo) {
                    (Some(h), Some(l)) => {
                        out.push((h * 16 + l) as u8);
                        i += 3;
                    }
                    _ => {
                        out.push(bytes[i]);
                        i += 1;
                    }
                }
            }
            b => {
                out.push(b);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// Percent-encodes a query-parameter value. Conservative: everything outside
/// the RFC 3986 unreserved set is escaped, so a passcode containing `&`, `#` or
/// a space cannot terminate or corrupt the query string.
pub fn percent_encode(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    for b in input.as_bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(*b as char)
            }
            other => out.push_str(&format!("%{other:02X}")),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // -- URL construction ---------------------------------------------------

    #[test]
    fn join_url_without_passcode_is_the_bare_meet_url() {
        assert_eq!(
            join_url("1234567890123", None),
            "https://teams.microsoft.com/meet/1234567890123"
        );
        // An empty / whitespace passcode must not produce a `?p=` with nothing
        // after it: Teams then parses an empty passcode and rejects the join.
        assert_eq!(
            join_url("1234567890123", Some("   ")),
            "https://teams.microsoft.com/meet/1234567890123"
        );
    }

    /// VERIFIED delivery mechanism: `?p=` propagates through all five hops into
    /// `coords.passcode` and prefills the passcode field. This is the whole
    /// passcode implementation on the happy path.
    #[test]
    fn join_url_routes_the_passcode_as_a_query_param() {
        assert_eq!(
            join_url("1234567890123", Some("AbCd1234EfGh")),
            "https://teams.microsoft.com/meet/1234567890123?p=AbCd1234EfGh"
        );
    }

    #[test]
    fn join_url_escapes_a_passcode_that_could_break_the_query_string() {
        assert_eq!(
            join_url("1234567890123", Some("a&b c#d")),
            "https://teams.microsoft.com/meet/1234567890123?p=a%26b%20c%23d"
        );
    }

    // -- percent coding -----------------------------------------------------

    #[test]
    fn percent_decode_handles_escapes_plus_and_garbage() {
        assert_eq!(percent_decode("a%20b"), "a b");
        assert_eq!(percent_decode("a+b"), "a b");
        assert_eq!(percent_decode("eyJt%2BZQ%3D%3D"), "eyJt+ZQ==");
        // Truncated / invalid escapes pass through rather than eating bytes.
        assert_eq!(percent_decode("100%"), "100%");
        assert_eq!(percent_decode("%zz"), "%zz");
    }

    #[test]
    fn percent_encode_round_trips_through_decode() {
        for raw in ["AbCd1234EfGh", "a&b c#d", "p=q?r", "плюс"] {
            assert_eq!(percent_decode(&percent_encode(raw)), raw);
        }
    }

    // -- query parsing ------------------------------------------------------

    #[test]
    fn query_param_reads_a_named_parameter() {
        let url = "https://teams.microsoft.com/light-meetings/launch?anon=true&coords=QUJD&agent=web";
        assert_eq!(query_param(url, "coords").as_deref(), Some("QUJD"));
        assert_eq!(query_param(url, "anon").as_deref(), Some("true"));
        assert_eq!(query_param(url, "nope"), None);
        assert_eq!(query_param("https://teams.microsoft.com/meet/1", "coords"), None);
    }

    #[test]
    fn query_param_ignores_a_fragment() {
        let url = "https://teams.microsoft.com/v2/?meetingjoin=true&coords=QUJD#/meet/9";
        assert_eq!(query_param(url, "coords").as_deref(), Some("QUJD"));
    }

    // -- the coords redirect: the bug this whole module exists to fix -------

    /// Builds the real thing: the JSON blob Teams base64s into `coords`, then
    /// percent-encodes into the final `/light-meetings/launch` URL.
    fn light_meetings_url(code: &str, passcode: Option<&str>) -> String {
        let json = match passcode {
            Some(p) => format!(
                "{{\"meetingUrl\":\"https://teams.microsoft.com/meet/{code}?p={p}&anon=true&\
                 launchAgent=join_launcher_web&lightExperience=true&correlationId=74ccaec3-0000\",\
                 \"meetingCode\":\"{code}\",\"passcode\":\"{p}\"}}"
            ),
            None => format!(
                "{{\"meetingUrl\":\"https://teams.microsoft.com/meet/{code}?anon=true&\
                 launchAgent=join_launcher_web&lightExperience=true&correlationId=74ccaec3-0000\",\
                 \"meetingCode\":\"{code}\"}}"
            ),
        };
        let coords = percent_encode(&base64_encode(json.as_bytes()));
        format!(
            "https://teams.microsoft.com/light-meetings/launch?anon=true&\
             launchAgent=join_launcher_web&lightExperience=true&correlationId=74ccaec3-0000&\
             agent=web&coords={coords}&deeplinkId=aaaaaaaa-0000"
        )
    }

    /// Test-only encoder, so the fixtures above are built the same way Teams
    /// builds them instead of being pasted opaque blobs.
    fn base64_encode(bytes: &[u8]) -> String {
        const T: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        let mut out = String::new();
        for chunk in bytes.chunks(3) {
            let b = [
                chunk[0],
                *chunk.get(1).unwrap_or(&0),
                *chunk.get(2).unwrap_or(&0),
            ];
            let n = ((b[0] as u32) << 16) | ((b[1] as u32) << 8) | b[2] as u32;
            out.push(T[(n >> 18) as usize & 63] as char);
            out.push(T[(n >> 12) as usize & 63] as char);
            out.push(if chunk.len() > 1 {
                T[(n >> 6) as usize & 63] as char
            } else {
                '='
            });
            out.push(if chunk.len() > 2 {
                T[n as usize & 63] as char
            } else {
                '='
            });
        }
        out
    }

    #[test]
    fn code_survives_the_plain_meet_url() {
        assert!(url_contains_code(
            "https://teams.microsoft.com/meet/1234567890123",
            "1234567890123"
        ));
        assert!(url_contains_code(
            "https://teams.microsoft.com/meet/1234567890123?p=AbCd",
            "1234567890123"
        ));
    }

    /// THE REGRESSION TEST. A plain substring check fails on this URL; that
    /// failure is what made every Teams meeting finish as a silent zero-segment
    /// skip. If this test ever goes red, Teams is silently broken again.
    #[test]
    fn code_is_found_inside_the_base64_coords_parameter() {
        let url = light_meetings_url("1234567890123", None);
        assert!(
            !url.contains("1234567890123"),
            "fixture is wrong: the id must NOT be in the URL as plain text, \
             otherwise this test proves nothing"
        );
        assert!(
            url_contains_code(&url, "1234567890123"),
            "the meeting id is base64-wrapped in `coords` and must be decoded, not dropped"
        );
    }

    #[test]
    fn code_is_found_in_coords_when_a_passcode_is_present() {
        let url = light_meetings_url("1234567890123", Some("AbCd1234EfGh"));
        assert!(url_contains_code(&url, "1234567890123"));
    }

    /// The check must still be a real check: a genuinely different meeting, or
    /// a bounce back to the Teams landing page, has to read as "navigated away".
    #[test]
    fn a_different_meeting_does_not_satisfy_the_code_check() {
        let url = light_meetings_url("9999999999999", None);
        assert!(!url_contains_code(&url, "1234567890123"));
        assert!(!url_contains_code("https://teams.microsoft.com/v2/", "1234567890123"));
        assert!(!url_contains_code(
            "https://teams.microsoft.com/dl/launcher/launcher.html?type=meet",
            "1234567890123"
        ));
    }

    #[test]
    fn an_empty_expected_code_never_reports_navigated_away() {
        assert!(url_contains_code("https://teams.microsoft.com/v2/", ""));
    }

    #[test]
    fn undecodable_coords_do_not_panic_or_falsely_match() {
        assert!(!url_contains_code(
            "https://teams.microsoft.com/light-meetings/launch?coords=!!!not-base64!!!",
            "1234567890123"
        ));
        assert_eq!(
            decode_coords("https://teams.microsoft.com/light-meetings/launch?coords="),
            None
        );
    }

    #[test]
    fn decoded_coords_carry_both_the_url_and_the_bare_code() {
        let url = light_meetings_url("1234567890123", None);
        let blob = decode_coords(&url).expect("coords must decode");
        assert!(blob.contains("\"meetingCode\":\"1234567890123\""));
        assert!(blob.contains("https://teams.microsoft.com/meet/1234567890123"));
    }

    // -- passcode routing ---------------------------------------------------

    /// Proves the whole passcode path end to end at the URL level: what
    /// `join_url` puts on the wire is what comes back out of `coords`.
    #[test]
    fn passcode_routed_via_query_param_arrives_in_coords() {
        let url = light_meetings_url("1234567890123", Some("AbCd1234EfGh"));
        assert_eq!(coords_passcode(&url).as_deref(), Some("AbCd1234EfGh"));
    }

    #[test]
    fn no_passcode_means_no_passcode_in_coords() {
        let url = light_meetings_url("1234567890123", None);
        assert_eq!(coords_passcode(&url), None);
    }

    #[test]
    fn coords_passcode_is_none_when_there_are_no_coords() {
        assert_eq!(coords_passcode("https://teams.microsoft.com/meet/123"), None);
    }

    // -- selector-table discipline -----------------------------------------

    /// The in-call marker list must never contain a selector the VERIFIED
    /// pre-join screen also matches. `toggle-mute` is the specific trap: it is
    /// byte-identical on both surfaces, so including it would make the bot
    /// declare itself admitted while standing in the green room and record a
    /// call it never joined.
    #[test]
    fn in_call_markers_never_overlap_the_prejoin_screen() {
        for marker in selectors::IN_CALL_ROOT {
            assert!(
                !marker.contains("toggle-mute") && !marker.contains("toggle-video"),
                "{marker} also matches the pre-join screen; it cannot prove admission"
            );
            assert!(
                !selectors::PREJOIN_ROOT.contains(marker),
                "{marker} is a pre-join anchor and cannot prove admission"
            );
        }
        // And the guard that catches the next version of this mistake.
        assert!(!selectors::NOT_IN_CALL.is_empty());
        for guard in [
            "[data-tid='calling-prejoin-screen']",
            "[data-tid='calling-retry-screen']",
        ] {
            assert!(
                selectors::NOT_IN_CALL.contains(&guard),
                "{guard} must veto an in-call claim"
            );
        }
    }

    /// Every diag group has to declare whether it was ever observed live. A
    /// group with no verification status makes the log line unreadable at 22:00.
    #[test]
    fn every_diag_group_declares_its_verification_status() {
        assert!(!DIAG_GROUPS.is_empty());
        for (name, sels, _) in DIAG_GROUPS {
            assert!(!sels.is_empty(), "diag group {name} has no selectors");
            assert!(group_verification(name).is_some());
        }
        assert_eq!(group_verification("prejoin_root"), Some(Verified::Yes));
        assert_eq!(group_verification("in_call_root"), Some(Verified::No));
        assert_eq!(group_verification("nonexistent"), None);
        assert_eq!(diag_groups().len(), DIAG_GROUPS.len());
    }

    /// Candidate-list discipline, same rule as `meet::selectors`: every entry is
    /// a non-empty list so "first match wins" always has something to try.
    #[test]
    fn every_selector_group_is_a_non_empty_candidate_list() {
        for (name, list) in [
            ("NAME_INPUT", selectors::NAME_INPUT),
            ("JOIN_BUTTON", selectors::JOIN_BUTTON),
            ("PREJOIN_ROOT", selectors::PREJOIN_ROOT),
            ("RETRY_SCREEN", selectors::RETRY_SCREEN),
            ("LOBBY_ROOT", selectors::LOBBY_ROOT),
            ("IN_CALL_ROOT", selectors::IN_CALL_ROOT),
            ("LEAVE_BUTTON", selectors::LEAVE_BUTTON),
            ("PARTICIPANT_TILES", selectors::PARTICIPANT_TILES),
            ("SPEAKING_INDICATORS", selectors::SPEAKING_INDICATORS),
        ] {
            assert!(!list.is_empty(), "{name} must have at least one candidate");
        }
    }

    #[test]
    fn join_stages_have_distinct_names_and_hints() {
        let stages = [
            JoinStage::Redirect,
            JoinStage::PreJoin,
            JoinStage::CodeCheck,
            JoinStage::JoinClick,
            JoinStage::Admission,
        ];
        let mut names: Vec<&str> = stages.iter().map(|s| s.as_str()).collect();
        names.sort_unstable();
        names.dedup();
        assert_eq!(names.len(), stages.len(), "stage names must be unique");
        for s in stages {
            assert!(!s.hint().is_empty());
        }
    }

    #[test]
    fn verified_labels_are_distinguishable() {
        assert!(Verified::Yes.label().contains("VERIFIED"));
        assert!(Verified::No.label().contains("INFERRED"));
    }
}
