# Targeted Reg-bù Hook: Feed Watchdog

## Trigger contract

A completed Feed watchdog session may classify machines as `skipped-empty` when the active row has no username/account. This classification must be converted into a targeted Reg-bù action only after the session result is finalized.

## Safe implementation pattern

- Parse `run_manifest.json` / `multi_machine_summary` and preserve exact machine STTs.
- Use the existing TikTok Reg launcher; pass only `TIKTOK_REG_TARGET_STTS=<comma-separated STTs>`.
- Do not confuse per-device reconcile/login recovery (`trigger_account_reconcile`, `_maybe_recover_missing_account_via_login`) with creating a new registration target.
- Preflight launcher, `_detect_clean.py`, cluster workbook, and marker path. Empty or invalid inputs must no-op.
- Marker path: `<cluster runtime_root>/cron-state/tiktok-reg-<cluster>-<session_key>.json`.
- Check marker before launch; write marker atomically/before launch when possible so repeated 5-minute watchdog ticks cannot duplicate the batch.

## Verification recipe

1. Run `py_compile` on the watchdog and focused test.
2. Mock `subprocess.Popen`; never execute `_run_all_targets.py`, ADB, or a live farm during unit verification.
3. Assert non-empty input calls once and sets exact `TIKTOK_REG_TARGET_STTS`.
4. Assert the same session key calls zero times on the second invocation and creates the marker.
5. Assert empty input calls zero times.
6. If repository pytest collection is blocked by unrelated dirty-test syntax, report that separately and run a direct mocked probe; do not revert unrelated workspace changes.

## Closeout pitfall

Closeout binding checks may reject a working-tree patch when the target paths overlap files already changed by the current `HEAD`, or when unrelated dirty files are mixed in. Preserve unrelated dirty paths; use an isolated owned commit/worktree or obtain an auditable commit before running the closeout gate. Never claim APPROVED from `py_compile` or a mocked probe alone.