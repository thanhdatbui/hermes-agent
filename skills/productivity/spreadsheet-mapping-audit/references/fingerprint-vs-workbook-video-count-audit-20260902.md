---
title: Fingerprint Ledger vs Workbook Video Count Audit (Case UI-VIDEO-COUNT-DRIFT-01)
date: 2026-09-02
repos: [Tiktok-video, tiktok-luot nuoi acc]
status: AUDIT_COMPLETED
---

## Problem
Media fingerprint ledger (`D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\*.json`) recorded more verified videos than the `Video Đã Đăng` column in Tik workbooks and `taikhoan_run_safe.xlsx`. This caused duplicate media blocking when workflow tried to post already-posted videos.

## Example Mismatches Found
| File | Machine | Account | Workbook Count | Verified Max |
|------|---------|---------|----------------|--------------|
| Tik1.xlsx | 14 | hong.bo.anh83 | 5 | 13 |
| Tik2.xlsx | 19 | luunhu290719 | 2 | 3 |
| Tik2.xlsx | 23 | .thanh.trc.ng | 1 | 2 |
| tik3.xlsx | 34 | truong.thuy950 | 0 | 5 |
| tik3.xlsx | 69 | quachtieu2106 | 0 | 2 |
| Tik4.xlsx | 37 | thanhlee372 | 0 | 1 |
| taikhoan_run_safe.xlsx | 22 | ngomai.ly | 0 | 16 |
| taikhoan_run_safe.xlsx | 69 | vo.my.hanh94 | 0 | 14 |

## Audit Method (Reusable)
```python
import glob, json, openpyxl

# 1. Load all verified records from fingerprint ledger
fp_files = glob.glob('D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints/*.json')
verified_map = {}  # (machine_str, account_norm) -> {max_vnum, all_vnums}
for f in fp_files:
    d = json.load(open(f, encoding='utf-8'))
    if d.get('status') == 'verified_success' or d.get('post_verified') is True:
        m = str(d.get('machine', '')).strip()
        acc = str(d.get('target_account', '')).strip().lstrip('@').casefold()
        vnum = int(d.get('video_number', 0))
        if m and acc and vnum > 0:
            key = (m, acc)
            # accumulate max and all vnums

# 2. Check each Tik workbook + taikhoan_run_safe.xlsx
for fname in ['Tik1.xlsx', 'Tik2.xlsx', 'tik3.xlsx', 'Tik4.xlsx', 'Tik5.xlsx', 'Tik6.xlsx', 'taikhoan_run_safe.xlsx']:
    wb = openpyxl.load_workbook(fpath, data_only=True)
    ws = wb['TaiKhoan'] if 'TaiKhoan' in wb.sheetnames else wb.active
    for row in range(2, ws.max_row + 1):
        m_val = ws.cell(row=row, column=1).value
        id_val = ws.cell(row=row, column=3).value
        v_val = ws.cell(row=row, column=8).value  # col 4 for safe
        # compare with verified_map

# 3. Report all where max_verified > workbook_count
```

## Root Causes Identified
1. **Upload hook workbook update** (`update_video_number` in `account_source.py`) uses `max(current, requested)` — prevents regression but if upload succeeded externally (manual, another runner), workbook may not be updated.
2. **Multi-repo execution** — upload runs in `Tiktok-video`, feed runs in `tiktok-luot nuoi acc`; workbook sync not guaranteed.
3. **Partial session completion** — session may complete upload but crash before workbook write.

## Recommended Fix
1. Periodic reconciliation script (daily/weekly) that updates workbooks from fingerprint ledger.
2. Make `update_video_number` more robust — always write max, add logging for discrepancy detection.
3. Consider making fingerprint ledger the source of truth for video count.

## Verification
- Total fingerprint records: 1,661
- Verified (machine, account) pairs: 212
- Total mismatches found: 6 (Tik workbooks) + 7 (taikhoan_run_safe.xlsx)
- Machine 40 (nguyenkhoi1403) fixed manually: updated Video Đã Đăng from 1 → 2