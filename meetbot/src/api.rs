//! axum HTTP surface: the Vexa-compatible endpoints the Python client calls,
//! plus `/health` and `/bots/status`.
//!
//! Contract: `SPEC.md` §9 (wire shapes in §1). Owner: the `api` builder agent.
//!
//! Two semantics here are load-bearing for `vexa_bots.py` and must not drift:
//!
//! * `GET /transcripts/{platform}/{id}` 404s **only** when no meeting row has
//!   ever existed for that key. That is the client's zombie guard (line 528):
//!   `bot_sent` + 404 + `sent_at` older than 3 h => `failed_not_found`. Once
//!   `POST /bots` has returned 201 for a key, this route must never 404 again.
//! * `POST /bots` over the concurrency ceiling returns **403** with the exact
//!   Vexa wording `maximum concurrent bot limit (N)`; the client surfaces that
//!   string verbatim in the operator's heartbeat.

use std::collections::HashMap;

use axum::Router;
use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::routing::{delete, get, post};
use chrono::{DateTime, SecondsFormat, Utc};
use serde::{Deserialize, Serialize};

use crate::db::Segment;
use crate::state::SharedState;

/// Header carrying the per-user API key (`config.api_key`).
const API_KEY_HEADER: &str = "x-api-key";
/// Header carrying the admin key (`config.admin_token`).
const ADMIN_KEY_HEADER: &str = "x-admin-api-key";

// ---------------------------------------------------------------------------
// Wire types
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct CreateBotRequest {
    pub platform: String,
    pub native_meeting_id: String,
    #[serde(default)]
    pub bot_name: Option<String>,
    #[serde(default)]
    pub language: Option<String>,
    #[serde(default)]
    pub passcode: Option<String>,
    #[serde(default)]
    pub recording_enabled: Option<bool>,
    #[serde(default)]
    pub transcribe_enabled: Option<bool>,
    /// meetbot extension; the Python client never sends it.
    #[serde(default)]
    pub title: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct CreateBotResponse {
    pub id: String,
    pub platform: String,
    pub native_meeting_id: String,
    pub constructed_meeting_url: String,
    pub bot_name: String,
    pub status: String,
    pub created_at: String,
}

#[derive(Debug, Serialize)]
pub struct StopBotResponse {
    pub id: String,
    pub platform: String,
    pub native_meeting_id: String,
    /// Always `"stopping"`; the session finalizes asynchronously.
    pub status: String,
}

#[derive(Debug, Serialize)]
pub struct TranscriptSegment {
    /// Elapsed **seconds** from meeting start, never a timestamp — the client
    /// runs `divmod(int(seconds), 60)` on it (`fmt_ts`).
    pub start_time: f64,
    pub end_time: f64,
    pub speaker: Option<String>,
    pub text: String,
    pub language: Option<String>,
}

impl From<Segment> for TranscriptSegment {
    fn from(s: Segment) -> Self {
        TranscriptSegment {
            start_time: s.start_time,
            end_time: s.end_time,
            speaker: s.speaker,
            text: s.text,
            language: s.language,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct TranscriptResponse {
    pub id: String,
    pub platform: String,
    pub native_meeting_id: String,
    pub constructed_meeting_url: Option<String>,
    pub status: String,
    /// RFC3339 UTC with a trailing "Z", or null. NEVER a non-UTC offset.
    pub start_time: Option<String>,
    pub end_time: Option<String>,
    /// Always present, `[]` when empty. Never null.
    pub segments: Vec<TranscriptSegment>,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub detail: String,
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("invalid api key")]
    Unauthorized,
    #[error("{0}")]
    BadRequest(String),
    #[error("{0}")]
    NotFound(String),
    #[error("{0}")]
    Conflict(String),
    #[error("maximum concurrent bot limit ({0})")]
    TooManyBots(usize),
    #[error("{0}")]
    Unavailable(String),
    #[error("{0}")]
    Internal(String),
}

impl ApiError {
    pub fn status(&self) -> StatusCode {
        match self {
            ApiError::Unauthorized => StatusCode::UNAUTHORIZED,
            ApiError::BadRequest(_) => StatusCode::BAD_REQUEST,
            ApiError::NotFound(_) => StatusCode::NOT_FOUND,
            ApiError::Conflict(_) => StatusCode::CONFLICT,
            ApiError::TooManyBots(_) => StatusCode::FORBIDDEN,
            ApiError::Unavailable(_) => StatusCode::SERVICE_UNAVAILABLE,
            ApiError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> axum::response::Response {
        let status = self.status();
        let detail = self.to_string();
        if status.is_server_error() {
            tracing::error!(%status, %detail, "api error");
        } else {
            tracing::debug!(%status, %detail, "api rejection");
        }
        (status, axum::Json(ErrorResponse { detail })).into_response()
    }
}

// ---------------------------------------------------------------------------
// Router / server
// ---------------------------------------------------------------------------

/// GET /, GET /health, GET /bots/status,
/// POST /bots, DELETE /bots/{platform}/{native_id},
/// GET /transcripts/{platform}/{native_id},
/// POST /admin/users, POST /admin/users/{uid}/tokens
pub fn router(state: SharedState) -> Router {
    Router::new()
        .route("/", get(root))
        .route("/health", get(health))
        .route("/bots", post(create_bot))
        .route("/bots/status", get(bots_status))
        .route("/bots/{platform}/{native_id}", delete(stop_bot))
        .route("/transcripts/{platform}/{native_id}", get(get_transcript))
        .route("/admin/users", post(admin_create_user))
        .route("/admin/users/{uid}/tokens", post(admin_create_token))
        .with_state(state)
}

/// Binds `cfg.http_bind:cfg.http_port` and serves until ctrl-c.
pub async fn serve(state: SharedState) -> anyhow::Result<()> {
    let addr = format!("{}:{}", state.cfg.http_bind, state.cfg.http_port);
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .map_err(|e| anyhow::anyhow!("failed to bind {addr}: {e}"))?;

    tracing::info!(%addr, "meetbot http listening");

    axum::serve(listener, router(state))
        .with_graceful_shutdown(shutdown_signal())
        .await
        .map_err(|e| anyhow::anyhow!("http server error: {e}"))
}

async fn shutdown_signal() {
    if let Err(e) = tokio::signal::ctrl_c().await {
        tracing::error!(error = %e, "failed to install ctrl-c handler");
        std::future::pending::<()>().await;
    }
    tracing::info!("shutdown signal received");
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

/// Liveness. No auth: the client probes this before it has a key (line 103),
/// and treats *any* HTTP response as "alive".
pub async fn root() -> impl IntoResponse {
    axum::Json(serde_json::json!({
        "service": "meetbot",
        "version": env!("CARGO_PKG_VERSION"),
        "status": "ok",
    }))
}

/// Dependency health. Always 200 — read the fields, not the status code.
pub async fn health(State(state): State<SharedState>) -> impl IntoResponse {
    let whisper_endpoint = state.whisper.endpoint().to_string();
    let whisper_up = state.whisper.health().await;
    let chromium_present = state.cfg.chromium_path.exists();
    let active = state.active_count().await;

    let status = if whisper_up && chromium_present {
        "ok"
    } else {
        "degraded"
    };

    axum::Json(serde_json::json!({
        "status": status,
        "whisper": { "reachable": whisper_up, "endpoint": whisper_endpoint },
        "chromium": {
            "path": state.cfg.chromium_path.display().to_string(),
            "present": chromium_present,
        },
        "active_bots": active,
        "max_concurrent_bots": state.cfg.max_concurrent_bots,
    }))
}

/// `POST /bots`. Order of operations is fixed by SPEC.md §9 so the 403/409
/// semantics stay stable: auth, parse, 409, 403, 503, insert, spawn.
pub async fn create_bot(
    State(state): State<SharedState>,
    headers: HeaderMap,
    axum::Json(body): axum::Json<CreateBotRequest>,
) -> Result<(StatusCode, axum::Json<CreateBotResponse>), ApiError> {
    // 1. auth
    check_api_key(&state, &headers)?;

    // 2. platform + native id
    let key = parse_key(&body.platform, &body.native_meeting_id)?;

    // NOTE (SPEC.md §1.3.1, v1.3): step 2b used to be a hard 400 for
    // `"platform": "teams"`. It is gone. Teams is now a supported join path —
    // `meet::MeetSession::join` dispatches to the Teams state machine and
    // `teams::selectors` — so `POST /bots` accepts it exactly like Google Meet
    // and every downstream check below applies unchanged. `parse_key` was never
    // touched by the gate, so DELETE and GET /transcripts keep addressing
    // historical Teams rows just as they did.

    // 3. one live bot per meeting
    if state
        .db
        .active_meeting(&key)
        .map_err(|e| ApiError::Internal(format!("db active_meeting failed: {e}")))?
        .is_some()
    {
        return Err(ApiError::Conflict(format!(
            "bot already active for {}",
            key.as_path()
        )));
    }

    // 4. concurrency ceiling -> 403 with Vexa's exact wording
    let permit = state
        .slots
        .clone()
        .try_acquire_owned()
        .map_err(|_| ApiError::TooManyBots(state.cfg.max_concurrent_bots))?;

    // 5. a transcribing bot with no whisper would produce an empty transcript
    let transcribe_enabled = body.transcribe_enabled.unwrap_or(true);
    let recording_enabled = body.recording_enabled.unwrap_or(false);
    if transcribe_enabled {
        let whisper_up = state.whisper.health().await;
        if let Err(e) = whisper_gate(
            state.cfg.require_whisper_for_bots,
            whisper_up,
            state.whisper.endpoint(),
        ) {
            drop(permit);
            return Err(e);
        }
    }

    let bot_name = non_empty(body.bot_name).unwrap_or_else(|| state.cfg.bot_name.clone());
    let language = non_empty(body.language);
    let passcode = non_empty(body.passcode);
    let title = non_empty(body.title);

    // 6. persist the row before anything can observe the session
    let new_meeting = crate::db::NewMeeting {
        key: key.clone(),
        title: title.clone(),
        bot_name: bot_name.clone(),
        language: language.clone(),
        passcode: passcode.clone(),
        recording_enabled,
        transcribe_enabled,
    };
    let record = state
        .db
        .create_meeting(&new_meeting)
        .map_err(|e| ApiError::Internal(format!("db create_meeting failed: {e}")))?;

    // 7. hand the permit to the session task
    let spec = crate::session::SessionSpec {
        meeting_id: record.id,
        key: key.clone(),
        title,
        bot_name: bot_name.clone(),
        language,
        passcode,
        recording_enabled,
        transcribe_enabled,
    };

    if let Err(e) = crate::session::spawn(state.clone(), spec, permit) {
        // The row exists and the client can poll it, so it must not stay
        // non-terminal: land it on `failed` immediately.
        let _ = state.db.set_status(
            record.id,
            crate::db::MeetingStatus::Failed,
            Some(&format!("failed to start session: {e}")),
        );
        return Err(ApiError::Internal(format!("failed to start session: {e}")));
    }

    tracing::info!(meeting_id = %record.id, key = %key, "bot requested");

    Ok((
        StatusCode::CREATED,
        axum::Json(CreateBotResponse {
            id: record.id.to_string(),
            platform: key.platform.as_str().to_string(),
            native_meeting_id: key.native_id.clone(),
            constructed_meeting_url: key.url(),
            bot_name,
            status: crate::db::MeetingStatus::Requested.as_str().to_string(),
            created_at: iso(record.created_at),
        }),
    ))
}

/// `DELETE /bots/{platform}/{native_id}` — ask the bot to leave.
pub async fn stop_bot(
    State(state): State<SharedState>,
    headers: HeaderMap,
    Path((platform, native_id)): Path<(String, String)>,
) -> Result<axum::Json<StopBotResponse>, ApiError> {
    check_api_key(&state, &headers)?;

    let not_found = || ApiError::NotFound(format!("no active bot for {platform}/{native_id}"));
    let key = parse_key(&platform, &native_id).map_err(|_| not_found())?;

    let handle = state.get_session(&key).await.ok_or_else(not_found)?;

    // Best effort: the task may be finalizing already, which is still a
    // successful stop from the caller's point of view.
    if let Err(e) = handle.stop().await {
        tracing::warn!(key = %key, error = %e, "stop command not delivered; session already ending");
    }

    Ok(axum::Json(StopBotResponse {
        id: handle.meeting_id.to_string(),
        platform: key.platform.as_str().to_string(),
        native_meeting_id: key.native_id.clone(),
        status: "stopping".to_string(),
    }))
}

/// `GET /transcripts/{platform}/{native_id}` — the money endpoint.
///
/// 404 here is the client's zombie guard, so it is returned **only** when no
/// row has ever existed for the key. Rows are permanent; there is no expiry.
pub async fn get_transcript(
    State(state): State<SharedState>,
    headers: HeaderMap,
    Path((platform, native_id)): Path<(String, String)>,
) -> Result<axum::Json<TranscriptResponse>, ApiError> {
    check_api_key(&state, &headers)?;

    let not_found = || ApiError::NotFound(format!("no meeting {platform}/{native_id}"));
    let key = parse_key(&platform, &native_id).map_err(|_| not_found())?;

    let record = state
        .db
        .latest_meeting(&key)
        .map_err(|e| ApiError::Internal(format!("db latest_meeting failed: {e}")))?
        .ok_or_else(not_found)?;

    let segments = state
        .db
        .get_segments(record.id)
        .map_err(|e| ApiError::Internal(format!("db get_segments failed: {e}")))?;

    Ok(axum::Json(TranscriptResponse {
        id: record.id.to_string(),
        platform: record.platform.as_str().to_string(),
        native_meeting_id: record.native_meeting_id.clone(),
        constructed_meeting_url: record
            .constructed_meeting_url
            .clone()
            .or_else(|| Some(key.url())),
        status: record.status.as_str().to_string(),
        start_time: record.start_time.map(iso),
        end_time: record.end_time.map(iso),
        segments: segments.into_iter().map(TranscriptSegment::from).collect(),
    }))
}

/// `GET /bots/status` — introspection (meetbot extension).
pub async fn bots_status(
    State(state): State<SharedState>,
    headers: HeaderMap,
) -> Result<axum::Json<serde_json::Value>, ApiError> {
    check_api_key(&state, &headers)?;

    let handles = state.list_sessions().await;
    let mut sessions = Vec::with_capacity(handles.len());

    for handle in &handles {
        let phase = handle.phase().await;
        let segment_count = state.db.count_segments(handle.meeting_id).unwrap_or(0);
        sessions.push(serde_json::json!({
            "id": handle.meeting_id.to_string(),
            "platform": handle.key.platform.as_str(),
            "native_meeting_id": handle.key.native_id,
            "title": handle.title,
            "phase": phase.as_str(),
            "started_at": iso(handle.started_at),
            "segment_count": segment_count,
        }));
    }

    Ok(axum::Json(serde_json::json!({
        "active_bots": handles.len(),
        "max_concurrent_bots": state.cfg.max_concurrent_bots,
        "sessions": sessions,
    })))
}

// --- admin compat (keeps `vexa_bots.py setup` working) ---------------------

#[derive(Debug, Deserialize)]
struct AdminUserRequest {
    #[serde(default)]
    email: Option<String>,
    #[serde(default)]
    name: Option<String>,
}

/// `POST /admin/users`. meetbot is single-tenant: the user is notional and
/// always id 1, but the shape has to match so `cmd_setup` can read `id`.
pub async fn admin_create_user(
    State(state): State<SharedState>,
    headers: HeaderMap,
    raw: String,
) -> Result<axum::Json<serde_json::Value>, ApiError> {
    check_admin_key(&state, &headers)?;

    let req: AdminUserRequest = if raw.trim().is_empty() {
        AdminUserRequest {
            email: None,
            name: None,
        }
    } else {
        serde_json::from_str(&raw)
            .map_err(|e| ApiError::BadRequest(format!("invalid json body: {e}")))?
    };

    Ok(axum::Json(serde_json::json!({
        "id": 1,
        "email": req.email,
        "name": req.name,
    })))
}

/// `POST /admin/users/{uid}/tokens?scopes=bot,tx,browser`.
/// meetbot does not mint keys; it returns the configured `api_key` so that
/// `setup` writes the right value into `vexa_token.env`. `scopes` is echoed
/// from the query string, unvalidated. The body is ignored.
pub async fn admin_create_token(
    State(state): State<SharedState>,
    headers: HeaderMap,
    Path(uid): Path<String>,
    Query(params): Query<HashMap<String, String>>,
    _body: String,
) -> Result<axum::Json<serde_json::Value>, ApiError> {
    check_admin_key(&state, &headers)?;

    let scopes: Vec<String> = params
        .get("scopes")
        .map(|s| {
            s.split(',')
                .map(str::trim)
                .filter(|p| !p.is_empty())
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();

    let user_id: i64 = uid.parse().unwrap_or(1);

    Ok(axum::Json(serde_json::json!({
        "token": state.api_key,
        "user_id": user_id,
        "scopes": scopes,
    })))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Constant-time compare of the `X-API-Key` header against `state.api_key`.
pub fn check_api_key(state: &SharedState, headers: &HeaderMap) -> Result<(), ApiError> {
    check_header_key(headers, API_KEY_HEADER, &state.api_key)
}

/// Same for `X-Admin-API-Key` against `state.cfg.admin_token`.
pub fn check_admin_key(state: &SharedState, headers: &HeaderMap) -> Result<(), ApiError> {
    check_header_key(headers, ADMIN_KEY_HEADER, &state.cfg.admin_token)
}

fn check_header_key(headers: &HeaderMap, header: &str, expected: &str) -> Result<(), ApiError> {
    let presented = headers
        .get(header)
        .and_then(|v| v.to_str().ok())
        .ok_or(ApiError::Unauthorized)?;

    if constant_time_eq(presented.as_bytes(), expected.as_bytes()) {
        Ok(())
    } else {
        Err(ApiError::Unauthorized)
    }
}

/// Length-leaking but content-constant-time byte comparison. Enough for an
/// API key check: the length of the configured key is not the secret.
fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

/// Step 5 of `create_bot`, factored out so the policy is testable without a
/// live `AppState`. Call only when `transcribe_enabled`.
///
/// SPEC.md §1.3.2 — deliberate deviation from Vexa, made configurable:
///
/// * `require_whisper = true` (**default**): unreachable whisper => 503. The
///   client records `send_failed` + a fail heartbeat, so a dead whisper is
///   loud. The cost is real: if whisper flaps between the client's own
///   `ensure_whisper()` probe and this POST, the meeting is not joined at all
///   and is MISSED, where Vexa would have joined and produced *something*.
/// * `require_whisper = false`: accept anyway. The bot joins and records; a
///   whisper that recovers mid-call still transcribes the rest, and a whisper
///   that never recovers yields `completed` with `segments: []` (SPEC.md §0.1),
///   which the client files as `skipped_not_admitted` — quiet, and easy to miss.
///
/// Default is fail-fast because a visible alarm beats a silent empty transcript.
pub fn whisper_gate(
    require_whisper: bool,
    whisper_up: bool,
    endpoint: &str,
) -> Result<(), ApiError> {
    if whisper_up {
        return Ok(());
    }
    if require_whisper {
        return Err(ApiError::Unavailable(format!(
            "transcription service unreachable at {endpoint}"
        )));
    }
    tracing::warn!(
        %endpoint,
        "whisper unreachable but require_whisper_for_bots=false; joining anyway \
         (transcript may be empty)"
    );
    Ok(())
}

/// Parses + validates the (platform, native_id) path pair -> `MeetingKey`.
///
/// Returns `BadRequest` (the 400 in SPEC.md §1.3). Path handlers remap it to
/// 404 so an unknown `{platform}` segment 404s per SPEC.md §1.
pub fn parse_key(platform: &str, native_id: &str) -> Result<crate::state::MeetingKey, ApiError> {
    let plat = crate::state::Platform::parse(platform.trim()).ok_or_else(|| {
        ApiError::BadRequest(format!(
            "unsupported platform: '{platform}' (expected google_meet or teams)"
        ))
    })?;

    let native = native_id.trim();
    if !plat.validate_native_id(native) {
        return Err(ApiError::BadRequest(format!(
            "invalid native_meeting_id for {plat}: '{native_id}'"
        )));
    }

    Ok(crate::state::MeetingKey::new(plat, native))
}

/// RFC3339 UTC, second precision, trailing `Z` — the only format the client's
/// `datetime.fromisoformat` can consume without shifting the meeting.
fn iso(ts: DateTime<Utc>) -> String {
    ts.to_rfc3339_opts(SecondsFormat::Secs, true)
}

fn non_empty(v: Option<String>) -> Option<String> {
    v.map(|s| s.trim().to_string()).filter(|s| !s.is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_key_accepts_valid_meet_id() {
        let key = parse_key("google_meet", "bqy-ybgi-pbb").expect("valid");
        assert_eq!(key.as_path(), "google_meet/bqy-ybgi-pbb");
    }

    /// SPEC.md §1.3.1 (v1.3): Teams is a SUPPORTED platform. `POST /bots` must
    /// accept it and route it into the Teams join path — the 400 that used to
    /// sit here made every Teams meeting a visible `send_failed`, which was the
    /// right trade only while there was no Teams join path at all.
    #[test]
    fn create_bot_accepts_teams() {
        let key = parse_key("teams", "12345678901").expect("teams must be accepted");
        assert_eq!(key.platform, crate::state::Platform::Teams);
        assert_eq!(
            key.url(),
            "https://teams.microsoft.com/meet/12345678901",
            "the Teams join path is built from this URL"
        );
    }

    /// The half of §1.3.1 that never changed: `teams` must keep PARSING, or
    /// DELETE and GET /transcripts stop addressing historical rows and the
    /// client's 3-hour zombie guard is stranded.
    #[test]
    fn teams_still_parses_so_historical_rows_stay_addressable() {
        let key = parse_key("teams", "12345678901").expect("teams must still parse");
        assert_eq!(key.as_path(), "teams/12345678901");
    }

    /// A Teams native id is digits only, 10-20 of them — that is what
    /// `vexa_bots.py` scrapes off the calendar. A Meet-shaped id on the Teams
    /// platform must still 400 at `parse_key`; removing the platform gate must
    /// not have loosened id validation.
    #[test]
    fn teams_native_id_is_still_validated() {
        assert!(parse_key("teams", "bqy-ybgi-pbb").is_err());
        assert!(parse_key("teams", "123").is_err());
        assert!(parse_key("teams", "12345678901234567890123").is_err());
    }

    /// The happy path the platform work must not have touched.
    #[test]
    fn google_meet_still_parses() {
        let key = parse_key("google_meet", "bqy-ybgi-pbb").expect("valid");
        assert_eq!(key.as_path(), "google_meet/bqy-ybgi-pbb");
    }

    #[test]
    fn parse_key_rejects_unknown_platform() {
        let err = parse_key("zoom", "bqy-ybgi-pbb").unwrap_err();
        assert_eq!(err.status(), StatusCode::BAD_REQUEST);
    }

    #[test]
    fn parse_key_rejects_malformed_native_id() {
        let err = parse_key("google_meet", "never-sent-xyz").unwrap_err();
        assert_eq!(err.status(), StatusCode::BAD_REQUEST);
    }

    #[test]
    fn error_status_mapping_matches_spec() {
        assert_eq!(ApiError::Unauthorized.status(), StatusCode::UNAUTHORIZED);
        assert_eq!(
            ApiError::NotFound("x".into()).status(),
            StatusCode::NOT_FOUND
        );
        assert_eq!(ApiError::Conflict("x".into()).status(), StatusCode::CONFLICT);
        assert_eq!(ApiError::TooManyBots(4).status(), StatusCode::FORBIDDEN);
        assert_eq!(
            ApiError::Unavailable("x".into()).status(),
            StatusCode::SERVICE_UNAVAILABLE
        );
    }

    #[test]
    fn too_many_bots_uses_vexa_wording() {
        assert_eq!(
            ApiError::TooManyBots(4).to_string(),
            "maximum concurrent bot limit (4)"
        );
    }

    #[test]
    fn constant_time_eq_behaves_like_eq() {
        assert!(constant_time_eq(b"secret", b"secret"));
        assert!(!constant_time_eq(b"secret", b"secreT"));
        assert!(!constant_time_eq(b"secret", b"secre"));
    }

    // SPEC.md §1.3.2: the 503 is a deliberate deviation from Vexa and is now a
    // config flag. Default stays fail-fast.
    #[test]
    fn whisper_gate_fails_fast_by_default() {
        let err = whisper_gate(true, false, "http://gw:8083/v1/audio/transcriptions").unwrap_err();
        assert_eq!(err.status(), StatusCode::SERVICE_UNAVAILABLE);
        assert!(
            err.to_string()
                .starts_with("transcription service unreachable at "),
            "wording lands verbatim in the client heartbeat: {err}"
        );
    }

    #[test]
    fn whisper_gate_can_be_configured_to_accept_anyway() {
        assert!(whisper_gate(false, false, "http://gw:8083/x").is_ok());
    }

    #[test]
    fn whisper_gate_is_a_noop_when_whisper_is_up() {
        assert!(whisper_gate(true, true, "http://gw:8083/x").is_ok());
        assert!(whisper_gate(false, true, "http://gw:8083/x").is_ok());
    }

    #[test]
    fn iso_is_utc_with_z() {
        let ts = DateTime::parse_from_rfc3339("2026-07-19T10:42:07Z")
            .unwrap()
            .with_timezone(&Utc);
        assert_eq!(iso(ts), "2026-07-19T10:42:07Z");
    }
}
