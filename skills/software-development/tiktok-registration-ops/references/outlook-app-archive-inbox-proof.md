# Outlook app Archive-vs-Inbox proof

## Root cause

Outlook Android can resume on `Lưu trữ`/`Archive`. The empty-state explanation and CTA contain `Hộp thư đến`/`Inbox`, so broad text matching can falsely classify Archive as Inbox and let the OTP reader enter a blind retry/resend loop.

## Evidence pattern

Machine 38 live UI showed Microsoft Outlook (`com.microsoft.office.outlook`), exact folder heading `Lưu trữ`, empty state `Không có gì trong Lưu trữ`, CTA `ĐI ĐẾN HỘP THƯ ĐẾN`, and no blocking dialog. Redacted artifacts were under `D:\Taadaa\Tiktok_Reg\.ai-runs\outlook-app-login\machine-38\`. The artifacts record package/activity/status but do not prove the active folder; folder proof requires the fresh UI dump or screenshot.

## Canonical contract

1. Require the Outlook messages-list resource and exact folder heading.
2. `Archive` wins over explanatory/body/CTA text containing `Inbox`.
3. On Archive, tap only the semantic `ĐI ĐẾN HỘP THƯ ĐẾN` / `GO TO INBOX` node.
4. Recapture and require a fresh Inbox heading; never reuse the Archive dump.
5. Verify the exact target mailbox in the drawer summary resource. Message-body/snippet email text is not identity proof.
6. Only then scan a TikTok-labelled message and extract the code.
7. Missing proof is terminal `LoginBlocked`; do not switch accounts, logout, clear app data, blind-resend, or continue the OTP loop.

## Regression pattern

Keep an Archive fixture with Inbox words in the explanation and CTA; assert `archive_visible=True` and `inbox_visible=False`. Keep an Inbox fixture with exact drawer identity and a TikTok six-digit message; assert CTA tap, second recapture, identity proof, then code. Keep a missing-identity fixture that fails with `OUTLOOK_APP_ACCOUNT_IDENTITY_NOT_VERIFIED` before scanning.

## Verification

Use the automation interpreter with cleared `PYTHONPATH`, then run focused reader/login tests, provider/post-auth tests, `py_compile`, and `git diff --check`. A prior `OTP_FOUND` artifact is not permission for live retry; fresh machine/serial/lock and Outlook-surface preflight are still required.

## Provider-routing pitfall

When changing provider routing, grep every reader call site. In this case `[8b]` and `[9]` directly called the Gmail reader, so fixing only the primary registration OTP path left Hotmail in a blind `Gửi lại mã` loop. Test Gmail and Hotmail/Outlook/Live dispatch and guard that resend is not tapped while a code is available.
