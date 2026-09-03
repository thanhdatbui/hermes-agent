import os
import json
import openpyxl

# Paths
SOURCE_MASTER_JSON = r"C:\Users\Kibe\AppData\Local\hermes\scripts\checkmail_results\gmail_all_master_results.json"
GMAIL_CLEAN_V2 = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
DEST_DIR = r"D:\OneDrive\TaadaaData\kibe"

# 1. Load current master results
with open(SOURCE_MASTER_JSON, "r", encoding="utf-8") as f:
    master_results = json.load(f)

print(f"Current master results: {len(master_results)} total, {sum(1 for v in master_results.values() if v == 'live')} live")

# 2. Extract and classify all emails from gmail_clean_v2.xlsx
wb = openpyxl.load_workbook(GMAIL_CLEAN_V2, data_only=True)
ws = wb.active

clean_v2_live = set()
clean_v2_die = set()

for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0 or not row:
        continue
    mail = row[1]
    status = str(row[10]).lower() if len(row) > 10 and row[10] is not None else ""
    
    if not mail:
        continue
    cstr = str(mail).strip().lower()
    if not "@" in cstr:
        em = cstr + "@gmail.com"
    else:
        em = cstr
        
    if "@gmail.com" in em:
        # If explicitly marked as die/banned/khoa
        if any(bad in status for bad in ["die", "banned", "khoa", "bi ban", "loi", "invalid"]):
            clean_v2_die.add(em)
            if em not in master_results:
                master_results[em] = "die"
        else:
            # Considered live unless known dead
            clean_v2_live.add(em)
            if em not in master_results or master_results[em] == "live":
                master_results[em] = "live"

print(f"Extracted from gmail_clean_v2: {len(clean_v2_live)} live, {len(clean_v2_die)} die")
print(f"Unified master results: {len(master_results)} total")

# 3. Separate Live & Die
all_live = sorted([k for k, v in master_results.items() if v == "live"])
all_die = sorted([k for k, v in master_results.items() if v != "live"])

print(f" -> Final Total LIVE: {len(all_live)}")
print(f" -> Final Total DIE: {len(all_die)}")

# 4. Write to OneDrive TaadaaData/kibe
live_out_txt = os.path.join(DEST_DIR, "gmail_live_tong.txt")
die_out_txt = os.path.join(DEST_DIR, "gmail_die_tong.txt")
master_out_json = os.path.join(DEST_DIR, "gmail_master_status.json")

with open(live_out_txt, "w", encoding="utf-8") as f:
    f.write("\n".join(all_live) + "\n")

with open(die_out_txt, "w", encoding="utf-8") as f:
    f.write("\n".join(all_die) + "\n")

with open(master_out_json, "w", encoding="utf-8") as f:
    json.dump(master_results, f, indent=2, ensure_ascii=False)

print(f"[+] Da xuat file thanh cong vao {DEST_DIR}:")
print(f" - {live_out_txt} ({len(all_live)} emails)")
print(f" - {die_out_txt} ({len(all_die)} emails)")
print(f" - {master_out_json}")
