#!/usr/bin/env python3
"""PreToolUse hook on Slack send tools (matcher: mcp__.*[Ss]lack.*__.*(post|send|reply).*).

Cross-platform replacement for slack_send_guard.sh.

Forces a confirmation prompt for EVERY Slack send, even if the tool is allowlisted -
the owner's rule: nothing goes to Slack without explicit "kirim"/approval.
Uses permissionDecision "ask" (not "deny") so an approved send costs one keypress.

Contract: always exit 0; on any internal failure fall back to a static prompt.
"""
import json
import sys

# Byte-identical to the bash script's raw `printf` fallback line (no python3,
# or empty stdin -- the bash script skips its python heredoc entirely in that
# case and falls through to this hand-written, compact/no-space JSON string).
RAW_FALLBACK_LINE = (
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask",'
    '"permissionDecisionReason":"APPROVAL GATE - Slack send detected. Confirm the owner '
    'explicitly approved this exact message (kirim)."}}'
)

# Same wording, used inside the "python parsed something" path below, where the
# bash script's inner python heredoc (default-spaced json.dumps) is the one
# producing output -- matches its except: branch reason string exactly.
FALLBACK_REASON = (
    "APPROVAL GATE - Slack send detected. Confirm the owner explicitly approved "
    "this exact message (kirim)."
)

def build_reason(raw):
    try:
        d = json.loads(raw)
        ti = d.get("tool_input") or {}
        ch = str(ti.get("channel_id") or ti.get("channel") or ti.get("channel_name") or "?")
        txt = str(ti.get("text") or ti.get("message") or "")[:300]
        txt = txt.replace("\n", " / ").replace('"', "'")
        return (
            f"APPROVAL GATE - Slack send to [{ch}]. Did the owner explicitly say "
            f'kirim/approve for THIS exact message? Preview: "{txt}"'
        )
    except Exception:
        return FALLBACK_REASON

def main():
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    except Exception:
        raw = ""

    if not raw:
        # Mirrors bash: no python3 available, or stdin empty -> raw compact fallback.
        print(RAW_FALLBACK_LINE)
        sys.exit(0)

    reason = build_reason(raw)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(payload))
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fallback: still gate the send even if something above blew up.
        print(RAW_FALLBACK_LINE)
        sys.exit(0)
