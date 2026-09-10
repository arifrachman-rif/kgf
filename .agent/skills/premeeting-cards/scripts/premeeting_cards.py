#!/usr/bin/env python3
"""
premeeting_cards.py - Auto-brief cards for upcoming meetings.

Pure mechanical join, NO LLM calls:
  Work calendar (gcal_manager.py list --json) x people.json (attendee resolution,
  best-effort) x MTG-* tickets (tickets.json, token overlap >=2) x fathom_registry
  (participant/title overlap >=2 -> last time we met) x open items from the
  Slack mention ledger, decisions log, commitments ledger, and waiting-on watchdog
  (all keyed to attendees when resolvable).

Design (2026-07-10, per the 8-component harness upgrade plan):
  - Clone of mention_ledger.py conventions: BASE_DIR from __file__, atomic
    load_state/save_state (.tmp + os.replace), argparse subcommands, graceful
    degradation when a sibling ledger file doesn't exist yet (all 8 components
    are being built in parallel).
  - `generate` is idempotent: reruning for the same date overwrites that date's
    cards + state entry (no duplication).
  - DEPENDENCY: gcal_manager.py's `list --json` DOES return a populated
    `attendees` field (email + responseStatus; displayName usually empty). The
    real dependency is on `people.json` records having their `emails[]`
    populated, since attendee resolution joins each attendee email to a person
    slug. If those emails are stale/empty the email->slug join yields nothing
    and attendee resolution falls back to empty. Resolution order: (a) native
    `attendees` emails, (b) email addresses found in the event description, and
    (c) known-person name/alias substring matches against the event summary +
    description. See SKILL.md "Gotchas".

Subcommands:
  generate [--date YYYY-MM-DD]   build cards for that WIB date (default: today)
  report [--date YYYY-MM-DD]     briefing-ready markdown index of that date's cards

State: journal/state/premeeting.json
Cards: journal/premeeting/<YYYY-MM-DD>/<HHMM>_<slug>.md
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
STATE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'premeeting.json')
CARDS_DIR = os.path.join(BASE_DIR, 'journal', 'premeeting')

PEOPLE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'people.json')
TICKETS_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'tickets.json')
FATHOM_REGISTRY_PATH = os.path.join(BASE_DIR, 'journal', 'fathom_registry.json')
MENTION_LEDGER_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'slack_mention_ledger.json')
DECISIONS_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'decisions.json')
COMMITMENTS_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'commitments.json')
WAITING_ON_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'waiting_on.json')

GCAL_SCRIPT = os.path.join(BASE_DIR, '.agent', 'skills', 'google-calendar-connector', 'gcal_manager.py')
HEARTBEAT_SCRIPT = os.path.join(BASE_DIR, '.agent', 'scripts', 'heartbeat.py')
JIRA_SCRIPT = os.path.join(BASE_DIR, '.agent', 'skills', 'jira-connector', 'scripts', 'jira_client.py')

sys.path.insert(0, os.path.join(BASE_DIR, '.agent', 'scripts'))
try:
    from portfolio_tagger import ALIASES as PORTFOLIO_ALIASES, resolve_storefront
except ImportError:      # tagger missing -> cards degrade to unfiltered, never crash
    PORTFOLIO_ALIASES = {}
    def resolve_storefront(text):
        return None

# Meeting-title keywords that name a portfolio outright. Checked before the
# topic aliases, since a title like "Marketplace - Sprint Review" is explicit.
PORTFOLIO_TITLE_HINTS = {
    'marketplace': ['marketplace', 'market place'],
    'platform': ['platform'],
    'b2c': ['b2c', 'superapp', 'super app'],
    'ecom-solution': ['e-commerce solution', 'ecommerce solution', 'ecom solution',
                      'seller portal', ' sp ', 'pim', 'oms'],
}
# "storefront" is deliberately absent above: Marketplace owns the storefront
# instances and E-Commerce Solution owns the storefront product, so the word
# alone decides nothing. resolve_storefront() reads the surrounding context.

SPRINT_TITLE_WORDS = ('sprint', 'backlog', 'refinement', 'grooming')

WIB = datetime.timezone(datetime.timedelta(hours=7))
CARD_RETENTION_DAYS = 14

STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'of', 'to', 'for', 'with', 'on', 'in', 'at',
    'prep', 'run', 'weekly', 'call', 'meeting', 'sync', 'review', 'check',
    'follow', 'up', 'followup', 'discussion', 'session', 'catch', 'held',
    'mandatory', 'rsvp', '1:1', 'walkthrough', 'is', 'are', 'we', 'i', 'our',
}

# ------------------------------------------------------------------ helpers --

def slugify(name):
    s = (name or '').strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')

def tokens(text):
    words = re.findall(r'[a-z0-9]+', (text or '').lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f'WARN: failed to parse {path}: {e}', file=sys.stderr)
            return default
    return default

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'dates': {}, 'last_run': None}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATE_PATH)

def wib_now():
    return datetime.datetime.now(WIB)

def parse_event_dt(value):
    """Parse a Google Calendar start/end string (dateTime or all-day date) to
    an aware datetime in WIB."""
    if not value:
        return None
    try:
        if 'T' in value:
            dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.astimezone(WIB)
        dt = datetime.datetime.strptime(value, '%Y-%m-%d')
        return dt.replace(tzinfo=WIB)
    except Exception:
        return None

# ------------------------------------------------------------- data sources --

def fetch_calendar_events():
    """timeout-wrapped gcal_manager.py list --json (Work profile), per spec.
    Tolerates connector auth failure / missing token -> empty list, no crash.
    The `timeout` binary is GNU coreutils and not present on stock macOS, so
    only prepend it when available; subprocess.run's own timeout still bounds
    the call either way."""
    cmd = ([shutil.which('timeout'), '180s'] if shutil.which('timeout') else []) + \
          [sys.executable, GCAL_SCRIPT, 'list',
           '--days-back', '0', '--days-forward', '1', '--profile', 'work', '--json']
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=190)
    except Exception as e:
        print(f'WARN: calendar fetch failed: {e}', file=sys.stderr)
        return []
    if out.returncode != 0:
        print(f'WARN: gcal_manager exit {out.returncode}: {out.stderr[:300]}', file=sys.stderr)
    # stdout may have a status line ahead of the JSON array; find the array.
    text = out.stdout.strip()
    idx = text.find('[')
    if idx == -1:
        return []
    try:
        return json.loads(text[idx:])
    except Exception as e:
        print(f'WARN: could not parse calendar JSON: {e}', file=sys.stderr)
        return []

def load_people():
    """journal/state/people.json is owned by the stakeholders component (5).
    Read-with-fallback: empty dict if it doesn't exist yet."""
    data = load_json(PEOPLE_PATH, {})
    return data.get('people', {}) if isinstance(data, dict) else {}

def load_tickets():
    data = load_json(TICKETS_PATH, {})
    return data.get('tickets', []) if isinstance(data, dict) else []

def load_fathom_registry():
    data = load_json(FATHOM_REGISTRY_PATH, {})
    return data if isinstance(data, dict) else {}

def load_mention_ledger():
    data = load_json(MENTION_LEDGER_PATH, {})
    return data.get('items', {}) if isinstance(data, dict) else {}

def load_decisions():
    data = load_json(DECISIONS_PATH, {})
    return data.get('items', {}) if isinstance(data, dict) else {}

def load_commitments():
    data = load_json(COMMITMENTS_PATH, {})
    return data.get('items', {}) if isinstance(data, dict) else {}

def load_waiting_on():
    data = load_json(WAITING_ON_PATH, {})
    return data.get('items', {}) if isinstance(data, dict) else {}

# ------------------------------------------------------------- attendee join --

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# the owner himself -- never list the calendar owner as an attendee.
SELF_EMAILS = {'you@yourcompany.com', 'you@example.com'}

def pretty_name_from_email(email):
    """Fallback display name for an attendee not in people.json:
    'Teammate.kachavarapu@...' -> 'Teammate Kachavarapu', 'ext.raouf.cherkawi@...'
    -> 'Raouf Cherkawi'."""
    local = re.sub(r'^ext\.', '', (email or '').split('@')[0])
    parts = [p for p in re.split(r'[._-]+', local) if p]
    return ' '.join(p.capitalize() for p in parts) or email

def resolve_attendees(event, people):
    """Resolve an event's attendees. Returns (matched_slugs, display):
      - matched_slugs: people.json slugs, used to key the ledger joins.
      - display: ordered list of EVERY attendee (dicts name/role/slug), so
        guests not in people.json still render (name falls back to the email
        local-part) instead of silently vanishing. the owner is excluded.

    The connector returns a populated `attendees` field, so when it is present
    we resolve by EMAIL ONLY -- the old name/alias substring pass caused false
    positives (e.g. the 3-char alias 'Ali' hitting 'personalization'). The
    text-mining fallbacks run ONLY when the payload carries no attendees[]."""
    email_to_slug = {}
    for slug, person in people.items():
        for e in person.get('emails', []) or []:
            email_to_slug[e.lower()] = slug

    raw = event.get('attendees') or []
    matched = set()
    display = []

    if raw:
        for att in raw:
            email = (att.get('email') or '').lower()
            if not email or email in SELF_EMAILS:
                continue
            slug = email_to_slug.get(email)
            if slug and slug in people:
                matched.add(slug)
                p = people[slug]
                display.append({'name': p.get('name', email), 'role': p.get('role'), 'slug': slug})
            else:
                disp = (att.get('displayName') or '').strip() or pretty_name_from_email(email)
                display.append({'name': disp, 'role': None, 'slug': None})
        return matched, display

    # --- fallback: no attendees[] in payload -> mine summary+description ---
    haystack = f"{event.get('summary', '')} {event.get('description', '')}"
    haystack_l = haystack.lower()
    found_emails = {m.lower() for m in EMAIL_RE.findall(haystack)}
    for slug, person in people.items():
        if found_emails & {e.lower() for e in person.get('emails', []) or []}:
            matched.add(slug)
    # word-boundary name/alias match, min length 4 (avoids 'Ali' inside a word)
    for slug, person in people.items():
        for cand in [person.get('name', '')] + (person.get('aliases') or []):
            cand = (cand or '').strip().lower()
            if len(cand) >= 4 and re.search(r'\b' + re.escape(cand) + r'\b', haystack_l):
                matched.add(slug)
                break
    for slug in sorted(matched):
        p = people[slug]
        display.append({'name': p.get('name'), 'role': p.get('role'), 'slug': slug})
    return matched, display

# ------------------------------------------------------------- ticket join --

def related_tickets(event, tickets):
    """MTG-* tickets whose title shares >=2 significant tokens with the event
    summary."""
    ev_tokens = tokens(event.get('summary', ''))
    if not ev_tokens:
        return []
    hits = []
    for t in tickets:
        if not str(t.get('id', '')).startswith('MTG-'):
            continue
        t_tokens = tokens(t.get('title', ''))
        overlap = ev_tokens & t_tokens
        if len(overlap) >= 2:
            hits.append((len(overlap), t))
    hits.sort(key=lambda x: -x[0])
    return [t for _, t in hits]

# ------------------------------------------------------------- fathom join --

def last_time_we_met(event, people, attendee_slugs, registry):
    """'Last time we met about THIS topic' lookup. Matches only on TOPIC:
    requires >=2 shared title tokens between the event summary and a past
    meeting's title. Shared attendees alone do NOT qualify -- everyone attends
    the same standups, so attendee overlap produced irrelevant matches (an
    'AI Search' card pointing at a generic 'B2C Standup'). Attendee overlap is
    kept only as a tie-breaker among topic-matched candidates. No topic match
    -> 'No prior meeting matched.'"""
    ev_tokens = tokens(event.get('summary', ''))
    if len(ev_tokens) < 2:
        return None
    attendee_names = {people[s]['name'].lower() for s in attendee_slugs
                      if s in people and people[s].get('name')}

    best = None
    best_score = 0
    for rec in registry.values():
        title_tokens = tokens(rec.get('matched_meeting') or rec.get('raw_title') or '')
        title_overlap = len(ev_tokens & title_tokens)
        if title_overlap < 2:
            continue  # must share the actual topic, not just the attendees
        attendee_bonus = 0
        participants = {p.lower() for p in rec.get('participants', [])}
        for name in attendee_names:
            name_tokens = tokens(name)
            if any(name_tokens & tokens(p) for p in participants):
                attendee_bonus += 1
        score = title_overlap * 10 + attendee_bonus
        if score > best_score:
            best_score = score
            best = rec
    return best

# ------------------------------------------------------ slack text cleanup --

_USER_RE = re.compile(r'<@([A-Z0-9]+)(?:\|([^>]+))?>')
_SUBTEAM_RE = re.compile(r'<!subteam\^[A-Z0-9]+(?:\|([^>]+))?>')
_CHAN_RE = re.compile(r'<#[A-Z0-9]+(?:\|([^>]+))?>')
_URL_RE = re.compile(r'<(https?://[^>|]+)(?:\|([^>]+))?>')
_ID_RE = re.compile(r'^(DM:)?[UWC][A-Z0-9]{6,}$')

def make_user_resolver(people, user_names):
    """slack_id -> display name, preferring people.json, then the mention
    ledger's user_names cache, then the raw id."""
    by_id = {p['slack_id']: p['name'] for p in people.values()
             if p.get('slack_id') and p.get('name')}
    cache = user_names or {}

    def resolve(uid):
        if not uid:
            return 'someone'
        return by_id.get(uid) or cache.get(uid) or uid
    return resolve

def clean_slack_text(text, resolve_user):
    """Render raw Slack mrkdwn readable: resolve <@ID|Name>/<@ID> mentions,
    turn <url|label> into markdown links, collapse whitespace."""
    if not text:
        return ''
    text = _USER_RE.sub(lambda m: '@' + (m.group(2) or resolve_user(m.group(1))), text)
    text = _SUBTEAM_RE.sub(lambda m: '@' + (m.group(1) or 'group'), text)
    text = _CHAN_RE.sub(lambda m: '#' + (m.group(1) or 'channel'), text)
    text = _URL_RE.sub(lambda m: f"[{m.group(2) or 'link'}]({m.group(1)})", text)
    return re.sub(r'\s+', ' ', text).strip()

def channel_label(item, channel_names, resolve_user):
    """Human channel name, resolving raw ids and DM pseudo-channels."""
    chan = (item.get('channel_name') or '').strip()
    cid = item.get('channel', '')
    if chan.startswith('DM:'):
        return 'DM: ' + resolve_user(chan[3:])
    if chan.startswith('mpdm-'):
        n = chan.count('--') + 1
        return f'Group DM ({n} people)'
    if chan and not _ID_RE.match(chan):
        return chan
    if cid.startswith('C'):
        return (channel_names or {}).get(cid) or chan or cid
    if chan.startswith(('U', 'W')):
        return 'DM: ' + resolve_user(chan)
    return (channel_names or {}).get(cid) or 'DM: ' + resolve_user(item.get('author', ''))

# --------------------------------------------------------------- card build --

# ------------------------------------------------------------------ portfolio --

def infer_meeting_portfolios(event):
    """Which of the owner's four portfolios this meeting is actually about.

    Returns a set, because some standups genuinely straddle two ("B2C + SP + PIM").
    An empty set means "could not tell" and the caller must NOT filter, otherwise
    an unrecognised meeting would silently show an empty card.

    Deliberately reads the TITLE only. Attendee lists are the very thing that
    caused cross-portfolio bleed: a wide invite is not evidence of scope.
    """
    title = (event.get('summary') or '').lower()
    if not title:
        return set()
    padded = f' {title} '

    storefront = resolve_storefront(padded)
    if storefront:
        return {storefront}

    found = set()
    for pid, needles in PORTFOLIO_TITLE_HINTS.items():
        for needle in needles:
            if needle in padded:
                found.add(pid)
                break
    if found:
        return found

    for pid, needles in PORTFOLIO_ALIASES.items():
        for needle in needles:
            if needle in padded:
                found.add(pid)
                break
    return found

def split_by_portfolio(items, meeting_portfolios):
    """(in_scope, out_of_scope). No filtering when the meeting is unclassified."""
    if not meeting_portfolios:
        return list(items), []
    in_scope, out_of_scope = [], []
    for it in items:
        (in_scope if it.get('portfolio') in meeting_portfolios else out_of_scope).append(it)
    return in_scope, out_of_scope

def is_sprint_meeting(event):
    title = (event.get('summary') or '').lower()
    return any(w in title for w in SPRINT_TITLE_WORDS)

def fetch_sprint_status(portfolio, stale_before):
    """Active-sprint snapshot via the jira connector. Never fatal: a missing token
    or a slow board degrades the card to 'unavailable' rather than killing the run."""
    try:
        proc = subprocess.run(
            [sys.executable, JIRA_SCRIPT, 'sprint-status',
             '--portfolio', portfolio, '--stale-before', stale_before],
            capture_output=True, text=True, timeout=90)
        if proc.returncode != 0:
            return {'error': (proc.stderr or proc.stdout or 'jira_client failed').strip()[:200]}
        return json.loads(proc.stdout)
    except Exception as e:
        return {'error': str(e)[:200]}

def build_card(event, people, tickets, registry, mention_items, decisions,
                commitments, waiting_items, user_names=None, channel_names=None):
    start_dt = parse_event_dt(event.get('start'))
    time_wib = start_dt.strftime('%H:%M') if start_dt else '--:--'
    title = event.get('summary', '(No title)')

    attendee_slugs, attendee_display = resolve_attendees(event, people)
    attendees = [people[s] for s in attendee_slugs if s in people]

    fathom_hit = last_time_we_met(event, people, attendee_slugs, registry)

    slack_ids = {p.get('slack_id') for p in attendees if p.get('slack_id')}
    pings = [it for it in mention_items.values()
             if it.get('status') == 'open' and it.get('author') in slack_ids]

    open_decisions = [d for d in decisions.values()
                       if d.get('status') == 'open'
                       and (set(d.get('stakeholder_slugs', [])) & attendee_slugs)]

    # Attendee membership decides WHO could answer; portfolio decides WHETHER the
    # item belongs in this room at all. Both gates, in that order.
    owe_candidates = [c for c in commitments.values()
                       if c.get('status') == 'open' and c.get('to_slug') in attendee_slugs]
    owed_candidates = [w for w in waiting_items.values()
                        if w.get('status') in ('open', 'breached')
                        and w.get('owner_slug') in attendee_slugs]

    meeting_portfolios = infer_meeting_portfolios(event)
    you_owe_them, you_owe_other = split_by_portfolio(owe_candidates, meeting_portfolios)
    they_owe_you, they_owe_other = split_by_portfolio(owed_candidates, meeting_portfolios)

    sprint = None
    if is_sprint_meeting(event) and len(meeting_portfolios) == 1:
        stale_before = (wib_now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        sprint = fetch_sprint_status(next(iter(meeting_portfolios)), stale_before)

    tix = related_tickets(event, tickets)

    lines = []
    lines.append(f'# {time_wib} WIB — {title}')
    lines.append('')
    if meeting_portfolios:
        lines.append(f"**Portfolio:** {', '.join(sorted(meeting_portfolios))}")
    else:
        lines.append('**Portfolio:** unclassified — items below are NOT filtered by portfolio')
    lines.append('')
    lines.append('## Attendees')
    if attendee_display:
        for a in attendee_display:
            role = f" ({a['role']})" if a.get('role') else ''
            lines.append(f"- {a.get('name', '(unknown)')}{role}")
    else:
        lines.append('- (no attendees in calendar payload)')
    lines.append('')

    lines.append('## Last time we met')
    if fathom_hit:
        title_str = fathom_hit.get('matched_meeting') or fathom_hit.get('raw_title') or '(untitled)'
        lines.append(f"- {fathom_hit.get('date_wib', '?')} — {title_str} "
                      f"([Fathom]({fathom_hit.get('fathom_url', '')}))")
    else:
        lines.append('- No prior meeting matched.')
    lines.append('')

    lines.append('## You owe them')
    if you_owe_them:
        for c in you_owe_them:
            due = f" (due {c.get('due')})" if c.get('due') else ''
            lines.append(f"- {c.get('text', '(no text)')}{due} `{c.get('id')}`")
    else:
        lines.append('- Nothing open.')
    lines.append('')

    lines.append('## They owe you')
    if they_owe_you:
        for w in they_owe_you:
            flag = '🚨 ' if w.get('status') == 'breached' else ''
            lines.append(f"- {flag}{w.get('what', '(no detail)')} (since {w.get('since', '?')}) `{w.get('id')}`")
    else:
        lines.append('- Nothing open.')
    lines.append('')

    lines.append('## Open decisions')
    if open_decisions:
        for d in open_decisions:
            deadline = f" (deadline {d.get('deadline')})" if d.get('deadline') else ''
            lines.append(f"- {d.get('title', '(untitled)')}{deadline} `{d.get('id')}`")
    else:
        lines.append('- None open.')
    lines.append('')

    lines.append('## Unanswered pings')
    if pings:
        resolve_user = make_user_resolver(people, user_names)
        for it in pings:
            text = clean_slack_text(it.get('text', ''), resolve_user)
            if len(text) > 200:
                text = text[:200].rstrip() + '…'
            chan = channel_label(it, channel_names, resolve_user)
            author = resolve_user(it.get('author', ''))
            link = it.get('permalink') or ''
            label = f"[#{chan}]({link})" if link else f"#{chan}"
            lines.append(f"- {label} · @{author}: {text}")
    else:
        lines.append('- None.')
    lines.append('')

    lines.append('## Related tickets')
    if tix:
        for t in tix:
            lines.append(f"- {t.get('id')} — {t.get('title')} [{t.get('status')}]")
    else:
        lines.append('- None matched.')
    lines.append('')

    if sprint:
        lines.append('## Sprint board')
        if sprint.get('error'):
            lines.append(f"- Unavailable: {sprint['error']}")
        else:
            for b in sprint.get('boards', []):
                if b.get('error'):
                    lines.append(f"- {b.get('name')}: {b['error']}")
                    continue
                base = f"https://{b['domain']}/browse/"
                lines.append(f"**{b['name']} ({b['project_key']}) · {b.get('sprint_name')} "
                             f"· ends {b.get('end_date')}**")
                lines.append(f"- {b['total']} issues: {b['done']} done, {b['open']} open")
                order = sorted(b.get('by_status', {}).items(), key=lambda kv: -kv[1])
                status_str = ', '.join(f'{k} {v}' for k, v in order)
                lines.append(f"- Status: {status_str}")
                top = list(b.get('by_assignee', {}).items())[:1]
                if top and b['open']:
                    who, n = top[0]
                    lines.append(f"- Heaviest load: {who} holds {n} of {b['open']} open "
                                 f"({round(n / b['open'] * 100)}%)")
                stale = b.get('stale', [])
                if stale:
                    lines.append(f"- ⚠️ {len(stale)} open issue(s) untouched for over a week:")
                    for r in stale[:8]:
                        lines.append(f"    - [{r['key']}]({base}{r['key']}) · {r['updated']} "
                                     f"· {r['status']} · {r['assignee']} · {r['summary'][:60]}")
                    if len(stale) > 8:
                        lines.append(f"    - ...and {len(stale) - 8} more")
                lines.append('')
        lines.append('')

    if you_owe_other or they_owe_other:
        lines.append('## Other portfolios — do NOT raise here')
        lines.append('<details>')
        lines.append('<summary>Open items these attendees carry that belong to another '
                     'portfolio or are unclassified</summary>')
        lines.append('')
        for c in you_owe_other:
            lines.append(f"- (you owe · {c.get('portfolio', '?')}) {c.get('text', '')} `{c.get('id')}`")
        for w in they_owe_other:
            lines.append(f"- (they owe · {w.get('portfolio', '?')}) {w.get('what', '')} `{w.get('id')}`")
        lines.append('')
        lines.append('</details>')
        lines.append('')

    return '\n'.join(lines), {
        'title': title, 'time_wib': time_wib,
        'attendee_slugs': sorted(attendee_slugs),
        'n_decisions': len(open_decisions), 'n_pings': len(pings),
        'n_you_owe': len(you_owe_them), 'n_they_owe': len(they_owe_you),
        'n_tickets': len(tix), 'has_last_meeting': bool(fathom_hit),
        'portfolios': sorted(meeting_portfolios),
        'n_filtered_out': len(you_owe_other) + len(they_owe_other),
        'has_sprint': bool(sprint and not sprint.get('error')),
    }

# --------------------------------------------------------------------- prune --

def heartbeat(job, status, summary):
    try:
        subprocess.run([sys.executable, HEARTBEAT_SCRIPT, '--job', job, '--status', status,
                        '--summary', summary], capture_output=True, text=True, timeout=15)
    except Exception as e:
        print(f'  ! heartbeat failed (non-fatal): {e}', file=sys.stderr)

def prune_old_cards():
    if not os.path.isdir(CARDS_DIR):
        return
    cutoff = (wib_now() - datetime.timedelta(days=CARD_RETENTION_DAYS)).strftime('%Y-%m-%d')
    for name in os.listdir(CARDS_DIR):
        path = os.path.join(CARDS_DIR, name)
        if not os.path.isdir(path):
            continue
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', name) and name < cutoff:
            for f in os.listdir(path):
                try:
                    os.remove(os.path.join(path, f))
                except OSError:
                    pass
            try:
                os.rmdir(path)
            except OSError:
                pass

# -------------------------------------------------------------------- main --

def cmd_generate(args):
    target_date = getattr(args, 'date', None) or wib_now().strftime('%Y-%m-%d')
    try:
        events = fetch_calendar_events()
        people = load_people()
        tickets = load_tickets()
        registry = load_fathom_registry()
        mention_data = load_json(MENTION_LEDGER_PATH, {})
        mention_items = mention_data.get('items', {}) if isinstance(mention_data, dict) else {}
        user_names = mention_data.get('user_names', {}) if isinstance(mention_data, dict) else {}
        channel_names = mention_data.get('channel_names', {}) if isinstance(mention_data, dict) else {}
        decisions = load_decisions()
        commitments = load_commitments()
        waiting_items = load_waiting_on()

        day_events = []
        for ev in events:
            dt = parse_event_dt(ev.get('start'))
            if dt and dt.strftime('%Y-%m-%d') == target_date:
                day_events.append((dt, ev))
        day_events.sort(key=lambda x: x[0])

        day_dir = os.path.join(CARDS_DIR, target_date)
        os.makedirs(day_dir, exist_ok=True)
        # idempotent regen: clear any existing cards for this date before rewriting
        for f in os.listdir(day_dir):
            if f.endswith('.md'):
                try:
                    os.remove(os.path.join(day_dir, f))
                except OSError:
                    pass

        written = []
        for dt, ev in day_events:
            slug = slugify(ev.get('summary', 'meeting'))[:40] or 'meeting'
            fname = f"{dt.strftime('%H%M')}_{slug}.md"
            content, meta = build_card(ev, people, tickets, registry, mention_items,
                                        decisions, commitments, waiting_items,
                                        user_names=user_names, channel_names=channel_names)
            fpath = os.path.join(day_dir, fname)
            tmp = fpath + '.tmp'
            with open(tmp, 'w') as f:
                f.write(content)
            os.replace(tmp, fpath)
            written.append({'file': os.path.join('journal', 'premeeting', target_date, fname), **meta})

        state = load_state()
        state['dates'][target_date] = {'generated_at': time.time(), 'cards': written}
        state['last_run'] = time.time()
        save_state(state)

        prune_old_cards()

        print(f'generated {len(written)} card(s) for {target_date} -> {day_dir}')
        for w in written:
            print(f"  - {w['time_wib']} {w['title']} ({w['file']})")
        heartbeat('premeeting-cards', 'ok', f'{len(written)} cards for {target_date}')
        return written
    except Exception as e:
        heartbeat('premeeting-cards', 'fail', str(e)[:280])
        raise

def cmd_report(args):
    target_date = getattr(args, 'date', None) or wib_now().strftime('%Y-%m-%d')
    state = load_state()
    entry = state.get('dates', {}).get(target_date)
    if not entry or not entry.get('cards'):
        print(f'No pre-meeting cards for {target_date}. Run `generate` first.')
        return
    print(f'## 📋 Pre-meeting cards — {target_date} ({len(entry["cards"])})\n')
    for c in entry['cards']:
        flags = []
        if c.get('n_decisions'):
            flags.append(f"{c['n_decisions']} open decision(s)")
        if c.get('n_pings'):
            flags.append(f"{c['n_pings']} unanswered ping(s)")
        if c.get('n_you_owe'):
            flags.append(f"{c['n_you_owe']} you owe")
        if c.get('n_they_owe'):
            flags.append(f"{c['n_they_owe']} they owe")
        if c.get('n_tickets'):
            flags.append(f"{c['n_tickets']} related ticket(s)")
        flag_str = f" — {', '.join(flags)}" if flags else ''
        attendees_str = ', '.join(c.get('attendee_slugs', [])) or 'unresolved attendees'
        print(f"- **{c['time_wib']}** {c['title']} ({attendees_str}){flag_str} — [{c['file']}]({c['file']})")

def main():
    p = argparse.ArgumentParser(description='Pre-meeting brief cards (mechanical join, no LLM)')
    sub = p.add_subparsers(dest='cmd')
    gp = sub.add_parser('generate')
    gp.add_argument('--date', help='YYYY-MM-DD (default: today WIB)')
    rp = sub.add_parser('report')
    rp.add_argument('--date', help='YYYY-MM-DD (default: today WIB)')
    args = p.parse_args()
    {'generate': cmd_generate, 'report': cmd_report}.get(args.cmd or 'generate', cmd_generate)(args)

if __name__ == '__main__':
    main()
