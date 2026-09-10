import os
import zipfile
import shutil

ktp_target = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_target = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"
downloads_dir = "/mnt/c/Users/rifra/Downloads"

os.makedirs(ktp_target, exist_ok=True)
os.makedirs(kk_target, exist_ok=True)

print("--- CHECKING ZIP ARCHIVES FOR MISSING FILES ---")

# Inspect KTP zip
ktp_zip = os.path.join(downloads_dir, "KTP Enum Mutiara.zip")
if os.path.exists(ktp_zip):
    print(f"Reading {ktp_zip}...")
    with zipfile.ZipFile(ktp_zip, 'r') as z:
        for member in z.namelist():
            if not member.endswith('/'):
                filename = os.path.basename(member)
                if filename:
                    target_file = os.path.join(ktp_target, filename)
                    if not os.path.exists(target_file):
                        print(f"  Extracting missing KTP: {filename}")
                        with z.open(member) as src, open(target_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)

# Inspect KK zip
kk_zip = os.path.join(downloads_dir, "KK Enum Mutiara.zip")
if os.path.exists(kk_zip):
    print(f"Reading {kk_zip}...")
    with zipfile.ZipFile(kk_zip, 'r') as z:
        for member in z.namelist():
            if not member.endswith('/'):
                filename = os.path.basename(member)
                if filename:
                    target_file = os.path.join(kk_target, filename)
                    if not os.path.exists(target_file):
                        print(f"  Extracting missing KK: {filename}")
                        with z.open(member) as src, open(target_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)

# Check standalone KTP Arif
arif_ktp = os.path.join(downloads_dir, "KTP Arif .jpeg")
if os.path.exists(arif_ktp):
    dest = os.path.join(ktp_target, "Arif Rahman (Original).jpeg")
    if not os.path.exists(dest):
        shutil.copy2(arif_ktp, dest)
        print(f"Copied standalone Arif KTP to {dest}")

print("\n--- FINAL INVENTORY ---")
ktp_final = sorted(os.listdir(ktp_target))
kk_final = sorted(os.listdir(kk_target))

print(f"KTP Enum Mutiara ({len(ktp_final)} files):")
for f in ktp_final:
    print("  -", f)

print(f"\nKK Enum Mutiara ({len(kk_final)} files):")
for f in kk_final:
    print("  -", f)
