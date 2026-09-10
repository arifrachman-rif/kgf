import openpyxl

file_path = "data/Daftar Petani Agroforestry 2026 (1).xlsx"
wb = openpyxl.load_workbook(file_path, data_only=True) # data_only=True to evaluate formulas like datedif!

# 1. Summary sheet analysis
sheet_summary = wb['Summary']
farmers_summary = []
header = None
for r in sheet_summary.iter_rows(values_only=True):
    if not header:
        # Check if this row is the header (e.g. contains Farmer Name)
        if 'Farmer Name' in r or any(x == 'Farmer Name' for x in r):
            header = [str(x).strip() if x is not None else "" for x in r]
        continue
    if r[0] is not None and str(r[0]).strip() != "" and any(r[1:]):
        farmers_summary.append(dict(zip(header, r)))

print(f"Total rows in Summary: {len(farmers_summary)}")
if farmers_summary:
    print("Columns in Summary:", list(farmers_summary[0].keys()))

# 2. Petani Agroforestry sheet analysis
sheet_petani = wb['Petani Agroforestry']
farmers_detail = []
p_header = None
for r in sheet_petani.iter_rows(values_only=True):
    # Find the row containing 'Farmer Database ID' or 'Name' as header
    if not p_header:
        if 'Name' in r or 'Farmer Database ID' in r:
            p_header = [str(x).strip() if x is not None else "" for x in r]
        continue
    if r[0] is not None and str(r[0]).strip() != "" and any(r[1:]):
        # build dict safely
        row_dict = {}
        for idx, val in enumerate(r):
            if idx < len(p_header):
                row_dict[p_header[idx]] = val
        farmers_detail.append(row_dict)

print(f"Total rows in Petani Agroforestry: {len(farmers_detail)}")
if farmers_detail:
    print("Columns in Petani Agroforestry:", list(farmers_detail[0].keys()))

# 3. Aggregating some stats
# - Gender counts
genders = {}
ages = []
pepper_areas = []
focus_farmers_count = 0
agroforestry_count = 0

for f in farmers_summary:
    gender = f.get('Gender', 'Unknown')
    genders[gender] = genders.get(gender, 0) + 1
    
    age = f.get('Age')
    if age is not None:
        try:
            ages.append(float(age))
        except ValueError:
            pass
            
    area = f.get('Pepper Area (ha)')
    if area is not None:
        try:
            pepper_areas.append(float(area))
        except ValueError:
            pass
            
    is_focus = str(f.get('Focus Farmers')).lower() == 'true'
    if is_focus:
        focus_farmers_count += 1

print("\n--- Summary Stats ---")
print("Gender Distribution in Summary:", genders)
if ages:
    print(f"Age range: {min(ages)} - {max(ages)} years (Average: {sum(ages)/len(ages):.1f})")
if pepper_areas:
    print(f"Total Pepper Area: {sum(pepper_areas):.2f} ha (Average: {sum(pepper_areas)/len(pepper_areas):.2f} ha per farmer)")
print(f"Focus Farmers count in Summary: {focus_farmers_count}")

# Check statuses in Petani Agroforestry
statuses = {}
for f in farmers_detail:
    status = f.get('Status', f.get('Status '))
    if status is not None:
        statuses[status] = statuses.get(status, 0) + 1
print("\nStatuses in Petani Agroforestry:", statuses)

# Let's inspect some of the other sheets like Potensi kebun, nursery, lada
print("\n--- Other sheets summary ---")
for s_name in ['Potensi kebun', 'Kompos Fasility', 'Pembelian Lada', 'Nursery Project']:
    if s_name in wb.sheetnames:
        sheet = wb[s_name]
        non_empty_rows = 0
        for r in sheet.iter_rows(values_only=True):
            if any(r):
                non_empty_rows += 1
        print(f"Sheet '{s_name}': {non_empty_rows} non-empty rows")
