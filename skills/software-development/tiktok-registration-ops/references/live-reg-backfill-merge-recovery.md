# Live reg backfill: VERIFIED_SUCCESS vs workbook merge

## Verified facts from a real run
A targeted M3/Row 8 TikTok registration produced:
- `all_results.json` status `SUCCESS`, `final_state` `VERIFIED_SUCCESS`.
- Per-target result JSON containing `tiktok_id`, `proof_xml`, and `proof_screenshot` paths.
- The physical workbook merge then failed at `tmp_trk.replace(TRACKING_WORKBOOK)` with Windows `PermissionError: [WinError 5]`, while the merged payload remained in `taikhoan_dat_v2_updated .tmp.xlsx`.

## Recovery protocol
1. Do not rerun registration or touch ADB when the result JSON and proof files already verify success.
2. Keep the `.tmp.xlsx` and create/retain the pre-write backup.
3. Reconcile the temporary workbook once using a controlled fallback (for example, copy the prepared temp workbook to the target only after verifying the target is not being concurrently written; otherwise wait for the official single-writer path).
4. Read back the exact machine/row in both `taikhoan_dat_v2_updated .xlsx` and `taikhoan_run_safe.xlsx`.
5. Report `DONE` only when registration proof and both workbook readbacks pass; otherwise report `BLOCKED` with the exact WinError and artifact paths.

## Common false-positive
A launcher exit code of 0 with `all_results.json: []` or `NO_VERIFIED_RESULT` is not registration success. Keep the target blocked and investigate detector/lock selection instead of claiming completion.