# SETUP_AGENT.md — Agent-Run Onboarding Playbook

**You are an AI coding agent (Claude Code, Cursor, Antigravity, or similar) running inside this
repository. A human just asked you to set up their AI Second Brain for them.** This file is your
playbook. Read it fully, then drive the setup end to end, doing every mechanical step yourself and
asking the human only for what genuinely needs a human: decisions, secrets, and browser clicks.

Your goal: by the end, the repo has a real `CLAUDE.md` filled with the user's context, an
`AGENTS.md` pointing to it, the user's chosen tools connected, and at least one verified end-to-end
check. The human should have typed a handful of answers and clicked through a few login screens,
nothing more.

Read these before you start, they are your source of truth:
- `CLAUDE.md.template` — the exact structure you are filling in, section by section.
- `docs/CUSTOMIZING.md` — how to write a strong `CLAUDE.md`.
- `docs/SETUP.md` — the authoritative source for every OAuth and token mechanic. Point to it and
  follow it; do not reinvent auth steps.

---

## Ground rules (hold these the whole way)

1. **Detect your host editor first, and adapt.** You are one of several possible agents. Run `bash
   .agent/scripts/detect_runtime.sh` if it's present in this repo (it prints `RUNTIME=...` among
   other `KEY=VALUE` lines) to find out which, because a few steps differ:
   - **Claude Code** — the rules file is `CLAUDE.md`; commands live in `.claude/commands/`.
   - **Cursor** — reads `CLAUDE.md` and `AGENTS.md` automatically; custom commands live in
     `.cursor/commands/`; MCP in `.cursor/mcp.json`.
   - **Antigravity** — reads `AGENTS.md`; supports `SKILL.md`-based skills and MCP.
   - Any other agent — the `AGENTS.md` → `CLAUDE.md` pattern below still works.
   Only ask the human when the script is missing or its `RUNTIME` line comes back `unknown`: "Which
   editor are you running me in: Cursor, Antigravity, or Claude Code?" It changes only steps 5 and
   9.
2. **One topic at a time.** Ask a small batch of related questions, wait, confirm, move on. Never
   dump the whole questionnaire at once. Keep it conversational, like a patient guide, not a form.
3. **Ask, never assume. Never fabricate.** If the user doesn't know or skips something, leave that
   field blank in `CLAUDE.md` and mark it `TODO, fill in later`. A blank is honest; an invented
   client, stakeholder, or metric is a landmine.
4. **Never collect a secret in the chat.** Do NOT ask the user to paste tokens, passwords, API
   keys, or OAuth codes into the conversation. Instead, walk them through saving each secret into
   its own file (`credentials.json` or `token.env`) per `docs/SETUP.md`. You may create the files
   and run the first-auth flow; the secret goes from the user into the file or the browser, never
   through you.
5. **Confirm before writing.** Before you write or overwrite `CLAUDE.md`, show the assembled section
   back and get a yes.
6. **Match their language.** Ask up front which language they want this conversation in (for AI
   Circle workshop users this is usually Bahasa Indonesia), then mirror it. Their per-document
   language rules are captured separately in Phase 5.
7. **Let them stop anytime.** This can be one sitting or several. If they say "enough for now,"
   write what you have (rest marked TODO) and tell them they can just ask you to "continue the
   setup" later.
8. **You do the mechanical work.** `cp` files, create folders, run install scripts, run the test
   commands, read errors and fix them. The human watches and supplies decisions. Every time an
   error appears, diagnose and fix it rather than handing it back to them.

---

## Phase 0 — Orient (do this silently, then greet)

1. Detect current state before greeting:
   - Does a real `CLAUDE.md` already exist (not just `CLAUDE.md.template`)? If yes, this is a resume
     or edit: read it, tell the user what's already filled, ask which sections to work on.
   - Which connectors already have credentials? Run
     `ls .agent/skills/*/token.env .agent/skills/*/credentials.json 2>/dev/null` so you don't
     re-ask for tools already wired.
   - Has `install.sh` run? If `CLAUDE.md.template` exists but there's no `.env`, offer to run
     `bash install.sh` for them now.
   - Platform: run `bash .agent/scripts/detect_platform.sh` if present, else infer from `uname`.
   - Runtime: run `bash .agent/scripts/detect_runtime.sh` if present (ground rule 1), so you already
     know which editor you're in before greeting.
2. Greet briefly and set expectations: "I'll set up your second brain with you. I'll ask about you,
   your work, and your rules, then connect your tools and do the technical parts myself. About 15
   to 30 minutes, and you can stop anytime."
3. If runtime detection came back unknown, confirm which editor you're running in (ground rule 1).
   Confirm which language to talk in (ground rule 6). Then start Phase 1.

## Phase 1 — Who you're helping  → fills "Who You're Helping"

Ask for: name (what to call them), role or title, city and country (sets their timezone for every
date reference), and working languages. Then one open question: "In 2 to 3 sentences, what do you
actually do day to day?" Confirm the timezone you'll use back to them explicitly.

## Phase 2 — Work contexts  → fills "Work Contexts" + client/project detail

Find out how many distinct work streams they juggle: clients, teams, products, a personal brand.
For **each**, gather: name, what they own there, team size, key stakeholders (name plus role), the
tools that context lives in (Slack channels, Drive folder, tracker), the document language for it,
and current top priorities plus known blockers. One context at a time; don't start context 2 until
context 1 is done. This is the routing table for every future task.

## Phase 3 — Track record & background

This is what makes you *theirs*, not generic. Ask about:
- **Experience and expertise:** years in the field, strong domains, the problems they're the go-to
  person for.
- **Impact and wins:** a few concrete real results, used later for reviews, CVs, bios, content.
  Capture specifics; never invent them.
- **Existing material to ingest:** a CV, LinkedIn export, past reports, a doc bank? If yes, offer to
  copy those into `brain/` (git-ignored, stays local) and read them so you start informed.
- **If they create content or have a personal brand:** platform, cadence, language, writing style,
  topics, tone, and the hard rule of whether you may ever post for them (default: never, they post
  manually).

## Phase 4 — Recurring work  → fills "Workflow Checklists"

Ask which recurring deliverables they want off their desk: weekly reports, meeting notes or MOM,
PRDs, daily briefings, status updates, content, or something else. For each, capture the steps,
format, language, and audience. The template ships sane default checklists (PRD, MOM, Slack, Weekly
Report), so walk through those, keep what fits, adjust the rest, add their own.

## Phase 5 — Rules, approval gates & preferences

Lock down the guardrails:
- **Language by context:** which language for which stream.
- **Approval gates:** confirm the defaults (never send Slack, email, or social, never delete files,
  never push to git without explicit approval) and add their own. Non-negotiable, so make sure
  they're happy with the list.
- **Style rules:** e.g. no em-dashes, formatting preferences, "always give me 3 options first," or
  "don't recap what you just did."

## Phase 6 — Connect tools & data

Now wire up the access you need to actually *do* the work. Follow `docs/SETUP.md` rather than
duplicating its steps.

1. Ask which they use: Google Workspace (Drive, Docs, Calendar, Gmail), Slack, Figma, analytics
   (Mixpanel or Metabase), a tracker (Jira or ClickUp), WhatsApp. Use the "Which skills do you
   actually need?" decision tree in `docs/SETUP.md`; most people need only Google plus Slack plus
   the meeting recorder to get 80% of the value.
2. **Set up the local meeting recorder by default.** Do not ask whether they want a meeting tool
   and do not lead with Fathom. Meeting notes are one of the highest-value things this harness
   does, the recorder needs no account or API key, and the audio stays on their machine, so treat
   it as part of the standard setup and walk them through it:
   - Confirm `ffmpeg` is installed (`ffmpeg -version`), and install it if not.
   - `cp meeting-recorder/config.example.json meeting-recorder/config.json`, then fill in the
     section for their platform (`macos` / `windows` / `wsl`).
   - Run `python3 meeting-recorder/recorder.py --list-devices` with them and help pick the
     loopback or monitor device. This is the step people get stuck on, so do not just hand them
     the command.
   - Record a short test, process it with `python3 meeting-recorder/watcher.py --once`, and
     confirm a transcript plus a `MOM_*.md` draft actually appeared. If nothing appeared, treat
     that as a failed setup and troubleshoot from `docs/MEETING_RECORDER.md`.
   - Full reference for engines, daily use, and the Vexa auto-join bot: `docs/MEETING_RECORDER.md`.
   - Only after this works, ask whether they *also* use a cloud recorder (Fathom). If yes, wire
     `fathom-connector` as an addition. If no, say plainly that they are already covered.
3. For each chosen tool, in order (Google first, it's the foundation):
   - Point them to the exact `docs/SETUP.md` section for getting the credential.
   - Do the mechanical parts yourself: `cp .env.example .env`, create the connector folder and a
     placeholder `token.env`, place `credentials.json` once they've downloaded it.
   - Run the first-auth and verify command from `docs/SETUP.md` and confirm it returns real data.
     If it fails, troubleshoot and fix it.
   - Ground rule 4: the secret goes into the file or the browser, never into this chat.
4. If they want to skip a tool, mark it TODO and move on; they can wire it later by asking you.

## Phase 7 — Assemble & write CLAUDE.md, then AGENTS.md

1. Build the full `CLAUDE.md` from `CLAUDE.md.template`, dropping in everything gathered. Keep
   required sections complete; mark anything skipped `TODO, fill in later`.
2. Show it back (section by section for a long one) and get a yes.
3. Write `CLAUDE.md` in the repo root, leaving the template in place as a reference.
4. **Create `AGENTS.md`** in the repo root: one short paragraph that instructs any agent to follow
   all operating rules in `CLAUDE.md` as the single source of truth. Do not duplicate CLAUDE.md's
   content; just point to it. This is what makes the brain portable across Cursor, Antigravity, and
   Claude Code.

## Phase 8 — Editor-specific wiring (only what your host needs)

- **Cursor:** offer to copy `.claude/commands/*.md` into `.cursor/commands/` so the user can invoke
  workflows by typing `/`. If they use MCP, help them set up `.cursor/mcp.json`.
- **Antigravity:** point out that the `.agent/skills/*/SKILL.md` folders can be treated as native
  skills; offer to summarize which skills exist and when you'll use them.
- **Claude Code:** commands already live in `.claude/commands/`; nothing to move.

## Phase 9 — Verify & hand off

1. Run a quick end-to-end check on at least one connected tool (a read-only call from
   `docs/SETUP.md`) and report the result.
2. Summarize: which contexts you now know, which tools are live, what's still TODO.
3. Suggest 2 to 3 first real tasks to try given what's connected, e.g. "ask me to draft this week's
   report" or "give me a morning briefing."
4. Tell them how the brain improves: correct you in the moment and the lesson can be saved to
   memory, and they can ask you to "continue the setup" anytime to fill the TODOs or add a tool.

---

Begin at Phase 0. Be a patient guide. Do the mechanical work yourself. Ask the human only for
decisions, secrets (into files, never the chat), and browser logins.
