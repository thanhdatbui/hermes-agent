# Live registration + workbook merge verification

## Proven workflow
- If the user explicitly authorizes live registration and the target device has no active machine/serial lock, run the canonical registration command immediately; do not defer to a recurring watchdog unless scheduling is requested.
- A launcher exit code 0 is not completion proof. Inspect the newest `all_results.json`: require target `status=SUCCESS` and `final_state=VERIFIED_SUCCESS`.
- Read the referenced tracking-result JSON and require the new provider email, TikTok ID, serial, and existing `proof_screenshot` + `proof_xml` files.
- If registration is verified but OneDrive rejects `Path.replace()` with `PermissionError`, preserve the `.tmp.xlsx`, do not rerun registration, and reconcile once with a controlled copy fallback (`shutil.copy2`) followed by removal of the temp file only after the destination is readable.
- Read back both tracking and safe workbooks for the exact machine/slot. Only then report success. Distinguish `VERIFIED_SUCCESS`, `NO_VERIFIED_RESULT`, and `workbook_write=FAILED_SYNC_*`.

## Failure patterns to avoid
- Do not treat `Batch Reg exit code 0` or a worker self-report as success.
- Do not schedule a watchdog or wait for a later feed window when the target is currently unlocked and the user asked to run now.
- Do not rerun device registration merely because workbook merge failed; it risks duplicate registration.
