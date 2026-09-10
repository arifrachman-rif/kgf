import os
import json
import re

registry_path = "journal/fathom_registry.json"

if not os.path.exists(registry_path):
    print("Registry json not found!")
    exit(1)

with open(registry_path, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# If dict, extract values or items
if isinstance(raw_data, dict):
    recordings = list(raw_data.values()) if not "recordings" in raw_data else raw_data["recordings"]
elif isinstance(raw_data, list):
    recordings = raw_data
else:
    recordings = []

print(f"Total Fathom items parsed: {len(recordings)}")

# Collect all existing .md files in the repository
existing_md_files = []
for root, dirs, files in os.walk("."):
    if ".git" in root or "node_modules" in root or ".venv" in root or ".system_generated" in root:
        continue
    for file in files:
        if file.endswith(".md"):
            existing_md_files.append(os.path.join(root, file))

# Build lookup text from all md files
md_contents = {}
for path in existing_md_files:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            md_contents[path] = f.read()
    except Exception:
        pass

missing_moms = []
found_moms = []

for item in recordings:
    if isinstance(item, str):
        # item is key or string
        continue
    if not isinstance(item, dict):
        continue
        
    rec_id = str(item.get("recording_id") or item.get("id") or "")
    title = item.get("title") or item.get("topic") or item.get("matched_meeting") or item.get("meeting_name") or "Untitled Meeting"
    date_wib = item.get("date_wib") or item.get("created_at") or item.get("start_time") or item.get("date") or ""
    fathom_url = item.get("fathom_url") or item.get("url") or ""
    client = item.get("client") or "General"
    
    clean_t = re.sub(r'[^a-zA-Z0-9]', ' ', title.lower()).strip()
    words = [w for w in clean_t.split() if len(w) > 3]

    matched_file = None
    for md_path, content in md_contents.items():
        # Check by recording ID
        if rec_id and len(rec_id) > 3 and rec_id in content:
            matched_file = md_path
            break
        # Check by fathom url
        if fathom_url and fathom_url in content:
            matched_file = md_path
            break
        # Check by date and key title words
        date_str = str(date_wib)[:10]
        if date_str and len(date_str) == 10 and date_str in md_path:
            if words and any(w in md_path.lower() for w in words):
                matched_file = md_path
                break

    record_info = {
        "id": rec_id,
        "title": title,
        "date": str(date_wib)[:16],
        "client": client,
        "url": fathom_url,
        "mom_file": matched_file
    }

    if matched_file:
        found_moms.append(record_info)
    else:
        missing_moms.append(record_info)

print(f"\n==========================================")
print(f"RESULTS SUMMARY:")
print(f"==========================================")
print(f"Total Fathom Recordings : {len(found_moms) + len(missing_moms)}")
print(f"Recordings WITH MOM     : {len(found_moms)}")
print(f"Recordings WITHOUT MOM  : {len(missing_moms)}")

print("\n--- RECORDINGS WITHOUT MOM (BELUM ADA MOM) ---")
for idx, r in enumerate(missing_moms, 1):
    print(f"{idx:2d}. [{r['date']}] {r['title']} ({r['client']})")
    if r['url']:
        print(f"    URL: {r['url']}")

print("\n--- RECORDINGS WITH MOM ---")
for idx, r in enumerate(found_moms, 1):
    print(f"{idx:2d}. [{r['date']}] {r['title']} -> {r['mom_file']}")
