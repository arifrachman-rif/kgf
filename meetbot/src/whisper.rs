//! OpenAI-compatible transcription client for the Windows-host whisper-server,
//! plus the `run_transcriber` worker that turns utterances into DB segments.
//!
//! Contract: `SPEC.md` §6.3. Owner: the `whisper` builder agent.
//!
//! # Why this module is paranoid
//!
//! The whisper-server does not live in WSL. It runs on the Windows host and is
//! reachable only through the WSL NAT gateway, whose address changes whenever
//! the host reboots or the WSL network is recreated. The previous stack pinned
//! that address into a `.env` file and "self-healed" by rewriting the file,
//! which broke every time the two disagreed. Here the gateway is resolved from
//! `ip route` at call time, cached for [`GATEWAY_TTL`], and **re-resolved
//! immediately on any connection failure** before the request is retried.
//!
//! Second landmine, straight from `vexa_bots.py:484-488`: whisper-server
//! reports the detected language as a full English word (`"english"`), not an
//! ISO-639-1 code. Vexa's validator rejected the row and silently persisted
//! zero segments, losing a whole meeting with no error anywhere. Everything the
//! server says is therefore treated as untrusted text and pushed through
//! [`normalize_language`] before it reaches the database.
//!
//! Third: a dead whisper must never fail a session. [`run_transcriber`] retries
//! with backoff and then **drops** the utterance. Per `SPEC.md` §0.1 a meeting
//! with no segments still finishes `completed`.

use std::process::Command;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, Instant};

use serde::Deserialize;
use tokio::sync::mpsc;
use uuid::Uuid;

use crate::audio::Utterance;
use crate::db::{Db, NewSegment};

/// Fallback gateway used when `ip route` gives us nothing usable.
pub const FALLBACK_GATEWAY: &str = "172.25.32.1";

/// How long a successfully resolved gateway is trusted before re-resolution.
/// Short on purpose: resolution costs one `ip route` exec (~1 ms) and a stale
/// gateway costs a whole meeting.
pub const GATEWAY_TTL: Duration = Duration::from_secs(60);

/// Request timeout for a single transcription call. Whisper on CPU can take a
/// while on a 25 s chunk (the segmenter's `max_utterance_ms` ceiling).
pub const DEFAULT_TIMEOUT: Duration = Duration::from_secs(120);

/// Liveness probe budget. `SPEC.md` §6.3: never blocks longer than this.
pub const HEALTH_TIMEOUT: Duration = Duration::from_secs(5);

/// Model name sent in the multipart body. Overridable with
/// `MEETBOT_WHISPER_MODEL` for servers that expose a different alias.
pub const DEFAULT_MODEL: &str = "whisper-1";

/// Base delay for the exponential backoff in [`run_transcriber`].
const RETRY_BASE_DELAY: Duration = Duration::from_millis(500);

/// Ceiling for the backoff, so a long meeting against a dead whisper does not
/// end up sleeping for minutes per utterance.
const RETRY_MAX_DELAY: Duration = Duration::from_secs(8);

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, thiserror::Error)]
pub enum WhisperError {
    #[error("whisper unreachable at {endpoint}: {source}")]
    Unreachable {
        endpoint: String,
        source: reqwest::Error,
    },
    #[error("whisper HTTP {status}: {body}")]
    Http { status: u16, body: String },
    #[error("whisper response decode failed: {0}")]
    Decode(String),
    #[error("wav encode failed: {0}")]
    Encode(String),
}

impl WhisperError {
    /// Worth another attempt: the box was unreachable, or the server answered
    /// with a 5xx / 429. A 4xx means we sent something it did not like and
    /// retrying produces the identical rejection.
    pub fn is_retryable(&self) -> bool {
        match self {
            WhisperError::Unreachable { .. } => true,
            WhisperError::Http { status, .. } => *status >= 500 || *status == 429,
            WhisperError::Decode(_) | WhisperError::Encode(_) => false,
        }
    }

    /// A transport-level failure, which is also the signal to re-resolve the
    /// WSL gateway before the next attempt.
    pub fn is_connection_failure(&self) -> bool {
        matches!(self, WhisperError::Unreachable { .. })
    }
}

// ---------------------------------------------------------------------------
// Response shapes
// ---------------------------------------------------------------------------

/// The flat part of an OpenAI-compatible transcription response.
#[derive(Debug, Clone, Deserialize)]
pub struct Transcription {
    pub text: String,
    /// Raw server value, may be a full name like "english" — normalize before use.
    #[serde(default)]
    pub language: Option<String>,
}

/// One `verbose_json` segment. Every field is optional because the field set
/// varies between whisper.cpp, faster-whisper and the OpenAI service.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct VerboseSegment {
    #[serde(default)]
    pub start: Option<f64>,
    #[serde(default)]
    pub end: Option<f64>,
    #[serde(default)]
    pub text: Option<String>,
}

/// Everything we are willing to read out of a transcription response.
///
/// Deliberately liberal: `response_format=verbose_json` is requested, but a
/// server that ignores it and returns `{"text": "..."}` still parses, and so
/// does one that returns a bare JSON string or non-JSON plain text.
#[derive(Debug, Clone, Default)]
pub struct TranscriptionResult {
    pub text: String,
    /// Already normalized to ISO-639-1, or `None` when unrecognized.
    pub language: Option<String>,
    /// Sub-segments, offsets relative to the start of the submitted clip.
    pub segments: Vec<VerboseSegment>,
}

impl TranscriptionResult {
    /// The flat view the frozen [`Transcription`] type exposes.
    pub fn as_transcription(&self) -> Transcription {
        Transcription {
            text: self.text.clone(),
            language: self.language.clone(),
        }
    }
}

/// Parses a whisper response body without trusting its shape.
///
/// Accepted, in order:
/// 1. an object with `text` (plus optional `language` / `segments`)
/// 2. a bare JSON string (`"hello"`)
/// 3. an object with only `segments`, whose texts are joined
/// 4. anything else non-empty and non-markup, taken as raw text
pub fn parse_transcription_body(body: &str) -> Result<TranscriptionResult, WhisperError> {
    let trimmed = body.trim();
    if trimmed.is_empty() {
        return Ok(TranscriptionResult::default());
    }

    let value: serde_json::Value = match serde_json::from_str(trimmed) {
        Ok(v) => v,
        Err(_) => {
            // whisper.cpp's text mode and a few reverse proxies answer with bare
            // text. If it is not JSON and not obviously markup, take it as-is.
            if trimmed.starts_with('<') {
                return Err(WhisperError::Decode(format!(
                    "expected JSON, got markup: {}",
                    truncate(trimmed, 200)
                )));
            }
            return Ok(TranscriptionResult {
                text: trimmed.to_string(),
                language: None,
                segments: Vec::new(),
            });
        }
    };

    if let Some(s) = value.as_str() {
        return Ok(TranscriptionResult {
            text: s.trim().to_string(),
            language: None,
            segments: Vec::new(),
        });
    }

    let obj = value
        .as_object()
        .ok_or_else(|| WhisperError::Decode(format!("unexpected JSON shape: {}", truncate(trimmed, 200))))?;

    // Some servers wrap errors in a 200 response. Surface that rather than
    // silently persisting an empty transcript.
    if !obj.contains_key("text")
        && !obj.contains_key("segments")
        && let Some(err) = obj.get("error")
    {
        let detail = err
            .get("message")
            .and_then(|m| m.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| err.to_string());
        return Err(WhisperError::Decode(format!("server error: {detail}")));
    }

    let segments: Vec<VerboseSegment> = obj
        .get("segments")
        .and_then(|s| s.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| serde_json::from_value::<VerboseSegment>(v.clone()).ok())
                .collect()
        })
        .unwrap_or_default();

    let text = obj
        .get("text")
        .and_then(|t| t.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| {
            segments
                .iter()
                .filter_map(|s| s.text.as_deref())
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .collect::<Vec<_>>()
                .join(" ")
        });

    let language = obj
        .get("language")
        .and_then(|l| l.as_str())
        .and_then(normalize_language);

    Ok(TranscriptionResult {
        text,
        language,
        segments,
    })
}

// ---------------------------------------------------------------------------
// Endpoint plumbing
// ---------------------------------------------------------------------------

/// The pieces of the whisper URL we need in order to rewrite the host.
#[derive(Debug, Clone, PartialEq, Eq)]
struct EndpointParts {
    scheme: String,
    host: String,
    port: Option<u16>,
    path: String,
}

impl EndpointParts {
    fn parse(url: &str) -> Option<EndpointParts> {
        let (scheme, rest) = url.split_once("://")?;
        if scheme.is_empty() || rest.is_empty() {
            return None;
        }
        let (authority, path) = match rest.find('/') {
            Some(i) => (&rest[..i], &rest[i..]),
            None => (rest, ""),
        };
        if authority.is_empty() {
            return None;
        }
        // IPv6 literals arrive bracketed: [::1]:8083
        let (host, port) = if let Some(close) = authority.rfind(']') {
            let host = &authority[..=close];
            let port = authority[close + 1..]
                .strip_prefix(':')
                .and_then(|p| p.parse::<u16>().ok());
            (host.to_string(), port)
        } else {
            match authority.rsplit_once(':') {
                Some((h, p)) => match p.parse::<u16>() {
                    Ok(port) => (h.to_string(), Some(port)),
                    Err(_) => (authority.to_string(), None),
                },
                None => (authority.to_string(), None),
            }
        };
        Some(EndpointParts {
            scheme: scheme.to_string(),
            host,
            port,
            path: path.to_string(),
        })
    }

    fn with_host(&self, host: &str) -> EndpointParts {
        EndpointParts {
            host: host.to_string(),
            ..self.clone()
        }
    }

    fn to_url(&self) -> String {
        match self.port {
            Some(p) => format!("{}://{}:{}{}", self.scheme, self.host, p, self.path),
            None => format!("{}://{}{}", self.scheme, self.host, self.path),
        }
    }

    /// `scheme://host:port/` — what the liveness probe hits.
    fn origin(&self) -> String {
        match self.port {
            Some(p) => format!("{}://{}:{}/", self.scheme, self.host, p),
            None => format!("{}://{}/", self.scheme, self.host),
        }
    }
}

/// True when the host looks like a NAT gateway address we are allowed to
/// repoint at a freshly resolved gateway. An explicit hostname
/// (`whisper.local`), a public IP, or loopback is left alone: the operator
/// meant it, and silently swapping it would be worse than failing.
fn host_is_reresolvable(host: &str) -> bool {
    let octets: Vec<&str> = host.split('.').collect();
    if octets.len() != 4 {
        return false;
    }
    let nums: Option<Vec<u8>> = octets.iter().map(|o| o.parse::<u8>().ok()).collect();
    let Some(n) = nums else { return false };
    match (n[0], n[1]) {
        (10, _) => true,
        (172, b) if (16..=31).contains(&b) => true,
        (192, 168) => true,
        _ => false,
    }
}

struct GatewayCache {
    value: String,
    at: Instant,
}

fn gateway_cache() -> &'static Mutex<Option<GatewayCache>> {
    static CACHE: OnceLock<Mutex<Option<GatewayCache>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(None))
}

/// Pulls the default-route gateway out of `ip route` output.
///
/// Handles both `ip route show default` (`default via 172.25.32.1 dev eth0`)
/// and the full `ip route` listing, where the default line is one of several.
pub fn parse_default_gateway(output: &str) -> Option<String> {
    for line in output.lines() {
        let mut fields = line.split_whitespace();
        if fields.next() != Some("default") {
            continue;
        }
        let mut rest = fields.peekable();
        while let Some(tok) = rest.next() {
            if tok == "via"
                && let Some(addr) = rest.peek()
                && !addr.is_empty()
            {
                return Some((*addr).to_string());
            }
        }
    }
    None
}

/// Runs `ip route` and extracts the default gateway. No caching, no fallback.
fn resolve_gateway_uncached() -> Option<String> {
    // `ip route show default` is the narrow query; fall back to the full table
    // because some minimal images ship a busybox `ip` without `show`.
    for args in [["route", "show", "default"].as_slice(), ["route"].as_slice()] {
        match Command::new("ip").args(args).output() {
            Ok(out) => {
                let text = String::from_utf8_lossy(&out.stdout);
                if let Some(gw) = parse_default_gateway(&text) {
                    return Some(gw);
                }
            }
            Err(e) => {
                tracing::debug!(error = %e, args = ?args, "`ip route` invocation failed");
            }
        }
    }
    None
}

/// Default gateway from `ip route show default`; falls back to "172.25.32.1".
///
/// Cached for [`GATEWAY_TTL`]. Call [`invalidate_gateway_cache`] to force the
/// next call to re-exec `ip route` — that is what makes the connection-failure
/// self-heal actually heal.
pub fn gateway_ip() -> String {
    let mut guard = match gateway_cache().lock() {
        Ok(g) => g,
        // Poisoning would mean a panic inside this tiny critical section, which
        // cannot happen; recover rather than propagate.
        Err(poisoned) => poisoned.into_inner(),
    };

    if let Some(cached) = guard.as_ref()
        && cached.at.elapsed() < GATEWAY_TTL
    {
        return cached.value.clone();
    }

    let resolved = resolve_gateway_uncached().unwrap_or_else(|| {
        tracing::warn!(
            fallback = FALLBACK_GATEWAY,
            "could not resolve default route gateway, using fallback"
        );
        FALLBACK_GATEWAY.to_string()
    });

    *guard = Some(GatewayCache {
        value: resolved.clone(),
        at: Instant::now(),
    });
    resolved
}

/// Drops the cached gateway so the next [`gateway_ip`] call re-reads `ip route`.
pub fn invalidate_gateway_cache() {
    let mut guard = match gateway_cache().lock() {
        Ok(g) => g,
        Err(poisoned) => poisoned.into_inner(),
    };
    *guard = None;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct WhisperClient {
    http: reqwest::Client,
    endpoint: String,
    timeout: Duration,
    /// Host actually in use. `None` means "the configured one"; it is set to a
    /// freshly resolved gateway after a connection failure.
    active_host: Arc<Mutex<Option<String>>>,
}

impl WhisperClient {
    pub fn new(http: reqwest::Client, endpoint: impl Into<String>) -> WhisperClient {
        WhisperClient {
            http,
            endpoint: endpoint.into(),
            timeout: DEFAULT_TIMEOUT,
            active_host: Arc::new(Mutex::new(None)),
        }
    }

    /// Overrides the per-request timeout (default [`DEFAULT_TIMEOUT`]).
    pub fn with_timeout(mut self, timeout: Duration) -> WhisperClient {
        self.timeout = timeout;
        self
    }

    /// The endpoint as configured. See [`WhisperClient::active_endpoint`] for
    /// the URL requests are currently going to.
    pub fn endpoint(&self) -> &str {
        &self.endpoint
    }

    fn parts(&self) -> Option<EndpointParts> {
        let base = EndpointParts::parse(&self.endpoint)?;
        let host = {
            let guard = match self.active_host.lock() {
                Ok(g) => g,
                Err(p) => p.into_inner(),
            };
            guard.clone()
        };
        Some(match host {
            Some(h) => base.with_host(&h),
            None => base,
        })
    }

    /// The URL requests currently go to: the configured endpoint, with the host
    /// replaced if a connection failure forced a gateway re-resolution.
    pub fn active_endpoint(&self) -> String {
        self.parts()
            .map(|p| p.to_url())
            .unwrap_or_else(|| self.endpoint.clone())
    }

    /// Re-reads `ip route` and, when the current host is a private NAT address
    /// that no longer matches, repoints this client at the new gateway.
    /// Returns the endpoint in force afterwards.
    pub fn refresh_gateway(&self) -> String {
        invalidate_gateway_cache();
        let Some(parts) = self.parts() else {
            return self.endpoint.clone();
        };
        if !host_is_reresolvable(&parts.host) {
            return parts.to_url();
        }
        let gw = gateway_ip();
        if gw != parts.host {
            tracing::warn!(
                old = %parts.host,
                new = %gw,
                "whisper host unreachable; repointing at freshly resolved WSL gateway"
            );
            let mut guard = match self.active_host.lock() {
                Ok(g) => g,
                Err(p) => p.into_inner(),
            };
            *guard = Some(gw.clone());
            return parts.with_host(&gw).to_url();
        }
        parts.to_url()
    }

    fn model(&self) -> String {
        std::env::var("MEETBOT_WHISPER_MODEL")
            .ok()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| DEFAULT_MODEL.to_string())
    }

    /// GET the endpoint root; any HTTP response counts as up, only a
    /// connection error counts as down. Never panics, never blocks > 5 s.
    pub async fn health(&self) -> bool {
        if self.probe_once().await {
            return true;
        }
        // One retry after a gateway re-resolution: on a host reboot the old
        // address is simply gone and the new one usually answers immediately.
        let before = self.active_endpoint();
        let after = self.refresh_gateway();
        if after == before {
            return false;
        }
        self.probe_once().await
    }

    async fn probe_once(&self) -> bool {
        let url = match self.parts() {
            Some(p) => p.origin(),
            None => {
                tracing::warn!(endpoint = %self.endpoint, "whisper endpoint is not a valid URL");
                return false;
            }
        };
        match self.http.get(&url).timeout(HEALTH_TIMEOUT).send().await {
            Ok(resp) => {
                tracing::debug!(url = %url, status = resp.status().as_u16(), "whisper probe ok");
                true
            }
            Err(e) => {
                tracing::debug!(url = %url, error = %e, "whisper probe failed");
                false
            }
        }
    }

    /// One transcription attempt. No retries — see
    /// [`WhisperClient::transcribe_retrying`] and [`run_transcriber`].
    pub async fn transcribe(
        &self,
        wav: Vec<u8>,
        language: Option<&str>,
    ) -> Result<Transcription, WhisperError> {
        self.transcribe_detailed(wav, language)
            .await
            .map(|r| r.as_transcription())
    }

    /// Full response including `verbose_json` sub-segments (offsets relative to
    /// the start of the submitted clip).
    pub async fn transcribe_detailed(
        &self,
        wav: Vec<u8>,
        language: Option<&str>,
    ) -> Result<TranscriptionResult, WhisperError> {
        let url = self.active_endpoint();

        let part = reqwest::multipart::Part::bytes(wav)
            .file_name("chunk.wav")
            .mime_str("audio/wav")
            .map_err(|e| WhisperError::Encode(format!("multipart part: {e}")))?;

        let mut form = reqwest::multipart::Form::new()
            .part("file", part)
            .text("model", self.model())
            .text("response_format", "verbose_json");

        // `language` is optional on the wire: absent means auto-detect.
        // Normalize first, because the server that answers "english" also tends
        // to reject "english" on the way in.
        if let Some(lang) = language.and_then(normalize_language) {
            form = form.text("language", lang);
        }

        let resp = self
            .http
            .post(&url)
            .timeout(self.timeout)
            .multipart(form)
            .send()
            .await
            .map_err(|source| WhisperError::Unreachable {
                endpoint: url.clone(),
                source,
            })?;

        let status = resp.status();
        let body = resp.text().await.map_err(|source| WhisperError::Unreachable {
            endpoint: url.clone(),
            source,
        })?;

        if !status.is_success() {
            return Err(WhisperError::Http {
                status: status.as_u16(),
                body: truncate(body.trim(), 300),
            });
        }

        parse_transcription_body(&body)
    }

    /// [`WhisperClient::transcribe_detailed`] with bounded exponential backoff.
    /// Re-resolves the gateway before every retry that followed a connection
    /// failure.
    pub async fn transcribe_retrying(
        &self,
        wav: Vec<u8>,
        language: Option<&str>,
        max_retries: u32,
    ) -> Result<TranscriptionResult, WhisperError> {
        let mut attempt = 0u32;
        loop {
            match self.transcribe_detailed(wav.clone(), language).await {
                Ok(result) => return Ok(result),
                Err(err) => {
                    if attempt >= max_retries || !err.is_retryable() {
                        return Err(err);
                    }
                    if err.is_connection_failure() {
                        self.refresh_gateway();
                    }
                    let delay = backoff_delay(attempt);
                    tracing::warn!(
                        attempt = attempt + 1,
                        max_retries,
                        delay_ms = delay.as_millis() as u64,
                        error = %err,
                        "whisper attempt failed, retrying"
                    );
                    tokio::time::sleep(delay).await;
                    attempt += 1;
                }
            }
        }
    }

    /// `Ok(None)` when the transcript is blank or a known non-speech artifact.
    pub async fn transcribe_utterance(
        &self,
        u: &Utterance,
        language: Option<&str>,
    ) -> Result<Option<NewSegment>, WhisperError> {
        let wav = u
            .to_wav_bytes()
            .map_err(|e| WhisperError::Encode(e.to_string()))?;
        let result = self.transcribe_detailed(wav, language).await?;
        Ok(collapse_to_segment(u, &result, language))
    }

    /// Every sub-segment of one utterance, with offsets shifted onto the
    /// meeting timeline. Falls back to a single whole-utterance segment when
    /// the server did not honor `verbose_json`.
    pub async fn transcribe_utterance_segments(
        &self,
        u: &Utterance,
        language: Option<&str>,
        max_retries: u32,
    ) -> Result<Vec<NewSegment>, WhisperError> {
        let wav = u
            .to_wav_bytes()
            .map_err(|e| WhisperError::Encode(e.to_string()))?;
        let result = self.transcribe_retrying(wav, language, max_retries).await?;
        Ok(expand_to_segments(u, &result, language))
    }
}

/// Exponential backoff with a ceiling: 0.5 s, 1 s, 2 s, 4 s, 8 s, 8 s…
fn backoff_delay(attempt: u32) -> Duration {
    let factor = 1u32 << attempt.min(5);
    let delay = RETRY_BASE_DELAY.saturating_mul(factor);
    if delay > RETRY_MAX_DELAY {
        RETRY_MAX_DELAY
    } else {
        delay
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        return s.to_string();
    }
    s.chars().take(max).collect::<String>() + "…"
}

/// Picks the language to persist: what the server detected, else what we asked
/// for. Both are normalized; anything unrecognized becomes `None`.
fn resolve_language(result: &TranscriptionResult, requested: Option<&str>) -> Option<String> {
    result
        .language
        .clone()
        .or_else(|| requested.and_then(normalize_language))
}

/// One utterance -> at most one segment, keyed to the utterance's own offsets.
fn collapse_to_segment(
    u: &Utterance,
    result: &TranscriptionResult,
    requested: Option<&str>,
) -> Option<NewSegment> {
    let text = result.text.trim();
    if is_noise_transcript(text, u.duration_sec()) {
        return None;
    }
    Some(NewSegment {
        start_time: u.start_time,
        end_time: u.end_time,
        speaker: u.speaker.clone(),
        text: text.to_string(),
        language: resolve_language(result, requested),
    })
}

/// One utterance -> its `verbose_json` sub-segments, offsets shifted from
/// clip-relative to meeting-relative and clamped to the utterance window.
fn expand_to_segments(
    u: &Utterance,
    result: &TranscriptionResult,
    requested: Option<&str>,
) -> Vec<NewSegment> {
    let language = resolve_language(result, requested);
    let duration = u.duration_sec().max(0.0);

    let mut out: Vec<NewSegment> = Vec::new();
    for seg in &result.segments {
        let text = seg.text.as_deref().unwrap_or("").trim();
        let rel_start = seg.start.unwrap_or(0.0).max(0.0);
        let rel_end = seg.end.unwrap_or(rel_start).max(rel_start);
        // Whisper's own segment length is the honest duration for the noise
        // heuristic: a 0.3 s "you" inside a 20 s clip is still a hallucination.
        let seg_duration = if rel_end > rel_start {
            rel_end - rel_start
        } else {
            duration
        };
        if is_noise_transcript(text, seg_duration) {
            continue;
        }
        let start = u.start_time + rel_start.min(duration);
        let end = (u.start_time + rel_end.min(duration)).max(start);
        out.push(NewSegment {
            start_time: start,
            end_time: end,
            speaker: u.speaker.clone(),
            text: text.to_string(),
            language: language.clone(),
        });
    }

    if out.is_empty() {
        // Either the server ignored `verbose_json`, or every sub-segment was
        // noise. Fall back to the flat text so real speech is never lost to a
        // missing field.
        if let Some(seg) = collapse_to_segment(u, result, requested) {
            out.push(seg);
        }
    }

    out.sort_by(|a, b| {
        a.start_time
            .partial_cmp(&b.start_time)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    out
}

// ---------------------------------------------------------------------------
// Language normalization  (SPEC.md §6.3 landmine)
// ---------------------------------------------------------------------------

/// Full English language names -> ISO-639-1. Covers what this stack actually
/// sees (English, Indonesian, Arabic) plus whisper's common detections.
const LANGUAGE_NAMES: &[(&str, &str)] = &[
    ("english", "en"),
    ("indonesian", "id"),
    ("bahasa indonesia", "id"),
    ("bahasa", "id"),
    ("malay", "ms"),
    ("arabic", "ar"),
    ("urdu", "ur"),
    ("hindi", "hi"),
    ("bengali", "bn"),
    ("french", "fr"),
    ("german", "de"),
    ("spanish", "es"),
    ("castilian", "es"),
    ("portuguese", "pt"),
    ("italian", "it"),
    ("dutch", "nl"),
    ("flemish", "nl"),
    ("russian", "ru"),
    ("ukrainian", "uk"),
    ("polish", "pl"),
    ("turkish", "tr"),
    ("persian", "fa"),
    ("farsi", "fa"),
    ("hebrew", "he"),
    ("chinese", "zh"),
    ("mandarin", "zh"),
    ("cantonese", "yue"),
    ("japanese", "ja"),
    ("korean", "ko"),
    ("vietnamese", "vi"),
    ("thai", "th"),
    ("tagalog", "tl"),
    ("filipino", "tl"),
    ("swahili", "sw"),
    ("hausa", "ha"),
    ("tamil", "ta"),
    ("telugu", "te"),
    ("marathi", "mr"),
    ("punjabi", "pa"),
    ("gujarati", "gu"),
    ("javanese", "jv"),
    ("sundanese", "su"),
    ("greek", "el"),
    ("czech", "cs"),
    ("slovak", "sk"),
    ("swedish", "sv"),
    ("norwegian", "no"),
    ("nynorsk", "nn"),
    ("danish", "da"),
    ("finnish", "fi"),
    ("hungarian", "hu"),
    ("romanian", "ro"),
    ("bulgarian", "bg"),
    ("croatian", "hr"),
    ("serbian", "sr"),
    ("slovenian", "sl"),
    ("catalan", "ca"),
    ("basque", "eu"),
    ("galician", "gl"),
    ("latin", "la"),
    ("welsh", "cy"),
    ("icelandic", "is"),
    ("estonian", "et"),
    ("latvian", "lv"),
    ("lithuanian", "lt"),
    ("azerbaijani", "az"),
    ("kazakh", "kk"),
    ("uzbek", "uz"),
    ("armenian", "hy"),
    ("georgian", "ka"),
    ("nepali", "ne"),
    ("sinhala", "si"),
    ("khmer", "km"),
    ("lao", "lo"),
    ("burmese", "my"),
    ("myanmar", "my"),
    ("mongolian", "mn"),
    ("amharic", "am"),
    ("somali", "so"),
    ("yoruba", "yo"),
    ("afrikaans", "af"),
    ("albanian", "sq"),
    ("macedonian", "mk"),
    ("bosnian", "bs"),
    ("maltese", "mt"),
    ("haitian creole", "ht"),
    ("hawaiian", "haw"),
    ("maori", "mi"),
    ("occitan", "oc"),
    ("breton", "br"),
    ("belarusian", "be"),
    ("yiddish", "yi"),
    ("pashto", "ps"),
    ("kannada", "kn"),
    ("malayalam", "ml"),
    ("assamese", "as"),
    ("sanskrit", "sa"),
    ("tibetan", "bo"),
    ("turkmen", "tk"),
    ("tatar", "tt"),
    ("bashkir", "ba"),
    ("faroese", "fo"),
    ("luxembourgish", "lb"),
    ("shona", "sn"),
    ("sindhi", "sd"),
];

/// ISO-639-2/T (and a few -2/B) three-letter codes -> ISO-639-1.
const ISO3_TO_ISO1: &[(&str, &str)] = &[
    ("eng", "en"),
    ("ind", "id"),
    ("ara", "ar"),
    ("msa", "ms"),
    ("may", "ms"),
    ("urd", "ur"),
    ("hin", "hi"),
    ("ben", "bn"),
    ("fra", "fr"),
    ("fre", "fr"),
    ("deu", "de"),
    ("ger", "de"),
    ("spa", "es"),
    ("por", "pt"),
    ("ita", "it"),
    ("nld", "nl"),
    ("dut", "nl"),
    ("rus", "ru"),
    ("ukr", "uk"),
    ("pol", "pl"),
    ("tur", "tr"),
    ("fas", "fa"),
    ("per", "fa"),
    ("heb", "he"),
    ("zho", "zh"),
    ("chi", "zh"),
    ("jpn", "ja"),
    ("kor", "ko"),
    ("vie", "vi"),
    ("tha", "th"),
    ("tgl", "tl"),
    ("swa", "sw"),
    ("tam", "ta"),
    ("tel", "te"),
    ("jav", "jv"),
    ("sun", "su"),
    ("ell", "el"),
    ("gre", "el"),
];

/// Every ISO-639-1 code we accept verbatim. Restricting the pass-through to a
/// known set is what stops `"xx"` or a truncated word from being persisted as
/// a language.
const ISO1_CODES: &[&str] = &[
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az", "ba", "be", "bg", "bh",
    "bi", "bm", "bn", "bo", "br", "bs", "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv", "cy", "da",
    "de", "dv", "dz", "ee", "el", "en", "eo", "es", "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr",
    "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "he", "hi", "ho", "hr", "ht", "hu", "hy", "hz",
    "ia", "id", "ie", "ig", "ii", "ik", "io", "is", "it", "iu", "ja", "jv", "ka", "kg", "ki", "kj",
    "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li", "ln",
    "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "na", "nb",
    "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv", "ny", "oc", "oj", "om", "or", "os", "pa", "pi",
    "pl", "ps", "pt", "qu", "rm", "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk",
    "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti",
    "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw", "ty", "ug", "uk", "ur", "uz", "ve", "vi", "vo",
    "wa", "wo", "xh", "yi", "yo", "za", "zh", "zu",
];

/// Non-ISO-639-1 codes whisper emits that are still worth keeping.
const EXTRA_CODES: &[&str] = &["yue", "haw", "nan", "hak"];

/// LANDMINE (vexa_bots.py:484-488): whisper-server returns the language as a
/// full English name ("english"). Vexa's validator rejected that and silently
/// saved zero segments. Always map to ISO-639-1 before persisting.
/// "english" -> "en", "indonesian" -> "id", "arabic" -> "ar", ...;
/// already-ISO input passes through; unknown input returns None.
pub fn normalize_language(raw: &str) -> Option<String> {
    let lowered = raw.trim().to_ascii_lowercase();
    if lowered.is_empty() {
        return None;
    }
    // Whisper reports these for a failed or skipped detection.
    if matches!(lowered.as_str(), "auto" | "unknown" | "none" | "null" | "n/a") {
        return None;
    }

    // Locale tags and underscore variants: "en-US", "zh_CN", "en_us".
    let primary = lowered
        .split(['-', '_'])
        .next()
        .unwrap_or(&lowered)
        .to_string();

    if ISO1_CODES.contains(&primary.as_str()) {
        return Some(primary);
    }
    if EXTRA_CODES.contains(&lowered.as_str()) {
        return Some(lowered);
    }
    if let Some((_, iso1)) = ISO3_TO_ISO1.iter().find(|(k, _)| *k == primary.as_str()) {
        return Some((*iso1).to_string());
    }

    // Full names: on the whole string (some carry a space, "haitian creole")
    // and on the part before a parenthetical ("english (united states)").
    let name = lowered
        .split('(')
        .next()
        .unwrap_or(&lowered)
        .trim()
        .to_string();
    if let Some((_, iso1)) = LANGUAGE_NAMES.iter().find(|(k, _)| *k == name.as_str()) {
        return Some((*iso1).to_string());
    }
    if let Some((_, iso1)) = LANGUAGE_NAMES.iter().find(|(k, _)| *k == lowered.as_str()) {
        return Some((*iso1).to_string());
    }

    tracing::debug!(raw = %raw, "unrecognized language from whisper, storing null");
    None
}

// ---------------------------------------------------------------------------
// Hallucination filter
// ---------------------------------------------------------------------------

/// Phrases whisper emits on silence regardless of clip length. These are the
/// caption-corpus artifacts baked into the model.
const ALWAYS_NOISE: &[&str] = &[
    "",
    "(silence)",
    "[silence]",
    "[blank_audio]",
    "(blank_audio)",
    "[inaudible]",
    "(inaudible)",
    "[music]",
    "(music)",
    "[applause]",
    "(applause)",
    "[background noise]",
    "(background noise)",
    "[no audio]",
    "(no audio)",
    "[sound]",
    "(sound)",
    "thanks for watching!",
    "thanks for watching.",
    "thank you for watching!",
    "thank you for watching.",
    "subscribe to my channel",
    "please subscribe",
    "terima kasih telah menonton",
    "terima kasih telah menonton.",
];

/// Short filler that is only noise on a short clip; on a long one it is
/// plausibly a real, terse utterance and is kept.
const SHORT_CLIP_NOISE: &[&str] = &[
    "you",
    "you.",
    "thank you",
    "thank you.",
    "thanks",
    "thanks.",
    "bye",
    "bye.",
    "okay",
    "okay.",
    "ok",
    "ok.",
    "uh",
    "uh.",
    "um",
    "um.",
    "hmm",
    "hmm.",
    "mm",
    "mm-hmm",
    "yeah",
    "yeah.",
    "so",
    "so.",
    "oh",
    "oh.",
    "ya",
    "ya.",
    "terima kasih",
    "terima kasih.",
];

/// Below this many seconds, [`SHORT_CLIP_NOISE`] entries are dropped.
const SHORT_CLIP_SEC: f64 = 1.5;

/// Blank text, "", "(silence)", "[BLANK_AUDIO]", "you", "Thank you." on a
/// sub-second clip, and similar whisper hallucinations on silence.
pub fn is_noise_transcript(text: &str, duration_sec: f64) -> bool {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return true;
    }

    let lowered = trimmed.to_ascii_lowercase();
    if ALWAYS_NOISE.contains(&lowered.as_str()) {
        return true;
    }

    // Punctuation-only output: ".", "...", "♪♪", "- -".
    if !lowered.chars().any(|c| c.is_alphanumeric()) {
        return true;
    }

    // A whole utterance that is a single bracketed sound tag carries no speech:
    // "[wind blowing]", "(engine noise)".
    let wrapped = (lowered.starts_with('[') && lowered.ends_with(']'))
        || (lowered.starts_with('(') && lowered.ends_with(')'));
    if wrapped {
        let inner = &lowered[1..lowered.len() - 1];
        if !inner.contains('[') && !inner.contains('(') {
            return true;
        }
    }

    if duration_sec < SHORT_CLIP_SEC && SHORT_CLIP_NOISE.contains(&lowered.as_str()) {
        return true;
    }

    false
}

// ---------------------------------------------------------------------------
// Worker
// ---------------------------------------------------------------------------

/// Consecutive per-utterance failures that trigger the single health probe.
///
/// Two, not one: a lone 5xx on a big chunk is ordinary, but two in a row while
/// the room is still talking is the signature of an outage rather than of one
/// unlucky clip.
const HEALTH_PROBE_AFTER_FAILURES: usize = 2;

/// What [`run_transcriber`] reports back.
///
/// The counts exist because "0 segments" is ambiguous on its own: a silent
/// meeting and a total ASR outage both produce it, and only one of them is a
/// real meeting quietly disappearing. `whisper_down` and `abandoned` are what
/// let `session::drive` tell the two apart instead of laundering the outage
/// into a green `completed` (SPEC §0.1 / §8).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct TranscriberOutcome {
    /// Segments actually committed to the DB.
    pub inserted: usize,
    /// Utterances pulled off the channel.
    pub seen: usize,
    /// Utterances lost to an exhausted retry budget or a failed DB write.
    pub dropped: usize,
    /// Backlog discarded untranscribed after whisper was confirmed down.
    pub abandoned: usize,
    /// A health probe confirmed whisper unreachable while work was pending.
    pub whisper_down: bool,
}

impl TranscriberOutcome {
    /// Utterances that produced no persisted segment because something broke.
    pub fn lost(&self) -> usize {
        self.dropped + self.abandoned
    }

    /// Share of utterances lost to errors, in `0.0..=1.0`. `0.0` when nothing
    /// was ever seen (a genuinely silent meeting lost nothing).
    pub fn loss_ratio(&self) -> f64 {
        if self.seen == 0 {
            0.0
        } else {
            self.lost() as f64 / self.seen as f64
        }
    }
}

/// Consumes utterances, transcribes, inserts segments. Retries each utterance
/// up to `max_retries` (3) with exponential backoff on `Unreachable`/5xx;
/// on final failure it logs and DROPS that utterance — a dead whisper must
/// never abort the session (§0.1).
///
/// **Backlog short-circuit.** Dropping utterances one at a time is only cheap
/// while the failures are isolated. Against a whisper that is simply gone, each
/// utterance still costs `max_retries` attempts plus backoff, and the 64-deep
/// channel can be full at the end of a call — serially that is hours of
/// finalization with the meeting row pinned in `finalizing`, well past
/// `SHUTDOWN_GRACE`, i.e. a SIGKILL that takes the whole transcript with it.
/// So after [`HEALTH_PROBE_AFTER_FAILURES`] consecutive failures one health
/// probe is run; if it says whisper is unreachable the remaining backlog is
/// drained without being transcribed and counted in `abandoned`. Everything
/// already inserted stays inserted — the DB writes happen per utterance, so
/// giving up never rolls back transcribed work.
pub async fn run_transcriber(
    client: Arc<WhisperClient>,
    mut utterances: mpsc::Receiver<Utterance>,
    db: Db,
    meeting_id: Uuid,
    language: Option<String>,
    max_retries: u32,
) -> anyhow::Result<TranscriberOutcome> {
    let lang = language.as_deref();
    let mut out = TranscriberOutcome::default();
    let mut consecutive_failures = 0usize;
    let mut probed = false;

    while let Some(utterance) = utterances.recv().await {
        out.seen += 1;

        let segments = match client
            .transcribe_utterance_segments(&utterance, lang, max_retries)
            .await
        {
            Ok(segs) => {
                consecutive_failures = 0;
                probed = false;
                segs
            }
            Err(err) => {
                // Deliberately swallowed. Losing one utterance is survivable;
                // aborting turns a recoverable ASR outage into a false `failed`
                // meeting (SPEC §0.1). The count is what makes the loss visible.
                out.dropped += 1;
                consecutive_failures += 1;
                tracing::error!(
                    %meeting_id,
                    start = utterance.start_time,
                    end = utterance.end_time,
                    error = %err,
                    "dropping utterance after exhausting whisper retries"
                );

                if consecutive_failures >= HEALTH_PROBE_AFTER_FAILURES && !probed {
                    // Exactly one probe per outage: it is a network round trip
                    // on a path that has just proven itself slow.
                    probed = true;
                    if !client.health().await {
                        out.whisper_down = true;
                        tracing::error!(
                            %meeting_id,
                            endpoint = %client.active_endpoint(),
                            inserted = out.inserted,
                            "whisper confirmed down; abandoning the remaining backlog"
                        );
                        break;
                    }
                }
                continue;
            }
        };

        if segments.is_empty() {
            tracing::debug!(
                %meeting_id,
                start = utterance.start_time,
                "utterance produced no speech (noise or blank transcript)"
            );
            continue;
        }

        // `Db` is synchronous and sub-millisecond by contract (SPEC §3).
        match db.insert_segments(meeting_id, &segments) {
            Ok(n) => out.inserted += n,
            Err(e) => {
                // A DB write failure is not the session's problem either; keep
                // draining so the channel closes and finalization can proceed.
                out.dropped += 1;
                tracing::error!(
                    %meeting_id,
                    error = %e,
                    "failed to insert segments; continuing"
                );
            }
        }
    }

    if out.whisper_down {
        // Drain, do not transcribe: the sender must still see the channel
        // emptied so the segmenter and `drive` can finish.
        while utterances.recv().await.is_some() {
            out.seen += 1;
            out.abandoned += 1;
        }
    }

    tracing::info!(
        %meeting_id,
        utterances = out.seen,
        segments = out.inserted,
        dropped = out.dropped,
        abandoned = out.abandoned,
        whisper_down = out.whisper_down,
        "transcriber finished"
    );
    Ok(out)
}

/// Standalone liveness check against an arbitrary endpoint, for `GET /health`
/// callers that do not hold a [`WhisperClient`]. Any HTTP response means up.
pub async fn health_check(http: &reqwest::Client, endpoint: &str) -> bool {
    WhisperClient::new(http.clone(), endpoint).health().await
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_default_gateway_from_show_default() {
        let out = "default via 172.25.32.1 dev eth0 proto kernel\n";
        assert_eq!(parse_default_gateway(out).as_deref(), Some("172.25.32.1"));
    }

    #[test]
    fn parses_default_gateway_from_full_table() {
        let out = "\
10.0.0.0/8 dev eth1 scope link
default via 192.168.1.1 dev eth0 proto dhcp metric 100
172.25.32.0/20 dev eth0 proto kernel scope link src 172.25.44.2
";
        assert_eq!(parse_default_gateway(out).as_deref(), Some("192.168.1.1"));
    }

    #[test]
    fn no_default_route_yields_none() {
        assert!(parse_default_gateway("10.0.0.0/8 dev eth1 scope link\n").is_none());
        assert!(parse_default_gateway("").is_none());
        assert!(parse_default_gateway("default dev eth0 scope link").is_none());
    }

    #[test]
    fn gateway_ip_never_panics_and_is_non_empty() {
        let gw = gateway_ip();
        assert!(!gw.is_empty());
        invalidate_gateway_cache();
    }

    #[test]
    fn endpoint_parts_roundtrip() {
        let p = EndpointParts::parse("http://172.25.32.1:8083/v1/audio/transcriptions").unwrap();
        assert_eq!(p.scheme, "http");
        assert_eq!(p.host, "172.25.32.1");
        assert_eq!(p.port, Some(8083));
        assert_eq!(p.path, "/v1/audio/transcriptions");
        assert_eq!(p.to_url(), "http://172.25.32.1:8083/v1/audio/transcriptions");
        assert_eq!(p.origin(), "http://172.25.32.1:8083/");
        assert_eq!(
            p.with_host("172.30.0.1").to_url(),
            "http://172.30.0.1:8083/v1/audio/transcriptions"
        );
    }

    #[test]
    fn endpoint_parts_without_port_or_path() {
        let p = EndpointParts::parse("http://whisper.local").unwrap();
        assert_eq!(p.host, "whisper.local");
        assert_eq!(p.port, None);
        assert_eq!(p.path, "");
        assert_eq!(p.origin(), "http://whisper.local/");
        assert!(EndpointParts::parse("not a url").is_none());
    }

    #[test]
    fn only_private_ipv4_hosts_are_reresolvable() {
        assert!(host_is_reresolvable("172.25.32.1"));
        assert!(host_is_reresolvable("192.168.1.1"));
        assert!(host_is_reresolvable("10.7.0.1"));
        assert!(!host_is_reresolvable("127.0.0.1"));
        assert!(!host_is_reresolvable("8.8.8.8"));
        assert!(!host_is_reresolvable("whisper.local"));
        assert!(!host_is_reresolvable("172.400.1.1"));
    }

    #[test]
    fn client_reports_configured_endpoint() {
        let c = WhisperClient::new(
            reqwest::Client::new(),
            "http://172.25.32.1:8083/v1/audio/transcriptions",
        );
        assert_eq!(c.endpoint(), "http://172.25.32.1:8083/v1/audio/transcriptions");
        assert_eq!(c.active_endpoint(), c.endpoint());
    }

    #[test]
    fn explicit_hostname_is_never_repointed() {
        let c = WhisperClient::new(
            reqwest::Client::new(),
            "http://whisper.local:8083/v1/audio/transcriptions",
        );
        let after = c.refresh_gateway();
        assert_eq!(after, "http://whisper.local:8083/v1/audio/transcriptions");
    }

    #[test]
    fn language_full_names_map_to_iso1() {
        assert_eq!(normalize_language("english").as_deref(), Some("en"));
        assert_eq!(normalize_language("English").as_deref(), Some("en"));
        assert_eq!(normalize_language("  ENGLISH  ").as_deref(), Some("en"));
        assert_eq!(normalize_language("indonesian").as_deref(), Some("id"));
        assert_eq!(normalize_language("Bahasa Indonesia").as_deref(), Some("id"));
        assert_eq!(normalize_language("arabic").as_deref(), Some("ar"));
        assert_eq!(
            normalize_language("English (United States)").as_deref(),
            Some("en")
        );
    }

    #[test]
    fn language_iso_codes_pass_through() {
        assert_eq!(normalize_language("en").as_deref(), Some("en"));
        assert_eq!(normalize_language("EN").as_deref(), Some("en"));
        assert_eq!(normalize_language("en-US").as_deref(), Some("en"));
        assert_eq!(normalize_language("zh_CN").as_deref(), Some("zh"));
        assert_eq!(normalize_language("eng").as_deref(), Some("en"));
        assert_eq!(normalize_language("ind").as_deref(), Some("id"));
        assert_eq!(normalize_language("yue").as_deref(), Some("yue"));
    }

    #[test]
    fn language_unknown_is_none() {
        assert!(normalize_language("").is_none());
        assert!(normalize_language("   ").is_none());
        assert!(normalize_language("auto").is_none());
        assert!(normalize_language("unknown").is_none());
        assert!(normalize_language("klingon").is_none());
        assert!(normalize_language("xx").is_none());
    }

    #[test]
    fn noise_filter_catches_artifacts() {
        assert!(is_noise_transcript("", 5.0));
        assert!(is_noise_transcript("   ", 5.0));
        assert!(is_noise_transcript("[BLANK_AUDIO]", 5.0));
        assert!(is_noise_transcript("(silence)", 5.0));
        assert!(is_noise_transcript("[Music]", 5.0));
        assert!(is_noise_transcript("[wind blowing]", 5.0));
        assert!(is_noise_transcript("...", 5.0));
        assert!(is_noise_transcript("♪♪", 5.0));
        assert!(is_noise_transcript("Thanks for watching!", 5.0));
    }

    #[test]
    fn short_filler_is_noise_only_on_short_clips() {
        assert!(is_noise_transcript("you", 0.4));
        assert!(is_noise_transcript("Thank you.", 0.9));
        assert!(!is_noise_transcript("Thank you.", 3.0));
        assert!(!is_noise_transcript("Sure, PIM sync is done.", 0.4));
    }

    #[test]
    fn parses_verbose_json() {
        let body = r#"{
            "task": "transcribe",
            "language": "english",
            "duration": 4.2,
            "text": "Let's start with the seller portal.",
            "segments": [
                {"id": 0, "start": 0.0, "end": 2.1, "text": " Let's start"},
                {"id": 1, "start": 2.1, "end": 4.2, "text": " with the seller portal."}
            ]
        }"#;
        let r = parse_transcription_body(body).unwrap();
        assert_eq!(r.text, "Let's start with the seller portal.");
        assert_eq!(r.language.as_deref(), Some("en"));
        assert_eq!(r.segments.len(), 2);
        assert_eq!(r.segments[1].start, Some(2.1));
    }

    #[test]
    fn parses_plain_json_without_segments() {
        let r = parse_transcription_body(r#"{"text":"hello there"}"#).unwrap();
        assert_eq!(r.text, "hello there");
        assert!(r.language.is_none());
        assert!(r.segments.is_empty());
    }

    #[test]
    fn parses_segments_only_response() {
        let body = r#"{"segments":[{"start":0.0,"end":1.0,"text":"one"},
                                    {"start":1.0,"end":2.0,"text":"two"}]}"#;
        let r = parse_transcription_body(body).unwrap();
        assert_eq!(r.text, "one two");
    }

    #[test]
    fn parses_bare_string_and_plain_text() {
        assert_eq!(parse_transcription_body("\"hi\"").unwrap().text, "hi");
        assert_eq!(parse_transcription_body("hi there").unwrap().text, "hi there");
        assert_eq!(parse_transcription_body("   ").unwrap().text, "");
    }

    #[test]
    fn rejects_markup_and_wrapped_errors() {
        assert!(parse_transcription_body("<html>502</html>").is_err());
        assert!(parse_transcription_body(r#"{"error":{"message":"model not loaded"}}"#).is_err());
    }

    #[test]
    fn backoff_is_bounded() {
        assert_eq!(backoff_delay(0), Duration::from_millis(500));
        assert_eq!(backoff_delay(1), Duration::from_millis(1000));
        assert_eq!(backoff_delay(3), Duration::from_millis(4000));
        assert_eq!(backoff_delay(20), RETRY_MAX_DELAY);
    }

    #[test]
    fn retryability_matches_spec() {
        assert!(
            WhisperError::Http {
                status: 503,
                body: "x".into()
            }
            .is_retryable()
        );
        assert!(
            WhisperError::Http {
                status: 429,
                body: "x".into()
            }
            .is_retryable()
        );
        assert!(
            !WhisperError::Http {
                status: 400,
                body: "x".into()
            }
            .is_retryable()
        );
        assert!(!WhisperError::Decode("bad".into()).is_retryable());
    }

    #[test]
    fn truncate_is_char_safe() {
        assert_eq!(truncate("abc", 10), "abc");
        assert_eq!(truncate("äöüß", 2), "äö…");
    }

    // -----------------------------------------------------------------------
    // run_transcriber / outage accounting
    // -----------------------------------------------------------------------

    fn outcome(seen: usize, dropped: usize, abandoned: usize) -> TranscriberOutcome {
        TranscriberOutcome {
            seen,
            dropped,
            abandoned,
            ..TranscriberOutcome::default()
        }
    }

    #[test]
    fn loss_ratio_is_zero_for_a_silent_meeting() {
        // Nothing was ever spoken, so nothing was lost. This must not read as
        // a total outage — it is the load-bearing `skipped_not_admitted` path.
        assert_eq!(TranscriberOutcome::default().loss_ratio(), 0.0);
        assert_eq!(TranscriberOutcome::default().lost(), 0);
    }

    #[test]
    fn loss_ratio_counts_dropped_and_abandoned() {
        let o = outcome(10, 2, 3);
        assert_eq!(o.lost(), 5);
        assert!((o.loss_ratio() - 0.5).abs() < f64::EPSILON);
        assert_eq!(outcome(4, 0, 4).loss_ratio(), 1.0);
    }

    /// A port nothing is listening on, so every connect is refused instantly.
    fn dead_port() -> u16 {
        let l = std::net::TcpListener::bind("127.0.0.1:0").expect("bind ephemeral");
        let port = l.local_addr().expect("addr").port();
        drop(l);
        port
    }

    fn test_utterance(i: usize) -> Utterance {
        Utterance {
            // 0.5 s of non-silent PCM so `to_wav_bytes` has something to encode.
            pcm: vec![1200i16; (crate::audio::SAMPLE_RATE / 2) as usize],
            start_time: i as f64,
            end_time: i as f64 + 0.5,
            speaker: Some("Tester".to_string()),
        }
    }

    fn test_meeting(db: &Db) -> Uuid {
        let rec = db
            .create_meeting(&crate::db::NewMeeting {
                key: crate::state::MeetingKey::new(
                    crate::state::Platform::GoogleMeet,
                    "abc-defg-hij",
                ),
                title: None,
                bot_name: "Notetaker".to_string(),
                language: None,
                passcode: None,
                recording_enabled: false,
                transcribe_enabled: true,
            })
            .expect("create meeting");
        rec.id
    }

    /// Regression for the unbounded-finalization finding: with whisper gone, a
    /// full backlog must NOT be walked utterance by utterance (retries plus
    /// backoff, serially — hours in the worst case). One health probe settles it
    /// and the rest is abandoned.
    #[tokio::test]
    async fn dead_whisper_short_circuits_the_backlog_instead_of_grinding_through_it() {
        let endpoint = format!("http://127.0.0.1:{}/v1/audio/transcriptions", dead_port());
        let client = Arc::new(WhisperClient::new(reqwest::Client::new(), endpoint));
        let db = Db::open_in_memory().expect("db");
        let meeting_id = test_meeting(&db);

        let (tx, rx) = mpsc::channel(64);
        for i in 0..24 {
            tx.send(test_utterance(i)).await.expect("queue utterance");
        }
        drop(tx);

        let started = std::time::Instant::now();
        let out = tokio::time::timeout(
            Duration::from_secs(30),
            // max_retries = 0: the point under test is the backlog, not backoff.
            run_transcriber(client, rx, db.clone(), meeting_id, None, 0),
        )
        .await
        .expect("run_transcriber must not hang on a dead whisper")
        .expect("run_transcriber never errors out");

        assert!(out.whisper_down, "the outage must be reported, not hidden");
        assert_eq!(out.seen, 24, "every utterance is accounted for");
        assert_eq!(out.inserted, 0);
        assert!(
            out.abandoned >= 20,
            "the backlog must be abandoned wholesale, not retried one by one: {out:?}"
        );
        assert!(
            out.dropped <= HEALTH_PROBE_AFTER_FAILURES,
            "at most the probe threshold is paid before short-circuiting: {out:?}"
        );
        assert_eq!(out.loss_ratio(), 1.0);
        assert_eq!(db.count_segments(meeting_id).expect("count"), 0);
        assert!(
            started.elapsed() < Duration::from_secs(20),
            "short-circuit must be fast, took {:?}",
            started.elapsed()
        );
    }

    /// The empty-channel case is the silent-meeting path: no work, no outage,
    /// no alarm.
    #[tokio::test]
    async fn silent_meeting_reports_no_loss_and_no_outage() {
        let endpoint = format!("http://127.0.0.1:{}/v1/audio/transcriptions", dead_port());
        let client = Arc::new(WhisperClient::new(reqwest::Client::new(), endpoint));
        let db = Db::open_in_memory().expect("db");
        let meeting_id = test_meeting(&db);

        let (tx, rx) = mpsc::channel::<Utterance>(8);
        drop(tx);

        let out = run_transcriber(client, rx, db, meeting_id, None, 0)
            .await
            .expect("ok");
        assert_eq!(out, TranscriberOutcome::default());
        assert!(!out.whisper_down);
    }
}
