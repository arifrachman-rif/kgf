#!/usr/bin/env python3
"""Build journal/state/insights.json for the dashboard Insights tab.

Pulls recent Fathom meetings (with default_summary + action_items), maps them to real meeting
names via journal/fathom_registry.json, and uses GLM 5.2 (agy-bridge --task draft, local/cheap)
to condense each into 2-3 crisp takeaways. The dashboard reads the cached JSON (fast); re-run
this nightly (or on demand) to refresh. No Claude quota used.

Usage: python3 .agent/scripts/build_insights.py [--limit 8]
"""
import argparse
import ast
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FATHOM = os.path.join(REPO, ".agent/skills/fathom-connector/scripts/fathom_client.py")
REGISTRY = os.path.join(REPO, "journal", "fathom_registry.json")
OUT = os.path.join(REPO, "journal", "state", "insights.json")
BRIDGE = os.path.join(REPO, ".agent/skills/agy-bridge/run.py")

def _fathom_full():
    p = subprocess.run([sys.executable, FATHOM, "--action", "list", "--full"],
                       cwd=REPO, capture_output=True, text=True, timeout=120)
    txt = p.stdout
    i = txt.find("[\n")
    return json.loads(txt[i:]) if i >= 0 else []

def _registry_map():
    if not os.path.exists(REGISTRY):
        return {}
    reg = json.load(open(REGISTRY, encoding="utf-8"))
    items = reg.values() if isinstance(reg, dict) else reg
    return {str(r.get("recording_id")): r for r in items}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    meetings = _fathom_full()[: args.limit]
    regmap = _registry_map()
    # build a compact prompt for GLM: one batched call -> per-meeting takeaways
    blocks = []
    meta = []
    for m in meetings:
        rid = str(m.get("recording_id"))
        reg = regmap.get(rid, {})
        name = reg.get("matched_meeting") or m.get("meeting_title") or "(untitled)"
        summary = str(m.get("default_summary") or "")[:1200]
        # action_items may be a stringified list
        ai = m.get("action_items")
        if isinstance(ai, str):
            try:
                ai = ast.literal_eval(ai)
            except Exception:
                ai = []
        actions = "; ".join(a.get("description", "") for a in (ai or []) if isinstance(a, dict))[:600]
        meta.append({"id": rid, "meeting": name, "client": reg.get("client", ""),
                     "project": reg.get("project", ""), "date": reg.get("date_wib", m.get("recording_start_time", "")[:10]),
                     "url": m.get("url", "")})
        blocks.append(f"### MEETING {rid}: {name}\nSUMMARY: {summary}\nACTIONS: {actions}")

    prompt = (
        "For each meeting below, output 2-3 crisp takeaway bullets (decisions/status, not fluff) "
        "and keep the concrete action items. Output ONLY a JSON object mapping the meeting id (string) "
        'to {"takeaways":[...], "action_items":[...]}. No prose.\n\n' + "\n\n".join(blocks)
    )
    pf = os.path.join("/tmp", "insights_prompt.txt")
    open(pf, "w", encoding="utf-8").write(prompt)
    # z.ai/GLM retired 2026-07-27 (subscription no longer active). Let agy-bridge
    # walk its own chain, which now heads with Gemini via the agy CLI.
    p = subprocess.run([sys.executable, BRIDGE, "--task", "draft",
                        "--prompt-file", pf],
                       cwd=REPO, capture_output=True, text=True, timeout=180)
    out = p.stdout.strip()
    # GLM may wrap in fences; extract the JSON object
    s, e = out.find("{"), out.rfind("}")
    glm = {}
    try:
        glm = json.loads(out[s:e + 1]) if s >= 0 else {}
    except Exception:
        glm = {}

    insights = []
    for mt in meta:
        g = glm.get(mt["id"], {})
        insights.append({**mt,
                         "takeaways": g.get("takeaways", []),
                         "action_items": g.get("action_items", [])})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"meetings": insights}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {OUT}: {len(insights)} meetings ({sum(1 for i in insights if i['takeaways'])} with model takeaways)")

if __name__ == "__main__":
    main()
