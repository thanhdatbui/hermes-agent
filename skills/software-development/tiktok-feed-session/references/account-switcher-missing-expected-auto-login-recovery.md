# Auto-Login Recovery on `account-switcher-missing-expected` in Feed Session Preflight

## Problem
During feed session profile preflight (`verify_and_switch_profile` in `flows/feed_swipe_smoke.py`), if the expected account is not found in the account switcher, the runner encounters `account-switcher-missing-expected`. Previously, this immediately halted the session as `ExitStatus.MANUAL_NEEDED`.

## Recovery Mechanism: `_maybe_recover_missing_account_via_login`
When `account-switcher-missing-expected` occurs:
1. `verify_and_switch_profile` calls `_maybe_recover_missing_account_via_login(ctx, expected_account, ...)`.
2. **Loop Prevention Guard**: Max 1 auto-login attempt per expected account per session via `_auto_login_recovered_accounts` set in `ctx.config`.
3. **Target Resolution**: Resolves `machine_id` from `ctx.config["_machine"]`, `ctx.config["machine"]`, or reverse lookup of ADB serial from `machine_mapping`.
4. **Subprocess Execution**: Invokes `tiktok-log-in/scripts/reconcile_tiktok_accounts.py` via Python interpreter (`D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe` or fallback `sys.executable`) with arguments:
   - `--workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx"`
   - `--machines <machine_id>`
   - `--adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe"`
   - `--source-runner "D:\Taadaa\tiktok-luot nuoi acc"`
   - `--login-project "D:\Taadaa\Tiktok_Reg"`
   - `--login-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"`
   - `--proxy-mapping "D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx"`
   - `--allow-live-reconcile`
   - `--full-scope-takeover`
5. **Re-Verification**: If reconcile exits with `returncode == 0`, `verify_and_switch_profile` re-executes itself to switch into the newly logged in account and continue the feed session smoothly.

## Pitfall: Profile Switch Fallback Anchor vs Header Exclusion
- When excluding unscrolled body elements from top header matching (`_find_sticky_profile_header`), do NOT filter out body elements inside `_profile_switch_fallback_anchor` if the fallback anchor is meant to be used after scroll attempts finish when sticky header is absent.
- Bounding checks on header nodes (e.g. `cy <= 250`, `left >= 300`) belong inside sticky header resolution (`_find_sticky_profile_header`), not fallback identity anchors.
