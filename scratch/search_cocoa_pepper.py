import openpyxl

file_path = "data/Daftar Petani Agroforestry 2026 (1).xlsx"
wb = openpyxl.load_workbook(file_path, data_only=True)

print("--- Searching for Cocoa (Kakao) ---")
for s_name in wb.sheetnames:
    sheet = wb[s_name]
    found = False
    for r_idx, r in enumerate(sheet.iter_rows(values_only=True)):
        # Search for 'kakao' or 'cocoa' or 'chocolate' (case-insensitive)
        row_str = " ".join([str(x) for x in r if x is not None]).lower()
        if 'kakao' in row_str or 'cocoa' in row_str:
            if not found:
                print(f"Found in sheet: '{s_name}'")
                found = True
            # print first 3 matches
            print(f"  Line {r_idx+1}: {[str(x)[:25] if x is not None else '' for x in r][:10]}")

print("\n--- Searching for Pepper (Lada) ---")
for s_name in wb.sheetnames:
    sheet = wb[s_name]
    found = False
    for r_idx, r in enumerate(sheet.iter_rows(values_only=True)):
        row_str = " ".join([str(x) for x in r if x is not None]).lower()
        if 'lada' in row_str or 'pepper' in row_str:
            if not found:
                print(f"Found in sheet: '{s_name}'")
                found = True
            print(f"  Line {r_idx+1}: {[str(x)[:25] if x is not None else '' for x in r][:10]}")
