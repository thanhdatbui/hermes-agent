# Farm Account Preservation & Anti-Ghost Logout (2026-09-25)

## Incident lesson
A TikTok account present on a device but absent from the current tracking workbook is **not** evidence that it is a parasite. In the investigated case, `@annhubvqttr` was a legitimate Machine 3 account whose registration write-back was missed; historical Gmail/2FA records and device evidence recovered its identity.

## Hard rule
- Treat every account visible in a device Account Switcher as Farm property until disproven.
- Never logout, delete, or clear an account merely because its username is missing from the current Excel/database.
- Classify an account as `parasite` only after proving it belongs to another machine: matching username/email/serial mapping in authoritative data, plus readback evidence.

## Required recovery sequence
1. Capture the live Account Switcher and record the exact username.
2. Check the authoritative tracking workbook, safe workbook, Gmail inventory, backups, deferred tracking results, and targeted registration logs for the username/email.
3. If identity is recovered, backfill the correct machine/slot, create a timestamped backup, sync `taikhoan_run_safe.xlsx`, and verify both workbooks plus `get_missing_machines_for_row(8)`.
4. If identity cannot be recovered, stop and ask the user. Do not remove the account.
5. Only after a positive cross-machine ownership proof may the canonical logout tool be used.

## Canonical tooling rule
Do not create ad-hoc `logout_mX.py` scripts. Use the existing canonical tool (`D:/Taadaa/tools/do_logout_account.py` or `run_logout_all.py`) only after the parasite proof gate passes.

## Evidence/reporting
Separate `confirmed`, `unproven`, and `hypothesis`. A worker summary is not proof. For UI changes, require a fresh Account Switcher screenshot before teardown; never use Settings/Home alone as proof of account inventory.
