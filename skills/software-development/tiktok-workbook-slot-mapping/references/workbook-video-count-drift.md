# Workbook Video Count Drift — Root Cause & Permanent Fix (2026-09-02)

## Symptoms
- Multiple accounts fail with `[DUPLICATE_MEDIA_BLOCKED]` in `tiktok-video` runs
- Report: `status=MANUAL_REVIEW`, reason: exact SHA-256 already verified for machine/account
- User asks: "Tại sao excel ghi sai hàng loạt" + "làm sao để script k lỗi nữa k bắn về farm alert nữa"

## Root Cause
`Video Đã Đăng` column in workbook (TikN.xlsx = column 8, taikhoan_run_safe.xlsx = column 4) gets out of sync with the media-fingerprint ledger when:

1. **Post-success crash before workbook write**: Session posts video successfully → ledger records `verified_success` → session crashes/MANUAL_REVIEW before calling `account_source.update_video_number()` → workbook counter never increments.

2. **OneDrive sync lag**: Workbook write succeeds locally but OneDrive sync fails silently → next session reads stale version.

3. **Legacy backfill**: Media fingerprint backfilled after video already posted → ledger shows more `verified_success` entries than workbook counter.

**Why it cascades**: Next session calculates `video_number = workbook_count + 1` → resolved video has SHA-256 matching `verified_success` in ledger → `DUPLICATE_MEDIA_BLOCKED` → session halts + Telegram alert.

## Permanent Fix: Two-Layer Defense

### Layer 1: Auto-Advance at RESOLVE_NEXT_VIDEO (Preventive — code change)

**File**: `D:/Taadaa/tiktok-video/scripts/tiktok_workflow/state_machine.py`

Added `_auto_advance_verified_videos()` method to `_handle_resolve_next_video`. When resolving next video:
1. Check ledger for `verified_success` on candidate video SHA-256
2. If found → advance `video_number` to next unposted (cap 50 iterations)
3. Call `account_source.update_video_number(new_video_number)` to sync workbook immediately
4. Continue session — **no halt, no alert**

Full implementation: `references/auto-advance-verified-videos.md` in `tiktok-upload-ui-recovery` skill.

### Layer 2: Cron Auto-Reconcile (Corrective — script)

**Script**: `D:/Taadaa/tmp/auto_reconcile_ledger_workbook.py`

Runs via `hermes_taikhoan_sync_cron.py` after `SYNC_TIK` step:
1. Load all `verified_success` from ledger (~1664 entries, ~2 min)
2. Scan Tik1..Tik6.xlsx + safe workbook for discrepancies (`ledger_max > workbook_count`)
3. For each discrepancy: backup → update → verify
4. Exit 0 on success (silent), non-zero on failure (cron logs)

Integration recipe: `references/2026-09-02-auto-reconcile-ledger-workbook.md` in `tiktok-farm-hermes-cron-migration` skill.

## Data Structure Reference

| File | Sheet | Column | Index |
|------|-------|--------|-------|
| Tik1..Tik6.xlsx | TaiKhoan | C=A (Máy), D=B (Device ID), E=C (ID), F=D (Folder Video), **L=H (Video Đã Đăng)** | 8 |
| taikhoan_run_safe.xlsx | active | A=May, B=Device ID, C=ID, **D=Video Đã Đăng** | 4 |

## Verification After Fix

```python
# Quick check one account
import openpyxl
wb = openpyxl.load_workbook('D:/OneDrive/TaadaaData/kibe/Tik2.xlsx', data_only=True)
ws = wb['TaiKhoan']
for row in ws.iter_rows(values_only=True):
    if row[0] == 40:
        print(f"M{row[0]} {row[2]} Video={row[7]}")  # row[7] = column 8

# Full scan
# python D:/Taadaa/tmp/auto_reconcile_ledger_workbook.py
```

## Accounts Affected (2026-09-02)

7 discrepancies found and fixed:
- Tik1 M14 hong.bo.anh83: 5→13
- Tik2 M19 luunhu290719: 2→3
- Tik2 M20 francesuhunt5: 4→5
- Tik2 M23 .thanh.trc.ng: 1→2
- Tik3 M34 truong.thuy950: 0→5
- Tik3 M69 quachtieu2106: 0→2
- Tik4 M37 thanhlee372: 0→1