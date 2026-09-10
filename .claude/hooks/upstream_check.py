#!/usr/bin/env python3
"""SessionStart hook: light check whether the upstream template has new commits.

Cross-platform replacement for upstream_check.sh (which used bash + sed/awk +
POSIX `date`/`timeout`).

Runs ONLY in forks of the AI Second Brain template. The source repos (this one,
and you/ai-second-brain itself) self-skip: you cannot be behind yourself.

Cheap by design: one `git ls-remote` (a single ref lookup, no object download),
throttled to once per 24h and cached. Offline or slow network exits silently.

Contract: always exits 0; never blocks the session.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TEMPLATE_URL = "https://github.com/BrianArfi/ai-second-brain.git"
TTL = 86400  # re-check the network at most once per day

def repo_dir():
    # Matches upstream_check.sh: REPO_DIR is derived from the script's own
    # location (two levels up from .claude/hooks/), NOT from CLAUDE_PROJECT_DIR
    # -- the bash version never reads that env var.
    return Path(__file__).resolve().parent.parent.parent

def run_git(args, cwd, timeout=10):
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None, "", ""

def emit_behind():
    ctx = (
        "=== Harness update available ===\n"
        "The upstream AI Second Brain template has commits your fork does not have.\n"
        "Tell the user they can pull them with /update-harness (it merges, resolves\n"
        "conflicts, and surfaces any new .env variables). Do NOT run it unprompted."
    )
    sysmsg = "Harness update available upstream. Run /update-harness to pull it in."
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx},
        "systemMessage": sysmsg,
    }, ensure_ascii=False, separators=(",", ":")))
    sys.exit(0)

def quiet():
    sys.exit(0)

def norm(url):
    """Normalize a remote URL for comparison: lowercase, drop trailing .git,
    drop scp-style/user prefixes -> 'owner/repo'."""
    if not url:
        return ""
    s = url.strip().lower()
    if s.endswith(".git"):
        s = s[: -len(".git")]
    m = re.search(r"[/:]([^/]*/[^/]*)$", s)
    return m.group(1) if m else s

def main():
    repo = repo_dir()
    state_path = repo / ".claude" / ".upstream_check"

    rc, _, _ = run_git(["--version"], repo, timeout=5)
    if rc is None:
        quiet()

    rc, _, _ = run_git(["rev-parse", "--git-dir"], repo, timeout=5)
    if rc is None or rc != 0:
        quiet()

    rc, out, _ = run_git(["remote", "get-url", "origin"], repo, timeout=5)
    origin = out.strip() if rc == 0 else ""
    rc, out, _ = run_git(["remote", "get-url", "upstream"], repo, timeout=5)
    upstream = out.strip() if rc == 0 else ""

    origin_slug = norm(origin)

    # --- Who am I? ---
    # Skip when this repo IS the template (nothing upstream of it).
    if origin_slug == "you/ai-second-brain":
        quiet()

    is_fork = False
    if upstream and norm(upstream) == "you/ai-second-brain":
        is_fork = True
    if origin_slug.endswith("/ai-second-brain"):
        is_fork = True
    if not is_fork:
        quiet()

    # --- Throttle ---
    now = int(time.time())
    last_ts = 0
    last_state = ""
    if state_path.is_file():
        try:
            raw = state_path.read_text(encoding="utf-8").strip()
            parts = raw.split(None, 1)
            if parts:
                try:
                    last_ts = int(parts[0])
                except ValueError:
                    last_ts = 0
                if len(parts) > 1:
                    last_state = parts[1]
        except Exception:
            last_ts = 0
            last_state = ""

    if now > 0 and (now - last_ts) < TTL:
        if last_state == "behind":
            emit_behind()
        quiet()

    # --- The actual check ---
    url = upstream or TEMPLATE_URL
    rc, out, _ = run_git(["ls-remote", url, "refs/heads/main"], repo, timeout=8)
    remote_sha = ""
    if rc == 0 and out:
        first_line = out.splitlines()[0] if out.splitlines() else ""
        fields = first_line.split()
        if fields:
            remote_sha = fields[0]

    if not remote_sha:
        # Offline/unreachable: stay silent, do NOT poison the cache.
        quiet()

    rc, _, _ = run_git(["merge-base", "--is-ancestor", remote_sha, "HEAD"], repo, timeout=10)
    state = "current" if rc == 0 else "behind"

    try:
        state_path.write_text(f"{now} {state}\n", encoding="utf-8")
    except Exception:
        pass

    if state == "behind":
        emit_behind()
    quiet()

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
