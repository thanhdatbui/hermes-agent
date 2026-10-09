# Canonical Workbook + Existing Switcher Recovery

## Trigger
Use when a feed runner reports `account-switcher-missing-expected` even though the target may already exist on-device, or when targeted login aborts while resolving a Gmail domain.

## Evidence pattern
- The canonical workbook is `taikhoan_dat_v2_updated .xlsx`; its authoritative account sheet is `Tài Khoản` (or `Accounts` in the runtime workbook).
- Audit/operational sheets such as `Khong Co Trong GmailClean`, `Máy Thiếu Acc`, and `Audit Pending` are not account sources. Loading all worksheets can create duplicate records for one TikTok ID and introduce a stale `email_missing_domain` flag.
- For M72, the canonical row for `m.ngc4624` had a complete Gmail address and TikTok ID/password; the audit sheet contained a duplicate local-part without `@domain`, which incorrectly forced a live-Gmail lookup and aborted login.

## Recovery contract
1. Resolve machine -> serial with the canonical mapping and inspect the live device first.
2. Read only the canonical account sheet for login selection. If duplicate matches still reach `pick_accounts`, prefer the canonical-sheet record and the record without `email_missing_domain`.
3. If the selected record has TikTok ID + password, an absent live Gmail match must not block ID+password login; infer `local_part@gmail.com` only for that path. Keep OTP-only/passwordless paths fail-closed when domain evidence is missing.
4. Before opening the add-account flow, inspect the account switcher for the target TikTok ID or email local-part. If present, tap that row and verify the post-switch profile; do not attempt a second login.
5. Count switcher accounts using both legacy account row IDs and the current `ng8` identity node, excluding the `Thêm tài khoản` row. This prevents false capacity decisions on current TikTok layouts.
6. Run a focused unit suite before any live canary. Then run the canary only after VPN/tun0 evidence is positive, capture pre/post screenshots, and verify the feed post-condition (profile switched + swipes completed).

## Verified test shape
The focused regression set should cover:
- canonical-sheet filtering;
- duplicate selection preference;
- ID+password domain fallback;
- OTP-only fail-closed behavior;
- existing-switcher target detection;
- auth-landing package filtering.

A passing canary is not just process exit 0: require a fresh machine inspection, screenshot artifact, and runner summary with `status: success`, `profile_preflight: success`, and `total_swipes_completed > 0`.
