import os
import shutil

search_dirs = [
    "/mnt/c/Users/rifra/Downloads",
    "/mnt/c/Users/rifra/Documents",
    "/mnt/c/Users/rifra/Desktop"
]

ktp_target = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_target = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

os.makedirs(ktp_target, exist_ok=True)
os.makedirs(kk_target, exist_ok=True)

missing_names = ["fadhilah", "kurniawan", "duta", "febi", "taufik", "ruly", "hendro"]

print("--- SCANNING FOR SCATTERED FILES ---")
found_ktp = []
found_kk = []

for s_dir in search_dirs:
    for root, dirs, files in os.walk(s_dir):
        # Skip the target folders themselves to avoid endless recursion
        if root == ktp_target or root == kk_target:
            continue
        for f in files:
            f_lower = f.lower()
            if any(name in f_lower for name in missing_names) or "ktp" in f_lower or "kk" in f_lower:
                full_path = os.path.join(root, f)
                print(f"Found candidate file: {full_path}")
                
                # Check if it's KTP or KK
                if "ktp" in f_lower or ("fadhilah" in f_lower and "kk" not in f_lower):
                    found_ktp.append(full_path)
                elif "kk" in f_lower:
                    found_kk.append(full_path)

print(f"\nFound {len(found_ktp)} candidate KTP files.")
print(f"Found {len(found_kk)} candidate KK files.")
