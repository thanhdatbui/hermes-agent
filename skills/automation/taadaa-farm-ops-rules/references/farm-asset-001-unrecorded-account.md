# FARM-ASSET-001 — Unrecorded account / logout safety

## Trigger
Use whenever a TikTok account is visible in a device switcher and someone proposes logout, removal, `pm clear`, app reset, or session deletion.

## Non-negotiable classification
- Every logged-in account is User-owned farm property until proven otherwise.
- `owner_stt == current_stt`: own account; logout forbidden.
- Exactly one registry match and `owner_stt != current_stt`: parasite account; logout is allowed only through the existing guarded logout tool because the User approved parasite cleanup.
- No current-registry match: **UNRECORDED_ASSET / DATA_DESYNC**, not “junk” and not parasite. Logout is forbidden.
- Duplicate owners, malformed registry, uncertain OCR, fuzzy-only match, or contradictory backups: fail closed; logout forbidden.

## Required recovery for an unrecorded account
1. Freeze automation on the machine; do not switch/delete/logout or clear app data.
2. Capture the switcher/profile and OCR the username. Preserve raw OCR and screenshot paths.
3. Trace current workbook, backups, registration logs, deferred tracking results, Gmail/Hotmail allocation records, and machine serial history.
4. If a matching asset is found, backfill only after verifying machine/serial/slot/email identity. Create a timestamped backup and read back both master and safe workbooks.
5. If no match is found, report the evidence and ask User. Never self-decide.
6. Teardown only after evidence capture; do not replace the evidence with a post-cleanup Home screenshot.

## Session-specific evidence
On 2026-09-25, `@annhubvqttr` on Machine 3 was initially misclassified as a parasite because it was absent from the current tracking workbook. Backup/history showed it belonged to Machine 3 and was linked to `an.nhuan.work64541@gmail.com`; it was a legitimate account whose tracking write had been missed. The correct response was backfill and restore, not logout. This case demonstrates why current-registry absence is a data-desync state.

## Implementation guard requirements
The logout execution path must require: exact OCR/readback username, exactly one registry owner, `owner_stt != current_stt`, an audit event before ADB, and a second username verification immediately before confirmation. Any failed condition must raise/return a blocked decision and must not be swallowed.
