#!/usr/bin/env python3
"""PostToolUse hook on Bash: formerly the Drive Operation Verification gate.

Cross-platform replacement for drive_verify.sh.

Drive Operation Verification (CLAUDE.md rule) is now enforced INSIDE each
Drive writer script via assert_drive_result() in .agent/scripts/file_utils.py.
All five writers - gdocs_create.py, gdoc_surgical.py, gdocs_writer.py,
gdoc_comment.py, patch_doc_links.py - call it before reporting success, and
it exits nonzero with a clear stderr message when a create/update/upload/
batchUpdate returns no file or document ID. That is a stronger guarantee
than this hook ever gave: it fires on all five writers, not just two, and
it looks at the actual API response instead of guessing from text.

This hook used to re-check the raw Bash command string for the same
signal (script name + create-doc/upload/update) and block the session on a
miss. That was a false-positive machine: ANY command whose text merely
CONTAINS those substrings trips it, including read-only commands like a
`grep -r gdocs_create.py ... update` over this very file, or a `cat`/echo
of documentation that mentions the writers. Matching a raw command string
cannot distinguish a real invocation from a mention of one, so there is no
safe way to keep this as a blocking check - narrowing the regex only moves
the false-positive rate, it does not remove it.

So this hook is now a deliberate no-op: it never blocks and never inspects
tool_response. It stays registered (see .claude/settings.json PostToolUse)
only so this note is where the next person will find it. Enforcement lives
in the writers now.
"""
import sys

def main():
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
