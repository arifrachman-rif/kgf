import openpyxl
import os

file_path = "data/Daftar Petani Agroforestry 2026 (1).xlsx"
print("File exists:", os.path.exists(file_path))

wb = openpyxl.load_workbook(file_path, read_only=True)
print("Sheet Names:", wb.sheetnames)

for sheet_name in wb.sheetnames[:5]: # look at the first few sheets
    sheet = wb[sheet_name]
    print(f"\n--- Sheet: {sheet_name} ---")
    # Print first 5 rows
    row_count = 0
    for row in sheet.iter_rows(values_only=True):
        if row_count < 10:
            # truncate cells to avoid huge output if there's long strings
            truncated_row = [str(cell)[:30] if cell is not None else "" for cell in row]
            # filter empty rows
            if any(truncated_row):
                print(truncated_row[:12])
                row_count += 1
        else:
            break
