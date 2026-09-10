import os

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_dir = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

ktp_files = sorted(os.listdir(ktp_dir)) if os.path.exists(ktp_dir) else []
kk_files = sorted(os.listdir(kk_dir)) if os.path.exists(kk_dir) else []

print(f"KTP Files ({len(ktp_files)}):")
for f in ktp_files:
    print("  -", f)

print(f"\nKK Files ({len(kk_files)}):")
for f in kk_files:
    print("  -", f)
