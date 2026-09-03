# Mail evidence and resume runbook

## Purpose

Use this when a registration target stops at a TikTok verification-looking screen and the question is whether the newest mailbox message is signup completion, signup OTP, or login OTP.

## Evidence rule

A TikTok screen is not mailbox evidence. The strings `Nhập mã`, `Sử dụng liên kết này hoặc nhập mã`, `Kiểm tra email`, and `Gửi lại mã` can overlap across signup, login, and post-verification states. A profile/feed success, `tracking_result_*.json`, or a `SUCCESS` log also proves only post-auth/profile state; it does not classify the newest mail.

Only claim mail classification after the canonical consumer flow has actually entered its mailbox reader and emitted fresh evidence for the newest message. If the resume log says foreground is Gmail/Chrome/SystemUI, `kiem_tra_email=N`, `gui_lai_ma=N`, or `ui_state=unknown` and then proceeds to Profile, record `MAIL_CLASSIFICATION_UNVERIFIED` rather than inferring login/signup from the final screen.

## Canonical resume procedure

1. Preserve the current TikTok screen and portrait orientation. Do not launch Gmail/Chrome with `monkey`, `am start`, or an ad-hoc probe.
2. Use the consumer entrypoint and its existing reader:

```text
TAADAA_HOST_CONFIG='D:/Taadaa/machine-config/kibe.yaml' \
PYTHONPATH='D:/Taadaa/Hotmail;.' \
SOCIAL_PREFERRED_EMAIL='<email>' \
'D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe' -u social_reg_v1.py <stt> --resume --ss --defer-tracking-write
```

3. `--defer-tracking-write` is mandatory for evidence-only investigation. Do not update workbook/tracking until the target outcome is independently verified.
4. Capture the complete canonical console log and artifact paths. Look for the actual `_read_gmail_otp_with_target_recovery`, `_try_get_otp_outlook_newest`, or magic-link evidence path and the newest-message proof; absence of those lines is absence of mail evidence.
5. Afterward verify no `social_reg`/runner remains, lock ownership is reconciled, and orientation is portrait (`accelerometer_rotation=0`, `user_rotation=0`, viewport 1080x1920/orientation 0).

## Hybrid verification screen

A fresh signup screen containing `Kiểm tra email` plus `Sử dụng liên kết này hoặc mã`, an OTP EditText, and `Gửi lại mã` is hybrid but numerically actionable: prefer `numeric` when an OTP marker exists. A link-only screen without an OTP marker is `magic-link`. Keep regression coverage for both cases.

## Do not infer registered state

`TikTok ID` empty in tracking means only "candidate selected"; it does not prove the mailbox has never registered. Conversely, a generic TikTok OTP/login-looking screen does not prove the newest mail is a login OTP. Resolve the ambiguity through the canonical mailbox reader and current UI evidence. If canonical resume bypasses the reader and reaches Profile, report the account/profile result separately from mail classification.

## Incident lessons

- Do not replace the registration script with `tiktok_login_v1.py` merely to read mail; that changes the flow contract.
- Do not open Gmail/Chrome externally to inspect mail during a live target; it can change foreground state and orientation and bypass the consumer's newest-message/readiness evidence.
- A batch exit code is not a target verdict. Read each child stdout/stderr and distinguish proxy readiness, lock ownership, registered-login deferral, signup-mode unknown, and actual mail-reader evidence.
