# Registered-vs-unregistered routing reference

## Core correction

Never classify an email as an existing TikTok account from a generic marker such as `Xác minh email`, `Nhập mã`, `Gửi lại mã`, or the presence of a TikTok verification email. The same-looking OTP/verification surfaces can belong to either:

- **Existing-account login**: entered from a TikTok login/identifier surface; downstream proof is password login, login OTP, or an explicit login-link surface.
- **New registration**: entered from a TikTok signup/create-account surface; downstream proof is `Xác minh email của bạn`, `Thao tác này sẽ xác nhận email của bạn và hoàn tất đăng ký`, a signup magic-link wait screen, or signup OTP/password continuation.

The entry surface and the fresh post-submit TikTok UI must be captured as one transition. Mail content is a later provider step, not the account-state classifier.

## Decision contract

1. Capture the current TikTok package/activity/screenshot/XML before submitting the email. Record whether the entry surface is login or signup.
2. Submit the email once, then recapture the TikTok UI. Do not infer mode from Gmail/Outlook provider, subject, old XML, or a six-digit code found in the mailbox.
3. Classify with both states:
   - `login_entry + password/login-OTP/login-link` -> `REGISTERED_LOGIN`.
   - `signup_entry + registration-verification/signup-magic-link/signup-OTP` -> `UNREGISTERED_REG`.
   - explicit `account not found` / `create account` -> `UNREGISTERED_REG`.
   - missing, conflicting, stale, or non-TikTok evidence -> `UNKNOWN` and fail closed.
4. Route only after classification:
   - `REGISTERED_LOGIN` -> `tiktok-log-in`.
   - `UNREGISTERED_REG` -> `Tiktok_Reg`.
5. For registered login, require TikTok ID + TikTok password (+ 2FA if required). `PASS MAIL` is never a TikTok password. If the account is registered but credentials are absent, return `REGISTERED_CREDENTIALS_MISSING`; never attempt registration over it or guess credentials.
6. Only after the mode is fixed, use the mailbox handler appropriate to that mode: newest OTP for numeric mode or newest verified magic-link for link mode. Refresh/select the newest message and retain identity/timestamp evidence.

## High-value negative example

A mail/screen containing `Xác minh email của bạn`, `Nhấp vào liên kết này hoặc nhập mã`, and `Thao tác này sẽ xác nhận email của bạn và hoàn tất đăng ký` is **signup evidence**, not proof of a pre-existing account. Treating its `Nhập mã` surface as existing-account login is a false positive.

## Regression matrix

- Signup entry + `Xác minh email của bạn` + `hoàn tất đăng ký` -> `UNREGISTERED_REG`.
- Signup entry + `Nhập mã gồm 6 chữ số` -> `UNREGISTERED_REG`.
- Login entry + password field -> `REGISTERED_LOGIN`.
- Login entry + `Nhập mã`/`Gửi lại mã` -> `REGISTERED_LOGIN`.
- Login entry + `Bạn có thể đăng nhập bằng liên kết` -> `REGISTERED_LOGIN`.
- No entry context + generic `Nhập mã` or `Xác minh email` -> `UNKNOWN`.
- Registered state without TikTok credentials -> `REGISTERED_CREDENTIALS_MISSING`, not registration.

## Verification gate

Before claiming the router is fixed, run focused tests for every row above and assert that `UNKNOWN` invokes neither numeric OTP nor magic-link handling.
