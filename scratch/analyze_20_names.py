import os
import re

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_dir = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

ktp_raw = sorted(os.listdir(ktp_dir))
kk_raw = sorted(os.listdir(kk_dir))

# Function to clean and extract person name from filename
def clean_ktp_name(filename):
    name = os.path.splitext(filename)[0]
    name = name.replace("_", " ").replace("2", "").strip()
    return name

def clean_kk_name(filename):
    name = os.path.splitext(filename)[0]
    if name.lower().startswith("kk "):
        name = name[3:].strip()
    return name

ktp_names_map = { clean_ktp_name(f): f for f in ktp_raw }
kk_names_map = { clean_kk_name(f): f for f in kk_raw }

print("--- RAW KTP NAMES ---")
for k, v in ktp_names_map.items():
    print(f"  {k} -> {v}")

print("\n--- RAW KK NAMES ---")
for k, v in kk_names_map.items():
    print(f"  {k} -> {v}")
