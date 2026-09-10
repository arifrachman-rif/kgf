#!/usr/bin/env bash
# DISABLED 26 Jul 2026 - the owner found the focus-steal annoying. The PostToolUse hook that
# invoked this script was removed from .claude/settings.local.json. Do NOT re-wire it.
# Present a consolidated clickable link list at the end of a task instead (memory:
# feedback_batch_file_writes_link_list). Script kept only for reference.
exit 0
# PostToolUse hook: auto-open Work deliverable .md files in VS Code so the owner can read + comment.
# Reads the tool-call JSON on stdin, extracts the file path, and opens it in the existing VS Code window.
# Scope: only .md files under a Clients/ directory. Skips *_output.md scratch renders.
# Silent + non-blocking by design (never fails a Write/Edit). Uses python3 (jq not guaranteed on PATH).

f=$(python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("file_path") or d.get("tool_response",{}).get("filePath") or "")
except Exception:
    print("")' 2>/dev/null)
[ -z "$f" ] && exit 0

# Only deliverables under Clients/, only markdown
case "$f" in
  */Clients/*.md) : ;;
  *) exit 0 ;;
esac
# Skip machine-generated scratch renders
case "$f" in
  *_output.md) exit 0 ;;
esac

# Resolve the VS Code CLI: PATH first, then the WSL remote-cli (version hash changes on updates)
CODE=$(command -v code 2>/dev/null)
[ -z "$CODE" ] && CODE=$(ls -t ~/.vscode-server/bin/*/bin/remote-cli/code 2>/dev/null | head -1)
[ -z "$CODE" ] && exit 0

# -r reuses the current window instead of spawning a new one each time
"$CODE" -r "$f" >/dev/null 2>&1 || true
exit 0
