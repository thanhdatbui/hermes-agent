# Signup mode and magic-link decision recipe

## Decision table

Classify from the **current TikTok screen immediately after the email signup submit**:

| TikTok marker | Mode | Mail action |
|---|---|---|
| `Nhập mã gồm 6 chữ số`, `mã PIN`, `code`, `Gửi lại mã` | numeric OTP | Pull-refresh Hotmail, open the newest TikTok code mail, read the fresh code, enter it |
| `Kiểm tra hộp thư của bạn`, `liên kết được gửi đến`, `link`, `Gửi lại email` | magic-link | Pull-refresh Hotmail, open the newest TikTok verification mail, click `Xác minh email`/`Verify email` |
| no decisive marker | unknown | fail closed; do not invoke either branch |

Do not infer the mode from Hotmail/Outlook, the email subject, an old screenshot/XML, or an activity name. `SignUpOrLoginActivity` alone is insufficient.

## Magic-link sequence

1. Leave TikTok on `Kiểm tra hộp thư của bạn`.
2. Open Hotmail and pull/swipe-refresh the inbox so the newest message is loaded.
3. Select the newest TikTok message whose body contains the verification action.
4. Click the semantic `Xác minh email`/`Verify email` link. Do not click generic `here` or use an older message.
5. The correct link automatically deep-links/returns to TikTok; no manual app switch or extra “step 7” is needed.
6. Verify the resulting TikTok state. If it becomes `CommonFlowActivity` with `Nhập mã gồm 6 chữ số` for password setup, the magic-link succeeded and the next step is a fresh OTP. This is not a magic-link failure.

## Stop handling

A user `dừng`/`stop` is a hard stop: cancel or reconcile delegated/live runners first, verify no target runner remains, then report. Do not continue polling, retrying, refreshing mail, changing rotation, or manipulating the device after the stop request.

## Evidence checklist

Record the current TikTok screenshot/UI evidence before classifying; after the mail action, record the resulting foreground activity and UI markers. Keep OTP values, passwords, tokens, and full credentials out of reports.
