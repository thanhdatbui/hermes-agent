# ACCOUNT_MISSING: Physical-vs-Workbook Drift Triage

Use this playbook before any logout, account deletion, or login recovery.

## Signal

`[ACCOUNT_SWITCHER_FAILED] ... ACCOUNT_MISSING: expected account was not found` does not prove session loss. The expected username may be stale or wrong in the workbook while TikTok is still authenticated with a different, valid account.

## O(1) evidence sequence

1. Run `python D:/Taadaa/tools/inspect_machine.py <N>` and record serial, model, battery, screen, and current focus.
2. Read the newest run for that serial only: `report.json`, `execution.log`, and the saved switcher/profile screenshots.
3. OCR both surfaces:
   - `account-switcher-profile.png` identifies the active account.
   - `soft-reboot-account_switcher-before.png` identifies the other accounts in the switcher.
   - The active account is normally omitted from the switcher bottom-sheet; total physical accounts = bottom-sheet accounts + active profile account.
4. Compare the physical set with the authoritative workbook/SQLite mapping. Inspect only the machine's rows; do not trust a single workbook.
5. If a physical username is absent from the workbook, trace its historical registration artifact (for example, a `tracking_result_stt<N>_*.json` containing `status=SUCCESS`, serial, and `tiktok_id`) before treating it as foreign.
6. Use `dumpsys account` only to establish whether the relevant Gmail is present for an OTP path. Its absence is supporting evidence for an OTP deadlock, not proof that the TikTok session is missing.

## Decision gates

- **Physical account present, workbook account absent:** classify as mapping/data drift. Freeze the batch; do not logout, clear app data, or auto-login. Repair the source-of-truth mapping only after duplicate/cross-machine checks and approval for any destructive operation.
- **Workbook account absent physically, but device has fewer than 8 accounts and Add account is visible:** this is a candidate for standard login recovery, subject to the normal lock, credential, and visual-evidence gates.
- **Device has 8 physical accounts and Add account is hidden:** classify as full-device drift/possible parasite or stale mapping. Never free a slot automatically; first prove ownership of each account and preserve the physical evidence.
- **Active profile and switcher evidence show TikTok is logged in:** suppress P0 "session lost" wording; report a false-positive session-loss classification separately from the real mapping failure.

## Evidence standard

A canary is not successful merely because the app is foreground or the script exits cleanly. Require a fresh in-app Profile/Switcher screenshot and OCR/readback showing the expected account selection or a corrected mapping outcome. Never send a launcher/home screenshot as proof.
