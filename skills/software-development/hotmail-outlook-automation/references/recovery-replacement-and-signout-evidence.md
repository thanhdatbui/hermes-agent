# Recovery-email replacement and sign-out evidence contract

## Do not conflate workflows

A password-change flow may use the recovery address Microsoft already presents to obtain an OTP. That is authentication evidence only. It does not prove that the recovery address was added during the current run.

The replacement flow is a separate transaction:

1. Generate/select the new domain mailbox for the target account.
2. Open Microsoft security options and choose **Add another way to sign in → Email a code**.
3. Fill the new mailbox and capture the pre-submit form.
4. Click Next/send code and capture the immediate post-submit code screen.
5. Read the OTP from the domain mailbox, fill it, and capture the pre-confirm state.
6. Submit the OTP and capture the immediate post-submit result. OCR must show navigation/success, not an error.
7. Refresh the security page and verify the new mailbox is present.
8. Remove the old mailbox only after the new one is verified. Capture the remove-confirmation dialog and then the post-confirm success (`Email removed`) plus the refreshed proof list.
9. Update workbook/state only after those account-specific artifacts pass inspection.

A workbook field such as `mail khôi phục` is input/state, not proof of when Microsoft added the address. If no prior verified artifact or Microsoft activity exists, report add-time as unknown.

## Sign-out-everywhere evidence

Seeing `Sign out everywhere` / `Đăng xuất khỏi mọi nơi` is only a pre-action checkpoint. It is never success evidence.

Required sequence:

1. Locate the canonical action (`#DeleteTrustedDevices` on the Microsoft security page, or a localized equivalent) and capture the pre-action page.
2. Click it once and capture the confirmation modal immediately.
3. Click the modal's confirmation button and capture the post-confirm result immediately.
4. Accept only an account-specific screenshot/OCR containing `We've started signing you out` (or the localized success equivalent), with the account/profile identity bound to the artifact.
5. If the modal/result is absent, stale, from another account, or contains an error, mark `BLOCKED/UNVERIFIED`; do not report success.

## Cross-account artifact guard

Artifact filenames, OCR transcripts, and report claims must all include the target email/profile. A successful add/remove/sign-out run for another mailbox cannot validate the current mailbox. Keep separate checkpoint paths for each target and inspect the exact file before attaching it.

## Known failure pattern

The generic recovery cleanup logic `if any(untrusted_domain in page_text)` is unsafe when the desired new mailbox itself uses that domain. Never remove a recovery method merely because it contains `fviainboxes.com` or another domain on an allow/deny list. Match the exact old address and require proof that a replacement has already been verified.
