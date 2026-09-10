import os

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"

files = os.listdir(ktp_dir)
for f in files:
    if f.startswith("Screenshot"):
        p = os.path.join(ktp_dir, f)
        os.remove(p)
        print(f"Cleaned up duplicate screenshot: {f}")

print("\nUpdated folder content:")
final_files = sorted(os.listdir(ktp_dir))
for f in final_files:
    print(" -", f)
