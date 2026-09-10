#!/usr/bin/env python3
"""SessionStart hook: inject current WIB (UTC+7, Jakarta) date/time so the model
never reasons from UTC.

Cross-platform replacement for wib_clock.sh (which shelled out to
`TZ=Asia/Jakarta date`). Uses datetime with a fixed +07:00 offset instead, since
Indonesia's WIB zone has no DST and no historical offset changes to worry about.

Contract: always exit 0; never block a session.
"""
import json
import sys
from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))

def main():
    try:
        now = datetime.now(WIB)
        formatted = now.strftime("%A, %Y-%m-%d %H:%M WIB")
    except Exception:
        sys.exit(0)

    if not formatted:
        sys.exit(0)

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "=== the owner local time === Now: "
                f"{formatted}. Use THIS for all date/day reasoning (the owner is "
                "UTC+7, Indonesia). Sessions can cross midnight - re-run TZ=Asia/Jakarta "
                "date if much time has passed."
            ),
        }
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
