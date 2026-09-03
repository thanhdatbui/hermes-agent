#!/usr/bin/env python3
"""
Pre-batch validation: cross-check _clean_targets.json against tracking workbook
to flag machines where detector says "clean" but workbook has pre-existing TikTok accounts.
"""
import json, openpyxl, sys
from pathlib import Path

def load_clean_targets(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def load_tracking_workbook(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    registered = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        try:
            machine = int(row[0])
        except (ValueError, TypeError):
            continue
        tik_id = row[2]  # col C = TikTok ID
        if tik_id and str(tik_id).strip():
            registered[machine] = str(tik_id).strip()
    return registered

def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_clean_targets.py _clean_targets.json taikhoan_dat_v2_updated.xlsx")
        sys.exit(1)
    
    targets_path = Path(sys.argv[1])
    workbook_path = Path(sys.argv[2])
    
    targets = load_clean_targets(targets_path)
    registered = load_tracking_workbook(workbook_path)
    
    conflicts = []
    for t in targets:
        stt = t.get('stt')
        if stt in registered:
            conflicts.append({
                'stt': stt,
                'email': t.get('email'),
                'tik_id': registered[stt],
                'reason': 'Workbook has TikTok ID but detector reported clean target'
            })
    
    if conflicts:
        print(f"⚠️  {len(conflicts)} CONFLICTS: detector targets with pre-existing TikTok accounts in workbook")
        for c in conflicts:
            print(f"  STT {c['stt']}: {c['email']} → TikTok ID: {c['tik_id']}")
        sys.exit(1)
    else:
        print("✅ No conflicts: all clean targets verified against workbook")
        sys.exit(0)

if __name__ == '__main__':
    main()