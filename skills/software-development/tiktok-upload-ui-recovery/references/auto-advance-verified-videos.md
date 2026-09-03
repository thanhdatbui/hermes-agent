# AUTO-ADVANCE Verified Videos — Prevent DUPLICATE_MEDIA_BLOCKED at Source

## Context
When `Video Đã Đăng` in workbook (TikN.xlsx / taikhoan_run_safe.xlsx) falls behind the media-fingerprint ledger:
- Next session calculates `video_number = workbook_count + 1`
- Resolved video already has `verified_success` in ledger → `DUPLICATE_MEDIA_BLOCKED`
- Session halts at `MANUAL_REVIEW`, fires Telegram alert

Instead of waiting for cron to fix, **auto-advance at RESOLVE_NEXT_VIDEO** prevents the halt entirely.

## Implementation: `_handle_resolve_next_video` patch (2026-09-02)

Location: `D:/Taadaa/tiktok-video/scripts/tiktok_workflow/state_machine.py`

```python
# After resolving video_path, before _backfill_completed_receipt_fingerprints():
if not self.context.dry_run and not self.context.config.get("upload_flow_smoke") is True:
    if not self._auto_advance_verified_videos():
        return False
```

New method `_auto_advance_verified_videos()`:
```python
def _auto_advance_verified_videos(self) -> bool:
    """Skip already-verified videos and auto-advance to the next unposted one.
    Also updates workbook cursor to prevent future DUPLICATE_MEDIA_BLOCKED.
    """
    runtime_root = self.context.config.get("runtime_root")
    machine = self.context.config.get("machine")
    account = self._fingerprint_target_account()
    folder = (self.context.account_row or {}).get("Folder Video")
    source_root = self.context.config.get("video_source_root")
    if not (runtime_root and machine and account and folder and source_root):
        return True

    try:
        ledger = MediaFingerprintLedger(runtime_root)
        max_checked = 50  # safety cap
        advanced = 0
        current_video_number = int(self.context.video_number or 0)

        for _ in range(max_checked):
            # Resolve candidate video path
            try:
                candidate_path = resolve_video_path(
                    Path(source_root), folder, current_video_number
                )
            except Exception:
                break

            if not candidate_path.is_file():
                break

            # Check ledger for verified_success on exact SHA-256
            sha256 = ledger.sha256_file(candidate_path)
            machine_value, account_value, key = ledger._identity_key(machine, account, sha256)
            entry_path = ledger._entry_path(key)

            if entry_path.exists():
                try:
                    entry = ledger._read_entry(entry_path)
                    if str(entry.get("status", "")).casefold() == "verified_success":
                        logger.info(
                            f"[AUTO-ADVANCE] Video {current_video_number} already verified "
                            f"(sha={sha256[:12]}...), advancing..."
                        )
                        current_video_number += 1
                        advanced += 1
                        continue
                except Exception:
                    pass
            break  # not verified, stop advancing

        if advanced > 0:
            new_video_number = current_video_number
            logger.info(
                f"[AUTO-ADVANCE] Skipped {advanced} verified video(s); "
                f"new video_number={new_video_number} (was {self.context.video_number})"
            )
            self.context.video_number = new_video_number

            # Proactively sync workbook cursor
            if self.context.account_source:
                try:
                    self.context.account_source.update_video_number(new_video_number)
                    logger.info(
                        f"[AUTO-ADVANCE] Workbook cursor synced to {new_video_number}"
                    )
                except Exception as e:
                    logger.warning(f"[AUTO-ADVANCE] Workbook sync failed: {e}")

    except Exception as e:
        logger.warning(f"[AUTO-ADVANCE] Check failed: {e}")

    return True
```

## Key Design Points

| Aspect | Decision |
|--------|----------|
| Safety cap | 50 iterations max (prevent infinite loop on corrupted folder) |
| Skip conditions | `dry_run`, `upload_flow_smoke=True` |
| Identity key | `(machine, account, sha256)` — exact file match |
| Verified status | `verified_success` (case-insensitive) |
| Workbook sync | Via `account_source.update_video_number()` — writes to OneDrive TikN.xlsx + local taikhoan_run_safe.xlsx |
| Logging | `[AUTO-ADVANCE]` prefix for grep-ability |

## Cron Auto-Reconcile (Defense in Depth)

Script: `D:/Taadaa/tmp/auto_reconcile_ledger_workbook.py`

Runs every 5 min via cron wrapper (attach to `hermes_taikhoan_sync_cron.py` or standalone):
1. Load all `verified_success` entries from ledger (1664 files as of 2026-09-02)
2. Scan Tik1..Tik6.xlsx + taikhoan_run_safe.xlsx for discrepancies
3. For each `(machine, account)` where `ledger_max > workbook_count`:
   - Backup workbook with timestamp
   - Update `Video Đã Đăng = ledger_max`
   - Verify write succeeded
4. Exit 0 on success, non-zero on failure (cron logs error, stays silent on success)

## Integration with Existing Recovery

This auto-advance **replaces** the old manual flow:
- ❌ Old: Session fails → MANUAL_REVIEW → Alert → User runs fix script → Restart session
- ✅ New: Session auto-advances → Updates workbook → Continues upload → No alert

The cron reconcile is a safety net for edge cases (legacy backfill, cross-machine workbook copy, OneDrive sync lag).

## Testing Checklist

- [ ] Dry-run mode: auto-advance disabled
- [ ] Smoke test: auto-advance disabled
- [ ] Normal run with 1 verified video ahead: advances 1, syncs workbook
- [ ] Normal run with 5 verified videos ahead: advances 5, syncs workbook
- [ ] Video file missing at candidate number: stops advancing (does not skip to next existing)
- [ ] Ledger read error: logs warning, continues with original video_number (fail-open)
- [ ] Workbook write error: logs warning, continues (session proceeds with new video_number in-memory)

## Related References
- `references/duplicate-media-blocked-repair.md` — batch repair workflow (now mostly preventive)
- `references/media-fingerprint-ledger.md` — ledger structure, reserve/stale-release logic