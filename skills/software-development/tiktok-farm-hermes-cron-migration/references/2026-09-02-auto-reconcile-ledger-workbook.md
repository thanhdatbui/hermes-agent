# Auto-Reconcile Ledger ↔ Workbook Integration (2026-09-02)

## Context
Cron `hermes_taikhoan_sync_cron.py` syncs `taikhoan_dat_v2` → `taikhoan_run_safe.xlsx` + Tik1..Tik6.xlsx every 5 minutes. But workbook `Video Đã Đăng` counter can drift behind the media-fingerprint ledger when:
- Upload session crashes after post success but before workbook write
- OneDrive sync lag / file lock on workbook
- Legacy backfill fingerprint added after video posted

Result: Next session picks `video_number = workbook_count + 1` → ledger has `verified_success` for that video → `DUPLICATE_MEDIA_BLOCKED` → `MANUAL_REVIEW` → Telegram alert.

## Two-Layer Defense

### Layer 1: Auto-Advance at RESOLVE_NEXT_VIDEO (Preventive)
**Location**: `D:/Taadaa/tiktok-video/scripts/tiktok_workflow/state_machine.py` → `_handle_resolve_next_video` → `_auto_advance_verified_videos()`

When resolving next video, checks ledger for `verified_success` on candidate video SHA-256. If found:
- Advances `video_number` to next unposted video (cap 50 iterations)
- Calls `account_source.update_video_number(new_video_number)` to sync workbook cursor immediately
- Continues session — **no halt, no alert**

Details: `tiktok-upload-ui-recovery/references/auto-advance-verified-videos.md`

### Layer 2: Cron Auto-Reconcile (Corrective Safety Net)
**Script**: `D:/Taadaa/tmp/auto_reconcile_ledger_workbook.py` (skill: `tiktok-upload-ui-recovery/scripts/auto_reconcile_ledger_workbook.py`)

Runs every 5 min (attach to `hermes_taikhoan_sync_cron.py` after `SYNC_TIK` step):
1. Load all `verified_success` from ledger (~1664 entries)
2. Scan Tik1..Tik6.xlsx + `taikhoan_run_safe.xlsx` for `(machine, account)` where `ledger_max > workbook_count`
3. For each discrepancy:
   - Backup workbook (timestamp)
   - Update `Video Đã Đăng = ledger_max`
   - Verify write
4. Exit 0 on success (silent), non-zero on failure (cron logs)

## Integration Point

In `hermes_taikhoan_sync_cron.py` main(), after `SYNC_TIK` success (line ~148):

```python
# 3. Auto-reconcile ledger vs workbook (defense in depth)
if SYNC_RECONCILE.exists():
    try:
        cmd_rec = [str(PYTHON), str(SYNC_RECONCILE)]
        comp_rec = subprocess.run(cmd_rec, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
        if comp_rec.returncode != 0:
            failed = True
            results.append(f"RECONCILE_FAIL rc={comp_rec.returncode}: {comp_rec.stderr.strip()}")
        elif comp_rec.stdout.strip():
            results.append(f"RECONCILE: {comp_rec.stdout.strip()}")
    except Exception as exc_rec:
        failed = True
        results.append(f"RECONCILE_EXC: {exc_rec}")
```

Where `SYNC_RECONCILE = REPO / "scripts" / "auto_reconcile_ledger_workbook.py"` (copy from skill's `scripts/` to repo's `scripts/`).

## Results (2026-09-02 session)

Fixed 7 discrepancies in single run:
| File | Machine | Account | WB → Fixed |
|------|---------|---------|------------|
| Tik1 | 14 | hong.bo.anh83 | 5 → **13** |
| Tik2 | 19 | luunhu290719 | 2 → **3** |
| Tik2 | 20 | francesuhunt5 | 4 → **5** |
| Tik2 | 23 | .thanh.trc.ng | 1 → **2** |
| Tik3 | 34 | truong.thuy950 | 0 → **5** |
| Tik3 | 69 | quachtieu2106 | 0 → **2** |
| Tik4 | 37 | thanhlee372 | 0 → **1** |

All verified in both OneDrive and local copy.

## Pitfalls

1. **Ledger scan timeout**: 1664 files → ~2 min. Use `glob.glob` + simple JSON parse (no SHA hashing). Script timeout 180s is safe.
2. **Workbook column indices**: Tik files = column 8 (Video Đã Đăng); Safe file = column 4. Hard-coded — verify if schema changes.
3. **Account normalization**: `lstrip('@').casefold()` must match both ledger and workbook format.
4. **OneDrive file lock**: If workbook open in Excel, `openpyxl.save()` may fail. Cron retries next cycle (state signature unchanged on failure).
5. **Legacy backfill entries**: Ledger may have `legacy_backfill: true` — still counts as `verified_success`. Do not filter out.

## Verification

After integration, run manually once:
```bash
python D:/Taadaa/tiktok-luot\ nuoi\ acc/scripts/auto_reconcile_ledger_workbook.py
# Exit 0 = no discrepancies or fixed silently
```

Then trigger cron:
```bash
cronjob action=run job_id=<taikhoan-sync-job-id>
# Check last_status: ok, execution_success: true
```