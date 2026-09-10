import os

search_paths = [
    "/mnt/c/Users/rifra/Downloads",
    "/mnt/c/Users/rifra/Documents",
    "/mnt/c/Users/rifra/Desktop",
    "."
]

print("--- SEARCHING FOR MUTIARA MEETING RECORDINGS / FILES ---")
found_files = []

keywords = ["mutiara", "yayasan", "weekly"]

for s_path in search_paths:
    for root, dirs, files in os.walk(s_path):
        if ".git" in root or ".venv" in root or "node_modules" in root or ".system_generated" in root:
            continue
        for f in files:
            f_lower = f.lower()
            if any(k in f_lower for k in keywords):
                full_path = os.path.join(root, f)
                found_files.append((full_path, os.path.getsize(full_path)))

print(f"Found {len(found_files)} candidate files:")
for path, size in sorted(found_files, key=lambda x: x[1], reverse=True)[:30]:
    print(f"  [{size/1024/1024:.2f} MB] {path}")
