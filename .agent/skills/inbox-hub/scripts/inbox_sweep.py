#!/usr/bin/env python3
"""inbox_sweep.py — unified inbound-inquiry hub for the dashboard Inbox tab.

Aggregates everything waiting on the owner across channels into ONE state file
(journal/state/inbox.json) that the dashboard renders as the 📥 Inbox tab:

  slack  — mirrors OPEN items from journal/state/slack_mention_ledger.json
           (the mention ledger stays the Slack source of truth; when the
           ledger answers/dismisses an item, the mirrored inbox item is
           auto-closed on the next sweep — flow is one-way ledger -> inbox,
           this script NEVER writes the mention ledger)
  gmail  — Work inbox (you@yourcompany.com) via the Gmail API
           using gmail-connector's token; last 3 days, promotions/social
           excluded, messages FROM the owner excluded
  gdoc   — Google Docs comment mentions (STUB — phase 2, needs Drive
           comments API wiring; renders as an empty lane with a note)
  jira   — Jira comment mentions (STUB — phase 2 via jira-connector)

the owner's triage statuses (open|done|ignored) live ONLY in inbox.json — they are
an overlay, never pushed back to Slack/Gmail — so every action is reversible
via `set-status --status open` (the dashboard Undo button).

Subcommands:
  sweep                       harvest all sources, merge preserving statuses
  set-status ID --status S    open|done|ignored (the dashboard single writer)
  link ID --ticket T-123      tie an item to a tracker ticket
  report                      one-line-per-open-item markdown (briefing embed)

State shape: {"last_sweep": epoch, "last_sweep_wib": iso, "sources": {name:
{ok, n, note}}, "items": {id: ITEM}}. ITEM keys: id, source, ts, from,
from_id, channel, title, text, permalink, status, status_changed_at,
prev_status, linked_ticket, first_seen.
"""
import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', '..'))
STATE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'inbox.json')
MENTION_LEDGER_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'slack_mention_ledger.json')
PEOPLE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'people.json')
NAME_CACHE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'slack_user_names.json')
SLACK_TOKEN_ENV = os.path.join(BASE_DIR, '.agent', 'skills', 'slack-connector', 'token.env')
GMAIL_TOKEN = os.path.join(BASE_DIR, '.agent', 'skills', 'gmail-connector', 'token_gmail_work.json')
AGY_BRIDGE = os.path.join(BASE_DIR, '.agent', 'skills', 'agy-bridge', 'run.py')
WIB = timezone(timedelta(hours=7))

OWNER_SLACK_ID = '<SLACK_ID>'
GMAIL_QUERY = 'newer_than:3d -category:promotions -category:social -from:me'
GMAIL_LIMIT = 25
DONE_RETENTION_DAYS = 14      # prune done/ignored items after this
GONE_RETENTION_DAYS = 7       # prune OPEN items whose source no longer reports them

# ------------------------------------------------------------------ state --

def load_state():
    try:
        with open(STATE_PATH, encoding='utf-8') as fh:
            st = json.load(fh)
        st.setdefault('items', {})
        return st
    except Exception:
        return {'last_sweep': 0, 'items': {}, 'sources': {}}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_PATH)

def new_item(item_id, source, **kw):
    it = {
        'id': item_id, 'source': source, 'ts': 0.0, 'from': '', 'from_id': '',
        'channel': '', 'title': '', 'text': '', 'permalink': '',
        'status': 'open', 'status_changed_at': None, 'prev_status': None,
        'linked_ticket': None, 'first_seen': time.time(),
        'triage': 'fyi', 'priority_hi': False, 'draft_reply': None,
        'draft_source': None, 'messages': [], 'msg_count': 1,
        'send_channel': None, 'send_thread_ts': None,
        'sent_permalink': None, 'sent_at': None,
    }
    it.update(kw)
    return it

# ------------------------------------------------------- name resolution --

def _load_names():
    """UID -> display name, merged from (priority order): local cache, the mention
    ledger's user_names, people.json slack_ids. Never guesses — an unresolvable
    ID stays a raw UID (per feedback_no_guessing_names)."""
    names = {}
    try:
        people = json.load(open(PEOPLE_PATH, encoding='utf-8'))
        plist = people.get('people', people)
        it = plist.values() if isinstance(plist, dict) else plist
        for p in it:
            if p.get('slack_id') and p.get('name'):
                names[p['slack_id']] = p['name']
    except Exception:
        pass
    try:
        ledger = json.load(open(MENTION_LEDGER_PATH, encoding='utf-8'))
        names.update(ledger.get('user_names') or {})
    except Exception:
        pass
    try:
        names.update(json.load(open(NAME_CACHE_PATH, encoding='utf-8')))
    except Exception:
        pass
    return names

def _slack_token():
    try:
        for line in open(SLACK_TOKEN_ENV, encoding='utf-8'):
            line = line.strip()
            if line.startswith('SLACK_USER_TOKEN') and '=' in line:
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return os.environ.get('SLACK_USER_TOKEN')

def _resolve_unknown_ids(uids, names):
    """users.info the still-unknown IDs (bounded), grow the local cache. Failures
    are silent — the raw UID keeps rendering rather than a guessed name."""
    missing = [u for u in uids if u and u not in names][:25]
    if not missing:
        return names
    tok = _slack_token()
    if not tok:
        return names
    import urllib.request
    import urllib.parse
    learned = {}
    for uid in missing:
        try:
            data = urllib.parse.urlencode({'token': tok, 'user': uid}).encode()
            req = urllib.request.Request('https://slack.com/api/users.info', data=data)
            r = json.load(urllib.request.urlopen(req, timeout=10))
            prof = (r.get('user') or {}).get('profile') or {}
            nm = prof.get('display_name') or prof.get('real_name') or ''
            if r.get('ok') and nm:
                learned[uid] = nm
            time.sleep(0.25)
        except Exception:
            continue
    if learned:
        names.update(learned)
        try:
            cache = {}
            if os.path.exists(NAME_CACHE_PATH):
                cache = json.load(open(NAME_CACHE_PATH, encoding='utf-8'))
            cache.update(learned)
            tmp = NAME_CACHE_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(cache, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, NAME_CACHE_PATH)
        except Exception:
            pass
    return names

def clean_slack_text(text, names):
    """Slack markup -> renderable markdown: <@UID|label> -> @label, <@UID> -> @name,
    <#CID|chan> -> #chan, <url|label> -> [label](url) (links stay clickable),
    <url> -> url. Newlines are KEPT so lists render as lists."""
    t = text or ''
    t = re.sub(r'<@([A-Z0-9]+)\|([^>]+)>', r'@\2', t)
    t = re.sub(r'<@([A-Z0-9]+)>',
               lambda m: '@' + names.get(m.group(1), m.group(1)), t)
    t = re.sub(r'<#[A-Z0-9]+\|([^>]+)>', r'#\1', t)
    t = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'[\2](\1)', t)
    t = re.sub(r'<(https?://[^>]+)>', r'\1', t)
    t = re.sub(r'<mailto:([^|>]+)(\|[^>]*)?>', r'\1', t)
    t = re.sub(r'[ \t]+', ' ', t)
    return re.sub(r'\n{3,}', '\n\n', t).strip()

def _fetch_full_conversation(gkey, msgs, names, tok):
    """Replace the ledger's mention-only, 600-char-capped view of a conversation
    with the REAL thread from the Slack API: every message, full text, including
    the owner's own replies — so the drawer matches what Slack shows and the digest
    drafts against complete context. Returns a message_log list or None on any
    failure (caller falls back to the ledger view)."""
    if not tok:
        return None
    import urllib.request
    import urllib.parse
    last = msgs[-1]
    chan_id = str(last.get('channel') or '')

    def call(method, **params):
        params['token'] = tok
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(f'https://slack.com/api/{method}', data=data)
        return json.load(urllib.request.urlopen(req, timeout=10))

    try:
        if gkey.startswith('dm-'):
            r = call('conversations.history', channel=chan_id, limit=15)
            raw = list(reversed(r.get('messages', []))) if r.get('ok') else None
        elif last.get('thread_ts'):
            r = call('conversations.replies', channel=chan_id,
                     ts=last['thread_ts'], limit=25)
            raw = r.get('messages', []) if r.get('ok') else None
        else:
            return None                     # standalone message: ledger view is fine
        if not raw:
            return None
        out = []
        for m in raw:
            if m.get('subtype') in ('channel_join', 'channel_leave'):
                continue
            uid = m.get('user') or m.get('bot_id') or '?'
            out.append({
                'from': names.get(uid, uid),
                'ts': float(m.get('ts') or 0),
                'text': clean_slack_text(m.get('text') or '', names),
            })
        return out or None
    except Exception:
        return None

# ------------------------------------------------------------------ triage --

ASK_RE = re.compile(
    r'\?|(?:\b(?:please|pls|kindly|can you|could you|would you|need your|need you|'
    r'let me know|lmk|wdyt|your (?:thoughts|input|approval|review|confirmation)|'
    r'confirm|approve|review|waiting (?:on|for) you|quick call|urgent|asap|'
    r'by (?:today|tomorrow|eod|eow))\b)', re.I)
ACK_RE = re.compile(
    r'^(?:@\S+\s*)*(?:thanks|thank you|thx|noted|understood|got it|ok(?:ay)?|sure|'
    r'done|invite sent|no no|great|perfect|awesome|will do|sounds good)\b', re.I)

def triage_slack(it, cleaned, author_id):
    """'reply' (the owner owes an answer) vs 'fyi' (visible, no action). Conservative:
    DMs and direct asks -> reply; short acknowledgements / passing mentions -> fyi.
    Anything from YourManager is always reply+high (feedback_harvest_catch_dms_fred_priority)."""
    YourManager = '<SLACK_ID>'
    if author_id == YourManager:
        return 'reply', True
    is_dm = (it.get('kind') == 'dm')
    mentions_brian = OWNER_SLACK_ID in (it.get('text') or '')
    asks = bool(ASK_RE.search(cleaned))
    ack = bool(ACK_RE.match(cleaned)) and len(cleaned) < 90 and '?' not in cleaned
    if ack:
        return 'fyi', False
    if is_dm:
        return 'reply', bool(asks and re.search(r'\burgent|asap\b', cleaned, re.I))
    if mentions_brian and asks:
        return 'reply', False
    return 'fyi', False

GMAIL_FYI_SENDER_RE = re.compile(
    r'(?:jira|no-?reply|notification|via read ai|via sprinto|calendar-notification|'
    r'drive-shares-noreply|comments-noreply|mailer|automated)', re.I)

def triage_gmail(sender, subject, snippet):
    if GMAIL_FYI_SENDER_RE.search(sender or ''):
        return 'fyi', False
    text = f'{subject} {snippet}'
    if ASK_RE.search(text):
        return 'reply', bool(re.search(r'\burgent|asap|approval required|action needed\b',
                                       text, re.I))
    return 'fyi', False

# ---------------------------------------------------------------- sources --

def harvest_slack():
    """Mirror OPEN mention-ledger items GROUPED PER CONVERSATION — one inbox item
    per DM partner / channel thread / standalone message, never one row per
    message. The ledger is the Slack SSOT — we only read it."""
    try:
        with open(MENTION_LEDGER_PATH, encoding='utf-8') as fh:
            ledger = json.load(fh)
    except Exception as e:
        return {}, f'ledger unreadable: {e}'
    chan_names = ledger.get('channel_names') or {}
    open_items = {k: v for k, v in (ledger.get('items') or {}).items()
                  if v.get('status') == 'open'}
    names = _load_names()
    ids = {v.get('author') for v in open_items.values()}
    ids |= {v.get('channel') for v in open_items.values()
            if re.fullmatch(r'U[A-Z0-9]+', str(v.get('channel') or ''))}
    for v in open_items.values():        # UIDs referenced inside message bodies too
        ids.update(re.findall(r'<@([A-Z0-9]+)>', v.get('text') or ''))
    names = _resolve_unknown_ids(sorted(x for x in ids if x), names)

    # group: DM channel -> one convo; channel thread -> one convo; else per message
    groups = {}
    for it in open_items.values():
        chan_id = str(it.get('channel') or '')
        if re.fullmatch(r'[DU][A-Z0-9]+', chan_id):
            gkey = f'dm-{chan_id}'
        elif it.get('thread_ts'):
            gkey = f'{chan_id}-{it["thread_ts"]}'
        else:
            gkey = f'{chan_id}-{it.get("ts")}'
        groups.setdefault(gkey, []).append(it)

    out = {}
    tok = _slack_token()
    fetch_budget = 40        # full-thread API fetches per sweep, bounded (~1 call each)
    for gkey, msgs in groups.items():
        msgs.sort(key=lambda m: float(m.get('ts') or 0))
        last = msgs[-1]
        chan_id = str(last.get('channel') or '')
        chan = last.get('channel_name') or chan_names.get(chan_id) or chan_id
        dm_uid = chan_id if re.fullmatch(r'U[A-Z0-9]+', chan_id) else None
        if not dm_uid:
            m_dm = re.fullmatch(r'DM:?\s*(U[A-Z0-9]+)', chan)
            dm_uid = m_dm.group(1) if m_dm else None
        if chan_id.startswith('D') or dm_uid:
            partner = dm_uid or last.get('author') or ''
            chan = 'DM ' + names.get(partner, partner)
        message_log = [{
            'from': names.get(m.get('author'), m.get('author') or '?'),
            'ts': float(m.get('ts') or 0),
            'text': clean_slack_text(m.get('text') or '', names),
        } for m in msgs]
        # convo triage: reply if ANY message needs one; high if any is high
        verdict, hi = 'fyi', False
        for m, ml in zip(msgs, message_log):
            v, h = triage_slack(m, ml['text'], m.get('author') or '')
            if v == 'reply':
                verdict = 'reply'
            hi = hi or h
        # reply-needed convos get the REAL thread (full text, all participants)
        # instead of the ledger's mention-only 600-char view
        if verdict == 'reply' and fetch_budget > 0:
            full = _fetch_full_conversation(gkey, msgs, names, tok)
            if full:
                message_log = full
                fetch_budget -= 1
        text = '\n'.join(f"[{m['from']}] {m['text']}" for m in message_log)
        last_from = names.get(last.get('author'), last.get('author') or '?')
        # reply target for Approve&kirim: same thread for channels, plain for DMs
        thread_root = last.get('thread_ts') or (None if chan_id.startswith(('D', 'U'))
                                                else last.get('ts'))
        out['slack:conv:' + gkey] = new_item(
            'slack:conv:' + gkey, 'slack',
            ts=float(last.get('ts') or 0),
            from_id=last.get('author') or '', **{'from': last_from},
            channel=chan,
            title=f"{message_log[-1]['text'][:100]}",
            text=text,
            permalink=last.get('permalink') or '',
            triage=verdict, priority_hi=hi,
            messages=message_log, msg_count=len(message_log),
            send_channel=chan_id, send_thread_ts=thread_root,
        )
    return out, f'{len(open_items)} msgs -> {len(out)} conversations'

def _gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    scopes = ['https://www.googleapis.com/auth/gmail.modify']
    creds = Credentials.from_authorized_user_file(GMAIL_TOKEN, scopes)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)

def harvest_gmail():
    """Work-inbox messages from the last 3 days (metadata + snippet only)."""
    if not os.path.exists(GMAIL_TOKEN):
        return {}, 'token_gmail_work.json missing — run gmail-connector auth'
    try:
        import html as _html
        svc = _gmail_service()
        res = svc.users().messages().list(
            userId='me', q=GMAIL_QUERY, maxResults=GMAIL_LIMIT).execute()
        threads = {}
        n_msgs = 0
        for m in res.get('messages', []):
            full = svc.users().messages().get(
                userId='me', id=m['id'], format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = {h['name']: h['value']
                       for h in full.get('payload', {}).get('headers', [])}
            sender = headers.get('From', '')
            threads.setdefault(full.get('threadId') or m['id'], []).append({
                'id': m['id'],
                'from': re.sub(r'\s*<[^>]*>', '', sender).strip().strip('"') or sender,
                'from_raw': sender,
                'ts': float(full.get('internalDate', 0)) / 1000.0,
                'subject': headers.get('Subject', '(no subject)'),
                # snippets arrive HTML-escaped (&#39; etc.) — unescape for display
                'text': _html.unescape(
                    re.sub(r'\s+', ' ', full.get('snippet') or '').strip()),
            })
            n_msgs += 1
        out = {}
        for tid, msgs in threads.items():
            msgs.sort(key=lambda x: x['ts'])
            last = msgs[-1]
            joined = '\n'.join(f"[{x['from']}] {x['text']}" for x in msgs)
            verdict, hi = triage_gmail(last['from_raw'], last['subject'], joined)
            out['gmail:t:' + tid] = new_item(
                'gmail:t:' + tid, 'gmail',
                ts=last['ts'], from_id=last['from_raw'], **{'from': last['from']},
                channel='Work inbox',
                title=last['subject'],
                text=joined,
                permalink=f'https://mail.google.com/mail/u/0/#inbox/{tid}',
                triage=verdict, priority_hi=hi,
                messages=[{'from': x['from'], 'ts': x['ts'], 'text': x['text']}
                          for x in msgs],
                msg_count=len(msgs),
            )
        return out, f'{n_msgs} msgs -> {len(out)} threads (3d window)'
    except Exception as e:
        return {}, f'gmail fetch failed: {e}'

def harvest_gdoc():
    return {}, 'stub — GDoc comment mentions land in phase 2 (Drive comments API)'

def harvest_jira():
    return {}, 'stub — Jira comment mentions land in phase 2 (jira-connector)'

# ------------------------------------------------------------------ sweep --

def cmd_sweep(_args):
    state = load_state()
    now = time.time()
    fresh, sources = {}, {}
    for name, fn in (('slack', harvest_slack), ('gmail', harvest_gmail),
                     ('gdoc', harvest_gdoc), ('jira', harvest_jira)):
        items, note = fn()
        ok = 'failed' not in note and 'missing' not in note and 'unreadable' not in note
        sources[name] = {'ok': ok, 'n': len(items), 'note': note}
        fresh.update(items)

    old = state['items']
    merged = {}
    for iid, it in fresh.items():
        prev = old.get(iid)
        if prev:
            # keep the owner's triage overlay + links + generated draft; refresh the
            # source payload (text/names/triage recompute from the fresh harvest)
            for k in ('status', 'status_changed_at', 'prev_status',
                      'linked_ticket', 'first_seen', 'draft_reply', 'draft_source',
                      'sent_permalink', 'sent_at'):
                it[k] = prev.get(k, it[k])
            # conversation got NEW inbound activity after the owner closed it -> reopen
            # (the counterpart replied again; it needs eyes, and the stale draft
            #  no longer answers the latest message)
            if (it['status'] in ('done', 'ignored')
                    and (it.get('ts') or 0) > (it.get('status_changed_at') or 0)):
                it.update(status='open', prev_status=it['status'],
                          status_changed_at=now, draft_reply=None,
                          draft_source=None)
                it['reopened_by'] = 'new_activity'
        merged[iid] = it

    # carry forward items the sources no longer report:
    #  - done/ignored: kept DONE_RETENTION_DAYS for the undo trail, then pruned
    #  - open but gone (e.g. mention ledger answered it): auto-close as done
    #    (answered at the source) and keep for the retention window
    failed = {n for n, s in sources.items() if not s['ok']}
    for iid, it in old.items():
        if iid in merged:
            continue
        # one-time migration: per-message ids ('slack:C..:ts' / 'gmail:<mid>')
        # were replaced by per-conversation ids — drop the old rows outright
        if ((iid.startswith('slack:') and not iid.startswith('slack:conv:'))
                or (iid.startswith('gmail:') and not iid.startswith('gmail:t:'))):
            continue
        src = it.get('source')
        if src in failed:                       # source down ≠ item resolved
            merged[iid] = it
            continue
        ref = it.get('status_changed_at') or it.get('first_seen') or now
        if it.get('status') in ('done', 'ignored'):
            if now - ref < DONE_RETENTION_DAYS * 86400:
                merged[iid] = it
        elif it.get('status') == 'open':
            if now - ref < GONE_RETENTION_DAYS * 86400:
                it.update(status='done', prev_status='open',
                          status_changed_at=now)
                it['closed_by'] = 'source'      # answered/archived at the source
                merged[iid] = it

    state.update(items=merged, sources=sources, last_sweep=now,
                 last_sweep_wib=datetime.now(WIB).isoformat(timespec='seconds'))
    save_state(state)
    n_open = sum(1 for i in merged.values() if i['status'] == 'open')
    print(f'sweep: {len(merged)} items ({n_open} open) — '
          + ', '.join(f"{n}:{s['n']}{'✓' if s['ok'] else '✗'}" for n, s in sources.items()))

# ---------------------------------------------------------------- actions --

def cmd_set_status(args):
    if args.status not in ('open', 'done', 'ignored'):
        sys.exit('status must be open|done|ignored')
    state = load_state()
    it = state['items'].get(args.item_id)
    if not it:
        sys.exit(f'item not found: {args.item_id}')
    it['prev_status'] = it.get('status')
    it['status'] = args.status
    it['status_changed_at'] = time.time()
    it.pop('closed_by', None)
    save_state(state)
    print(f"{args.item_id} -> {args.status} (was {it['prev_status']})")

def cmd_link(args):
    state = load_state()
    it = state['items'].get(args.item_id)
    if not it:
        sys.exit(f'item not found: {args.item_id}')
    it['linked_ticket'] = args.ticket or None
    save_state(state)
    print(f"linked: {args.item_id} -> {args.ticket or '(cleared)'}")

def cmd_set_draft(args):
    """Store a reply draft on an item (used by the inbox-digest claude run and any
    manual upgrade). --file avoids shell-escaping pain for multi-line drafts."""
    state = load_state()
    it = state['items'].get(args.item_id)
    if not it:
        sys.exit(f'item not found: {args.item_id}')
    if args.file:
        text = open(args.file, encoding='utf-8').read().strip()
    else:
        text = (args.text or '').strip()
    if not text:
        sys.exit('empty draft (need --file or --text)')
    it['draft_reply'] = text
    it['draft_source'] = args.source
    save_state(state)
    print(f'draft set ({args.source}): {args.item_id} ({len(text)} chars)')

def cmd_mark_sent(args):
    """Record an approved+sent reply: item goes done with the sent permalink kept
    for the audit trail. Called by the dashboard after a successful send."""
    state = load_state()
    it = state['items'].get(args.item_id)
    if not it:
        sys.exit(f'item not found: {args.item_id}')
    it['prev_status'] = it.get('status')
    it.update(status='done', status_changed_at=time.time(),
              sent_permalink=args.permalink or None, sent_at=time.time())
    save_state(state)
    print(f'sent+closed: {args.item_id}')

def cmd_draft(_args):
    """Generate short reply drafts for OPEN triage:'reply' items that don't have one
    yet, in ONE batched GLM call via agy-bridge (per the GLM-offload rule: bulk
    generation never burns Claude tokens). Drafts are stored on the item
    (draft_reply) for the dashboard drawer — NEVER sent anywhere. On GLM failure
    prints FALLBACK_TO_CLAUDE and exits 0: the per-item AI copilot stays the manual
    fallback, a broken bridge must not fail the cron chain."""
    import subprocess
    state = load_state()
    todo = [it for it in state['items'].values()
            if it['status'] == 'open' and it.get('triage') == 'reply'
            and not it.get('draft_reply')]
    if not todo:
        print('draft: nothing to draft (all reply-needed items already have one)')
        return
    todo = sorted(todo, key=lambda i: -(i.get('ts') or 0))[:15]
    blocks = []
    for i, it in enumerate(todo):
        blocks.append(f"ITEM {i} (id={it['id']}, from={it['from'] or it['from_id']}, "
                      f"channel={it['channel']}):\n{(it.get('text') or it.get('title') or '')[:600]}")
    prompt = (
        'You draft Slack/email replies for Your Name, a product leader at Work. '
        'Voice: plain flowing prose, professional but warm, no emoji, no bullet lists, '
        '1-3 sentences each, English. If the message asks something the owner cannot answer '
        'without checking, the draft should acknowledge + commit to a concrete next step. '
        'Return ONLY a JSON array, one object per item: '
        '[{"id": "<item id>", "draft": "<reply text>"}]. No commentary, no markdown fences.\n\n'
        + '\n\n'.join(blocks))
    try:
        proc = subprocess.run(
            [sys.executable, AGY_BRIDGE, '--task', 'draft', '--label', 'ai-inbox-digest',
             '--prompt', prompt, '--timeout', '120'],
            capture_output=True, text=True, timeout=180, cwd=BASE_DIR)
        raw = (proc.stdout or '').strip()
        m = re.search(r'\[.*\]', raw, re.S)
        if proc.returncode != 0 or not m:
            print(f'FALLBACK_TO_CLAUDE: bridge rc={proc.returncode}, unparsable output '
                  f'({raw[:120]!r}) — drafts skipped, use the per-item AI copilot')
            return
        drafts = json.loads(m.group(0))
    except Exception as e:
        print(f'FALLBACK_TO_CLAUDE: {e} — drafts skipped')
        return
    by_id = {d.get('id'): (d.get('draft') or '').strip() for d in drafts
             if isinstance(d, dict)}
    n = 0
    for it in todo:
        d = by_id.get(it['id'])
        if d:
            it['draft_reply'] = d
            it['draft_source'] = 'glm'   # placeholder tier — inbox-digest upgrades it
            n += 1
    save_state(state)
    print(f'draft: {n}/{len(todo)} reply drafts generated (GLM)')

def age_str(ts):
    h = (time.time() - float(ts or 0)) / 3600
    return f'{h/24:.1f}d' if h >= 24 else f'{h:.0f}h'

def cmd_report(_args):
    state = load_state()
    items = [i for i in state['items'].values() if i['status'] == 'open']
    items.sort(key=lambda i: -(i.get('ts') or 0))
    icons = {'slack': '💬', 'gmail': '📧', 'gdoc': '📄', 'jira': '🎫'}
    print(f'## 📥 Inbox ({len(items)} open)\n')
    for it in items:
        link = f" [↗]({it['permalink']})" if it.get('permalink') else ''
        tick = f" `{it['linked_ticket']}`" if it.get('linked_ticket') else ''
        print(f"- {icons.get(it['source'], '·')} **{it['from'] or it['channel']}** · "
              f"{age_str(it['ts'])} ago — {it['title'][:120]}{link}{tick}  `{it['id']}`")

# ------------------------------------------------------------------- main --

def main():
    p = argparse.ArgumentParser(description='Unified inbound-inquiry hub')
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('sweep')
    sp = sub.add_parser('set-status')
    sp.add_argument('item_id')
    sp.add_argument('--status', required=True)
    lp = sub.add_parser('link')
    lp.add_argument('item_id')
    lp.add_argument('--ticket', default='')
    sdp = sub.add_parser('set-draft')
    sdp.add_argument('item_id')
    sdp.add_argument('--file', default=None)
    sdp.add_argument('--text', default=None)
    sdp.add_argument('--source', default='claude')
    msp = sub.add_parser('mark-sent')
    msp.add_argument('item_id')
    msp.add_argument('--permalink', default='')
    sub.add_parser('report')
    sub.add_parser('draft')
    args = p.parse_args()
    {'sweep': cmd_sweep, 'set-status': cmd_set_status, 'link': cmd_link,
     'set-draft': cmd_set_draft, 'mark-sent': cmd_mark_sent,
     'report': cmd_report, 'draft': cmd_draft}.get(args.cmd or 'sweep', cmd_sweep)(args)

if __name__ == '__main__':
    main()
