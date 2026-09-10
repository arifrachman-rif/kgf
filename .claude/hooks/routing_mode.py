#!/usr/bin/env python3
"""SessionStart: surface which model this session is on, so the main loop knows
which direction to delegate (down to haiku/sonnet, up to fable) per CLAUDE.md ## Subagents.
Non-blocking, informational only.

Cross-platform replacement for routing_mode.sh.

Model comes from harness_config.py (backed by detect_runtime, which reads the
session transcript JSONL). That is authoritative because the SessionStart hook
payload only carries a "model" field on some call sites -- it is absent on
resume and clear -- which used to make this hook print "unknown" most of the time.
The stdin payload parse below is kept only as a last-resort fallback.

Contract: always exit 0; never block a session.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROUTING_BODY = """Announce the agent plan, do NOT gate on it. Before any task that will spawn
subagents or run a Workflow, emit ONE compact block first, then start work in
the SAME turn without waiting for approval:

  Plan agent: <1-line what> | <tier>: <who does what> | main loop: <what stays>

Routing (CLAUDE.md ## Subagents): match model to the WORK, not to the session.
  - DOWN (always): harvest / lookup / routine draft / conversion -> haiku|sonnet,
    even when this session is on a flagship model.
  - UP (when needed): complex decomposition or ambiguous multi-step planning ->
    Agent(model:"fable", effort:"xhigh"); on a fable session, spawn opus for a
    second flagship lens.
  - Main loop keeps final synthesis, judgment, and the owner-facing output.
Skip the block for single-tool or trivial work. Approval gates that already exist
(Slack sends, Drive writes) still apply and are unaffected by this."""

def get_repo_root():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    # Fallback: two levels up from .claude/hooks/
    return Path(__file__).resolve().parent.parent.parent

def config_lookup(repo_root):
    """Ask harness_config.py --json for {model, tier}. Returns (model, tier), each
    "unknown" on any failure."""
    script = repo_root / ".agent" / "scripts" / "harness_config.py"
    if not script.is_file():
        return "unknown", "unknown"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--json"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unknown", "unknown"

    out = proc.stdout.strip()
    if not out:
        return "unknown", "unknown"
    try:
        d = json.loads(out)
    except Exception:
        return "unknown", "unknown"
    return (d.get("model") or "unknown"), (d.get("tier") or "unknown")

def payload_fallback():
    """Parse the SessionStart stdin payload as a last resort."""
    if sys.stdin.isatty():
        return "unknown"
    try:
        raw = sys.stdin.read()
    except Exception:
        return "unknown"
    if not raw:
        return "unknown"
    try:
        d = json.loads(raw)
    except Exception:
        return "unknown"
    m = d.get("model") or {}
    if isinstance(m, dict):
        return m.get("display_name") or m.get("id") or "unknown"
    return m or "unknown"

def main():
    repo_root = get_repo_root()
    model, tier = config_lookup(repo_root)

    if model == "unknown":
        model = payload_fallback()

    print("=== ROUTING MODE ===")
    print(f"Session model: {model} (tier: {tier}).")
    print(ROUTING_BODY)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
