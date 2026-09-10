import os

files_to_check = [
    "./scratch/mutiara_transcript_1.md",
    "./scratch/mutiara_transcript_2.md",
    "./scratch/MOM_Yayasan_Mutiara_Nusa_Antara.md",
    "./Clients/Work/meetings/MOM_07262026_Mutiara_scope_alignment.md"
]

for fp in files_to_check:
    print(f"\n==========================================")
    print(f"FILE: {fp}")
    print(f"==========================================")
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            print(f"Total lines: {len(lines)}")
            print("First 15 lines:")
            print("".join(lines[:15]))
    else:
        print("File does not exist.")
