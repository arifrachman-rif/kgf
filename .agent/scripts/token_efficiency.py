#!/usr/bin/env python3
"""
token_efficiency.py - Continuous-improvement tracker for harness token spend.

Answers: is every workflow/tool/skill getting CHEAPER over time, task type by
task type, and did our optimizations actually move the needle?

Sources (all optional - degrade gracefully, never crash on a missing file):
  journal/state/token_usage.json      - token-tracker sweep state (per-file
                                         summaries with task_type + per-day
                                         tokens/cost; see token_usage.py).
  dashboard-data/agy_usage_log.jsonl  - per-call agy-bridge offload log
                                         (tokens + backend: agy/zai = offloaded
                                         to non-Claude models).
  journal/ai_runs/*.json              - headless run records (tokens_in/
                                         tokens_out/cost_usd when the run
                                         finished with usage attached).

Design: bucket every dated token/cost datum into ISO weeks (Mon-Sun, WIB),
keep the last 8 weeks, group by task_type within each week. "Offloaded" =
agy_usage_log rows with backend != 'claude' (agy/zai backends route to
Gemini/GLM, not Claude).

Subcommands:
  report                        aggregate last 8 ISO weeks, write
                                 journal/state/token_efficiency.json, print a
                                 compact report, call heartbeat.
  log-change --what --files --task-types --expected
                                 append one row to
                                 journal/state/efficiency_changelog.jsonl.
    This is how every future token-saving change gets recorded so the weekly
    report can pair it with the observed delta.

State: journal/state/token_efficiency.json (atomic tmp+replace)
Changelog: journal/state/efficiency_changelog.jsonl (append-only)
Cron (proposed, not installed): Monday 12:50 WIB, see
  .agent/protocols/token_efficiency.md
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOKEN_USAGE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'token_usage.json')
AGY_LOG_PATH = os.path.join(BASE_DIR, 'dashboard-data', 'agy_usage_log.jsonl')
AI_RUNS_DIR = os.path.join(BASE_DIR, 'journal', 'ai_runs')
STATE_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'token_efficiency.json')
CHANGELOG_PATH = os.path.join(BASE_DIR, 'journal', 'state', 'efficiency_changelog.jsonl')
HEARTBEAT = os.path.join(BASE_DIR, '.agent', 'scripts', 'heartbeat.py')

WEEKS_BACK = 8

def _atomic_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def heartbeat(job, status, summary):
    try:
        subprocess.run([sys.executable, HEARTBEAT, '--job', job, '--status', status,
                        '--summary', summary], capture_output=True, text=True, timeout=15)
    except Exception as e:
        print(f'  ! heartbeat failed (non-fatal): {e}', file=sys.stderr)

def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception as e:
        print(f'  ! could not parse {path}: {e}', file=sys.stderr)
        return None

def _load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows

def iso_week(date_str):
    """'YYYY-MM-DD' -> 'YYYY-Www' (ISO week, Mon-Sun)."""
    d = datetime.strptime(date_str, '%Y-%m-%d').date()
    y, w, _ = d.isocalendar()
    return f'{y}-W{w:02d}'

def _week_from_ts(ts_wib):
    try:
        dt = datetime.fromisoformat(ts_wib)
    except Exception:
        return None
    y, w, _ = dt.isocalendar()
    return f'{y}-W{w:02d}'

def _empty_week():
    return {'by_task_type': {}, 'totals': {'tokens': 0, 'cost_usd': 0.0, 'runs': 0,
                                            'offloaded_tokens': 0, 'claude_tokens': 0}}

def _week_bucket(weeks, week):
    return weeks.setdefault(week, _empty_week())

def _task_bucket(week_obj, task_type):
    return week_obj['by_task_type'].setdefault(task_type, {
        'tokens': 0, 'cost_usd': 0.0, 'runs': 0,
        'offloaded_tokens': 0, 'claude_tokens': 0,
    })

def collect_token_usage(weeks, cutoff_week_keys):
    """journal/state/token_usage.json: per-file summaries with task_type +
    per-day {tokens, cost} breakdown. Tokens here are Claude-side (interactive
    + subagent + ai-* sessions), so they all count as 'claude_tokens'."""
    data = _load_json(TOKEN_USAGE_PATH)
    if not data or 'files' not in data:
        return False
    for fname, entry in data['files'].items():
        summary = entry.get('summary') or {}
        task_type = summary.get('task_type') or 'interactive'
        for day, v in (summary.get('days') or {}).items():
            try:
                week = iso_week(day)
            except Exception:
                continue
            if week not in cutoff_week_keys:
                continue
            wk = _week_bucket(weeks, week)
            tt = _task_bucket(wk, task_type)
            tokens = v.get('tokens', 0)
            cost = v.get('cost', 0.0)
            tt['tokens'] += tokens
            tt['cost_usd'] += cost
            tt['claude_tokens'] += tokens
            wk['totals']['tokens'] += tokens
            wk['totals']['cost_usd'] += cost
            wk['totals']['claude_tokens'] += tokens
        # runs (sessions) are per-file, attribute to the file's first day
        first_epoch = summary.get('first_epoch')
        if first_epoch:
            day = datetime.fromtimestamp(first_epoch, WIB).strftime('%Y-%m-%d')
            try:
                week = iso_week(day)
            except Exception:
                week = None
            if week in cutoff_week_keys:
                wk = _week_bucket(weeks, week)
                tt = _task_bucket(wk, task_type)
                tt['runs'] += 1
                wk['totals']['runs'] += 1
    return True

def collect_agy_log(weeks, cutoff_week_keys):
    """dashboard-data/agy_usage_log.jsonl: per-call offload log. backend
    agy/zai = routed to a non-Claude model (Gemini/GLM); counts as offloaded
    tokens, not Claude tokens."""
    rows = _load_jsonl(AGY_LOG_PATH)
    if not rows:
        return False
    for r in rows:
        week = _week_from_ts(r.get('ts_wib', ''))
        if week is None or week not in cutoff_week_keys:
            continue
        task_type = r.get('label') or r.get('task') or 'offload'
        tokens = (r.get('input_tokens') or 0) + (r.get('output_tokens') or 0)
        cost = r.get('actual_usd') or 0.0
        backend = r.get('backend') or ''
        wk = _week_bucket(weeks, week)
        tt = _task_bucket(wk, task_type)
        tt['tokens'] += tokens
        tt['cost_usd'] += cost
        tt['runs'] += 1
        wk['totals']['tokens'] += tokens
        wk['totals']['cost_usd'] += cost
        wk['totals']['runs'] += 1
        if backend and backend != 'claude':
            tt['offloaded_tokens'] += tokens
            wk['totals']['offloaded_tokens'] += tokens
        else:
            tt['claude_tokens'] += tokens
            wk['totals']['claude_tokens'] += tokens
    return True

def collect_ai_runs(weeks, cutoff_week_keys):
    """journal/ai_runs/*.json: headless runs. tokens_in/tokens_out/cost_usd
    only present once the run finished with usage attached; runs without it
    still count toward 'runs' but not tokens/cost."""
    paths = glob.glob(os.path.join(AI_RUNS_DIR, '*.json'))
    if not paths:
        return False
    for p in paths:
        d = _load_json(p)
        if not d:
            continue
        started = d.get('started_wib')
        if not started:
            continue
        week = _week_from_ts(started)
        if week is None or week not in cutoff_week_keys:
            continue
        task_type = f"ai-{d.get('kind', 'run')}"
        wk = _week_bucket(weeks, week)
        tt = _task_bucket(wk, task_type)
        tt['runs'] += 1
        wk['totals']['runs'] += 1
        tokens = (d.get('tokens_in') or 0) + (d.get('tokens_out') or 0)
        cost = d.get('cost_usd') or 0.0
        if tokens:
            tt['tokens'] += tokens
            tt['claude_tokens'] += tokens
            wk['totals']['tokens'] += tokens
            wk['totals']['claude_tokens'] += tokens
        if cost:
            tt['cost_usd'] += cost
            wk['totals']['cost_usd'] += cost
    return True

def _sorted_week_keys():
    """Last WEEKS_BACK ISO week keys ending with the current week, oldest first."""
    today = datetime.now(WIB).date()
    keys = []
    seen = set()
    d = today
    while len(keys) < WEEKS_BACK:
        y, w, _ = d.isocalendar()
        k = f'{y}-W{w:02d}'
        if k not in seen:
            keys.append(k)
            seen.add(k)
        d -= timedelta(days=7)
    return list(reversed(keys))

def build_report():
    week_keys = _sorted_week_keys()
    cutoff = set(week_keys)
    weeks = {}
    sources_ok = {
        'token_usage': collect_token_usage(weeks, cutoff),
        'agy_log': collect_agy_log(weeks, cutoff),
        'ai_runs': collect_ai_runs(weeks, cutoff),
    }

    week_list = []
    for k in week_keys:
        wk = weeks.get(k, _empty_week())
        totals = wk['totals']
        offload_pct = (round(100.0 * totals['offloaded_tokens'] /
                              (totals['offloaded_tokens'] + totals['claude_tokens']), 1)
                       if (totals['offloaded_tokens'] + totals['claude_tokens']) else 0.0)
        by_task_type = {}
        for tt_name, tt in sorted(wk['by_task_type'].items(), key=lambda kv: -kv[1]['tokens']):
            by_task_type[tt_name] = {
                'tokens': tt['tokens'],
                'cost_usd': round(tt['cost_usd'], 4),
                'runs': tt['runs'],
                'offloaded_tokens': tt['offloaded_tokens'],
                'claude_tokens': tt['claude_tokens'],
            }
        week_list.append({
            'week': k,
            'by_task_type': by_task_type,
            'totals': {
                'tokens': totals['tokens'],
                'cost_usd': round(totals['cost_usd'], 4),
                'runs': totals['runs'],
                'offloaded_share_pct': offload_pct,
            },
        })

    # Hotspots: top 3 task types by tokens in the most recent populated week.
    hotspots = []
    latest_populated = next((w for w in reversed(week_list) if w['totals']['tokens']), None)
    if latest_populated:
        ranked = sorted(latest_populated['by_task_type'].items(), key=lambda kv: -kv[1]['tokens'])[:3]
        for name, v in ranked:
            why = f"{v['tokens']:,} tokens / {v['runs']} runs in {latest_populated['week']}"
            if v['claude_tokens'] and v['offloaded_tokens'] == 0:
                why += ' - no agy-bridge offload observed, worth a look'
            hotspots.append({'task_type': name, 'tokens': v['tokens'], 'why': why})

    # Recent changelog entries (last 14 days) paired with the observed delta
    # for their week vs the prior week (by total tokens across their task types).
    changes_recent = []
    fourteen_days_ago = datetime.now(WIB) - timedelta(days=14)
    for row in _load_jsonl(CHANGELOG_PATH):
        try:
            ts = datetime.fromisoformat(row.get('ts_wib', ''))
        except Exception:
            continue
        if ts < fourteen_days_ago:
            continue
        change_week = f'{ts.isocalendar()[0]}-W{ts.isocalendar()[1]:02d}'
        idx = next((i for i, w in enumerate(week_list) if w['week'] == change_week), None)
        delta = None
        if idx is not None and idx > 0:
            task_types = row.get('task_types') or []
            cur = sum(week_list[idx]['by_task_type'].get(t, {}).get('tokens', 0) for t in task_types)
            prev = sum(week_list[idx - 1]['by_task_type'].get(t, {}).get('tokens', 0) for t in task_types)
            if prev:
                delta = round(100.0 * (cur - prev) / prev, 1)
        changes_recent.append({
            'ts_wib': row.get('ts_wib'),
            'what': row.get('what'),
            'task_types': row.get('task_types'),
            'week': change_week,
            'observed_delta_pct': delta,
        })

    state = {
        'generated_at': datetime.now(WIB).isoformat(timespec='seconds'),
        'weeks': week_list,
        'hotspots': hotspots,
        'changes_recent': changes_recent,
        'sources_ok': sources_ok,
    }
    return state

def print_report(state):
    weeks = state['weeks']
    populated = [w for w in weeks if w['totals']['tokens']]
    if not populated:
        print('token-efficiency: no data in the last 8 weeks yet (new install or sources empty).')
        return

    print(f"token-efficiency report - last {len(weeks)} ISO weeks (generated {state['generated_at']})")
    print()
    last = weeks[-1]
    prev = weeks[-2] if len(weeks) > 1 else None
    print(f"  This week ({last['week']}): {last['totals']['tokens']:,} tokens, "
          f"${last['totals']['cost_usd']:.2f}, {last['totals']['runs']} runs, "
          f"{last['totals']['offloaded_share_pct']}% offloaded")
    if prev and prev['totals']['tokens']:
        delta = round(100.0 * (last['totals']['tokens'] - prev['totals']['tokens']) / prev['totals']['tokens'], 1)
        sign = '+' if delta >= 0 else ''
        print(f"  vs prior week ({prev['week']}): {sign}{delta}% tokens")
    print()

    if state['hotspots']:
        print('  Top hotspots:')
        for h in state['hotspots']:
            print(f"    - {h['task_type']}: {h['why']}")
        print()

    if state['changes_recent']:
        print('  Changes logged in the last 14 days:')
        for c in state['changes_recent']:
            delta = c['observed_delta_pct']
            delta_str = f"{delta:+.1f}% tokens ({c['week']})" if delta is not None else 'no comparison week yet'
            print(f"    - {c['ts_wib']}: {c['what'][:80]} -> {delta_str}")
    else:
        print('  No changes logged in the last 14 days.')

    for name, ok in state['sources_ok'].items():
        if not ok:
            print(f"  ! source unavailable: {name}")

def cmd_report(args):
    state = build_report()
    _atomic_write(STATE_PATH, state)
    print_report(state)
    populated = [w for w in state['weeks'] if w['totals']['tokens']]
    if populated:
        last = populated[-1]
        summary = f"{last['week']}: {last['totals']['tokens']:,} tok, {len(state['hotspots'])} hotspots"
    else:
        summary = 'no data in window'
    heartbeat('token-efficiency', 'ok', summary)
    return 0

def cmd_log_change(args):
    row = {
        'ts_wib': datetime.now(WIB).isoformat(timespec='seconds'),
        'what': args.what,
        'files': [f.strip() for f in args.files.split(',') if f.strip()],
        'task_types': [t.strip() for t in args.task_types.split(',') if t.strip()],
        'expected_effect': args.expected,
    }
    os.makedirs(os.path.dirname(CHANGELOG_PATH), exist_ok=True)
    with open(CHANGELOG_PATH, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps(row, ensure_ascii=False, indent=2))
    return 0

def main():
    ap = argparse.ArgumentParser(description='Token-efficiency continuous-improvement tracker')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p_report = sub.add_parser('report', help='aggregate last 8 ISO weeks + print report')
    p_report.set_defaults(func=cmd_report)

    p_log = sub.add_parser('log-change', help='record a token-saving optimization')
    p_log.add_argument('--what', required=True, help='what changed, one line')
    p_log.add_argument('--files', required=True, help='comma-separated files touched')
    p_log.add_argument('--task-types', required=True, help='comma-separated task types affected')
    p_log.add_argument('--expected', required=True, help='expected effect, one line')
    p_log.set_defaults(func=cmd_log_change)

    args = ap.parse_args()
    sys.exit(args.func(args))

if __name__ == '__main__':
    main()
