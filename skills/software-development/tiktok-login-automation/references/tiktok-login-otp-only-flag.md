# TikTok Login OTP-Only Flow (`--otp-only`)

Added on 2026-09-24.

## Purpose
By default, `tiktok_login_v1.py` prefers login via `account["id"]` + `account["tiktok_pass"]` to bypass email OTP and captcha.
When accounts require email OTP verification or password login is unavailable/unwanted, pass `--otp-only` to force the email OTP login flow.

## Behavior with `--otp-only`
1. **Target Calculation**:
   - `force_otp = bool(account.get("otp_only", False))`
   - `login_target = account["login_email"] if (force_otp or not (account.get("id") and account.get("tiktok_pass"))) else (account.get("id") or "").strip()`
   - Used in both `login_one_account` and `resume_one_account`.
2. **Screen Driving (`drive_login_screens`)**:
   - In `PASSWORD_HINTS`: If `force_otp`, taps "Đăng nhập bằng mã" ("Dang nhap bang ma", "Log in with code", "Đăng nhập bằng mã xác minh", "Gửi mã", "Send code") and continues.
   - In `OTP_HINTS`: Avoids tapping "Đăng nhập bằng mật khẩu", letting `handle_tiktok_email_otp` read mail and fill the code.

## Verification
- Unit test: `tests/test_tiktok_login_otp_only.py`
- Command: `python -m unittest tests/test_tiktok_login_otp_only.py`
