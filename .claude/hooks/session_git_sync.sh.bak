#!/usr/bin/env bash
# SessionStart hook: sync repo with GitHub (fetch + rebase pull when safe).
# Portable: pure bash (no python/jq), runs on WSL/Linux, macOS, and Windows Git Bash.
# Always exits 0 and emits hook JSON; never blocks the session.
set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

json_escape() {
  local s="$1"
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\r'/}
  s=${s//$'\n'/\\n}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

emit() {
  local ctx sysmsg
  ctx="$(json_escape "=== Git sync (origin/main) ===
$1")"
  sysmsg="${2:-}"
  if [ -n "$sysmsg" ]; then
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"},"systemMessage":"%s"}\n' \
      "$ctx" "$(json_escape "$sysmsg")"
  else
    printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
  fi
  exit 0
}

command -v git >/dev/null 2>&1 || emit "git not found on this machine — skipped."
git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1 || emit "Not a git repo at $REPO_DIR — skipped."

branch="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ "$branch" = "main" ] || emit "On branch '$branch' (not main) — auto-sync skipped."

# Rebase/merge already in progress? Don't touch anything.
gitdir="$(git -C "$REPO_DIR" rev-parse --git-dir)"
if [ -d "$gitdir/rebase-merge" ] || [ -d "$gitdir/rebase-apply" ] || [ -f "$gitdir/MERGE_HEAD" ]; then
  emit "⚠ A rebase/merge is in progress — auto-sync skipped. Resolve it first." \
       "Git sync: rebase/merge in progress, not synced"
fi

# GNU timeout exists on Linux/WSL; Windows ships an incompatible timeout.exe.
# The hook's own timeout in settings.json is the real safety net.
FETCH=(git -C "$REPO_DIR" fetch origin main --quiet)
if timeout --version 2>/dev/null | grep -q GNU; then
  FETCH=(timeout 20 "${FETCH[@]}")
fi
if ! "${FETCH[@]}" 2>/dev/null; then
  emit "⚠ git fetch failed (offline or GitHub unreachable) — repo may be stale." \
       "Git sync: fetch failed (offline?)"
fi

behind="$(git -C "$REPO_DIR" rev-list --count HEAD..origin/main 2>/dev/null || echo 0)"
ahead="$(git -C "$REPO_DIR" rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
dirty="$(git -C "$REPO_DIR" status --porcelain --untracked-files=no)"

if [ "$behind" -eq 0 ]; then
  if [ "$ahead" -gt 0 ]; then
    emit "✓ Up to date with origin/main, but $ahead local commit(s) not pushed. Consider pushing." \
         "Git sync: $ahead unpushed commit(s) on main"
  fi
  emit "✓ Up to date with origin/main."
fi

if [ -n "$dirty" ]; then
  emit "⚠ origin/main is $behind commit(s) ahead, but the working tree has uncommitted changes — NOT auto-pulled.
Sync manually: commit or stash, then 'git pull --rebase origin main'.
Dirty files:
$dirty" \
       "Git sync: $behind commit(s) behind origin/main — manual sync needed (uncommitted changes)"
fi

if git -C "$REPO_DIR" pull --rebase origin main --quiet 2>/dev/null; then
  pulled="$(git -C "$REPO_DIR" log --oneline -"$behind" 2>/dev/null)"
  emit "✓ Pulled $behind commit(s) from origin/main (rebase):
$pulled" \
       "Git sync: pulled $behind commit(s) from origin/main"
else
  git -C "$REPO_DIR" rebase --abort >/dev/null 2>&1
  emit "⚠ Pull --rebase hit conflicts ($behind commit(s) behind, $ahead ahead) — rebase aborted, repo left untouched.
Resolve manually: 'git pull --rebase origin main' and fix conflicts." \
       "Git sync: rebase conflict — manual sync needed"
fi
