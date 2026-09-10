import os
import hashlib

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"

def get_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

files = os.listdir(ktp_dir)
screenshots = sorted([f for f in files if f.startswith("Screenshot")])
named_files = sorted([f for f in files if not f.startswith("Screenshot")])

print(f"Total Screenshots: {len(screenshots)}")
print(f"Total Named KTP Files: {len(named_files)}")

hash_map = {}
for nf in named_files:
    p = os.path.join(ktp_dir, nf)
    h = get_hash(p)
    hash_map[h] = nf

unmatched_screenshots = []
for ss in screenshots:
    p = os.path.join(ktp_dir, ss)
    h = get_hash(p)
    if h in hash_map:
        print(f"  {ss} == {hash_map[h]}")
    else:
        size = os.path.getsize(p)
        print(f"  {ss} (NEW/UNMATCHED, size={size} bytes)")
        unmatched_screenshots.append((ss, size))

print(f"\nUnmatched Screenshots count: {len(unmatched_screenshots)}")
