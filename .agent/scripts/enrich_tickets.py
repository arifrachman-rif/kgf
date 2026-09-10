#!/usr/bin/env python3
"""Enrich journal/state/tickets.json priority + due via GLM 5.2 (conservative, off Claude quota).

The migration defaulted most priorities to P1 with no due dates. This asks GLM to:
- upgrade to P0 ONLY when the title/note clearly signals urgency (blocker, deadline-now, ASAP,
  'today', explicit P0); downgrade to P2 only for clearly low/someday items; else keep.
- set due ONLY when a concrete date is evident in the text; else leave "".
It will NOT invent dates or priorities. Atomic-swap write.

Usage: python3 .agent/scripts/enrich_tickets.py
"""
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TICKETS = os.path.join(REPO, "journal", "state", "tickets.json")
BRIDGE = os.path.join(REPO, ".agent/skills/agy-bridge/run.py")

def main():
    doc = json.load(open(TICKETS, encoding="utf-8"))
    tix = doc.get("tickets", [])
    compact = [{"id": t["id"], "title": t.get("title", ""), "note": t.get("note", ""),
                "priority": t.get("priority", "P1"), "due": t.get("due", "")} for t in tix]
    prompt = (
        "You are triaging tickets. For EACH ticket return its priority and due date. RULES:\n"
        "- priority: 'P0' ONLY if title/note clearly signals urgency (blocker, ASAP, 'today', deadline now, explicit P0/critical). "
        "'P2' only if clearly low/someday/nice-to-have. Otherwise keep the given priority.\n"
        "- due: a date 'YYYY-MM-DD' ONLY if a concrete date/deadline is evident in the text; otherwise empty string. NEVER invent a date.\n"
        "Output ONLY a JSON object mapping id -> {\"priority\":\"P0|P1|P2\",\"due\":\"YYYY-MM-DD|\"}. No prose.\n\n"
        + json.dumps(compact, ensure_ascii=False)
    )
    pf = "/tmp/enrich_prompt.txt"
    open(pf, "w", encoding="utf-8").write(prompt)
    # z.ai/GLM retired 2026-07-27 (subscription no longer active). Let agy-bridge
    # walk its own chain, which now heads with Gemini via the agy CLI.
    p = subprocess.run([sys.executable, BRIDGE, "--task", "draft",
                        "--prompt-file", pf], cwd=REPO, capture_output=True, text=True, timeout=180)
    out = p.stdout.strip()
    s, e = out.find("{"), out.rfind("}")
    try:
        glm = json.loads(out[s:e + 1])
    except Exception as ex:
        print("model JSON parse failed:", ex)
        print(out[:300])
        return
    changed = 0
    for t in tix:
        g = glm.get(t["id"])
        if not g:
            continue
        np, nd = g.get("priority"), g.get("due", "")
        if np in ("P0", "P1", "P2") and np != t.get("priority"):
            t["priority"] = np
            changed += 1
        if nd and nd != t.get("due"):
            t["due"] = nd
            changed += 1
    doc["tickets"] = tix
    tmp = TICKETS + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.load(open(tmp, encoding="utf-8"))  # validate
    os.replace(tmp, TICKETS)
    from collections import Counter
    print(f"enriched: {changed} field changes")
    print("priority now:", dict(Counter(t["priority"] for t in tix)))
    print("with due:", sum(1 for t in tix if t.get("due")))

if __name__ == "__main__":
    main()
