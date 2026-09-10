import openpyxl
from collections import Counter

file_path = "data/Daftar Petani Agroforestry 2026 (1).xlsx"
wb = openpyxl.load_workbook(file_path, data_only=True)

# 1. Villages distribution in Summary
sheet_summary = wb['Summary']
villages = []
header = None
for r in sheet_summary.iter_rows(values_only=True):
    if not header:
        if 'Farmer Name' in r or any(x == 'Farmer Name' for x in r):
            header = [str(x).strip() if x is not None else "" for x in r]
        continue
    if r[0] is not None and str(r[0]).strip() != "" and any(r[1:]):
        row_dict = dict(zip(header, r))
        v = row_dict.get('Village')
        if v:
            villages.append(str(v).strip())

print("--- Villages in Summary ---")
print(Counter(villages))

# 2. Potensi Kebun Crops
# Columns are starting from header at row 2
sheet_potensi = wb['Potensi kebun']
crops = {}
header1 = None
header2 = None
row_idx = 0
for r in sheet_potensi.iter_rows(values_only=True):
    row_idx += 1
    if row_idx == 1:
        header1 = r
        continue
    if row_idx == 2:
        header2 = [str(x).strip() if x is not None else "" for x in r]
        continue
    # Process rows
    if any(r):
        # The columns for crops: Gamal, Dadap, Lamtoro, Durian, Alpukat are at indices 7, 8, 9, 10, 11
        for idx, val in enumerate(r):
            if idx >= 7 and idx < len(header2) and header2[idx]:
                crop_name = header2[idx]
                if val is not None:
                    try:
                        v_num = float(val)
                        crops[crop_name] = crops.get(crop_name, 0) + v_num
                    except ValueError:
                        pass

print("\n--- Potensi Kebun Crop Sums ---")
for crop, total in crops.items():
    print(f"{crop}: {total:.0f}")

# 3. Pembelian Lada
sheet_pembelian = wb['Pembelian Lada']
pembelian_rows = []
for r in sheet_pembelian.iter_rows(values_only=True):
    if any(r):
        pembelian_rows.append([str(x) if x is not None else "" for x in r])

print("\n--- Pembelian Lada (First 5 Rows) ---")
for r in pembelian_rows[:6]:
    print(r)

# 4. Pendapatan Rataan Petani
sheet_pendapatan = wb['Pendapataan Rataan Petani']
pendapatan_rows = []
for r in sheet_pendapatan.iter_rows(values_only=True):
    if any(r):
        pendapatan_rows.append([str(x) if x is not None else "" for x in r])

print("\n--- Pendapataan Rataan Petani (First 5 Rows) ---")
for r in pendapatan_rows[:8]:
    print(r[:8])
