import csv

total = 0.0
items = []

with open('budget_1a._Budget_Cost-based.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) > 4:
            desc = row[0].upper()
            if 'PTKGF' in desc or 'PT KGF' in desc:
                try:
                    val = float(row[4].replace(',', ''))
                    total += val
                    items.append((row[0].strip(), val))
                except ValueError:
                    pass

print(f"Total for PTKGF: EUR {total:,.2f}")
print(f"Number of line items: {len(items)}")
