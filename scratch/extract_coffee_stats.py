import openpyxl

file_path = "data/Daftar Petani Agroforestry 2026 (1).xlsx"
wb = openpyxl.load_workbook(file_path, data_only=True)

if 'Pendapataan Rataan Petani' in wb.sheetnames:
    sheet = wb['Pendapataan Rataan Petani']
    print("--- Detailed Coffee Production and Income data per Village (Sheet: Pendapataan Rataan Petani) ---")
    for r in sheet.iter_rows(values_only=True):
        # Print if there is any data in the row
        if any(r):
            row_clean = [str(x).strip() if x is not None else "" for x in r]
            print(row_clean[:10])

# Let's also look at 'Pembelian Lada' or 'Summary' if there's any coffee or agroforestry notes
if 'Summary' in wb.sheetnames:
    sheet = wb['Summary']
    print("\n--- Summary Columns ---")
    # print first row to check columns
    for r in sheet.iter_rows(values_only=True):
        print([str(x) if x is not None else "" for x in r][:15])
        break
