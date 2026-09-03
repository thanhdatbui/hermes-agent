# Signup verification mode classification

## Rule

Choose the verification branch from the **current TikTok UI after pressing Đăng ký/Tiếp tục email**. Never infer it from the email provider, email subject, activity name, or an older screenshot/XML.

## Decision matrix

| Current TikTok marker | Mode | Allowed next step |
|---|---|---|
| `Nhập mã gồm 6 chữ số`, `mã PIN`, `Gửi lại mã` | Numeric OTP | Open/refresh provider inbox, select the newest TikTok code mail, enter only a fresh code |
| `Kiểm tra hộp thư của bạn`, `liên kết được gửi đến`, `Gửi lại email` | Magic-link | Select the newest TikTok verification-link mail, open its verified deep-link, recapture and verify transition |
| No decisive marker; Chrome/Outlook foreground; stale/old evidence | UNKNOWN / fail-closed | Bring TikTok foreground and recapture; do not read OTP, open a link, or resend |

## Critical distinction

`SignUpOrLoginActivity` is only an activity name. It does not prove OTP. The text `Kiểm tra hộp thư của bạn` is magic-link even when the package/activity is `SignUpOrLoginActivity`.

A prior screenshot showing `Nhập mã gồm 6 chữ số` must not override a newer screenshot showing `Kiểm tra hộp thư`. On STT30, relaunch/recents repeatedly exposed this stale-evidence failure: the app state changed while the old OCR artifact remained available.

## Live sequence

1. Verify TikTok is foreground.
2. Submit the signup email / press `Đăng ký` or `Tiếp tục`.
3. Recapture the current TikTok UI immediately.
4. Classify by the decision matrix.
5. Only then enter the corresponding provider flow.
6. After provider action, recapture TikTok and verify a real state transition; foreground/package alone is not success.

## Safety

- Do not use old numeric codes from a lower/older inbox row when the newest mail is a link mail.
- Do not fall from magic-link to numeric reader or shared OTP resend because a code-looking old email exists.
- Do not click a generic email link: prove it is a TikTok verification anchor from the newest TikTok mail.
- Preserve the current UI on `UNKNOWN` or unverified transition and report `FINAL_BLOCKED` with screenshot/XML evidence.

## Regression cases

1. UI containing `Nhập mã gồm 6 chữ số` + `Gửi lại mã` selects OTP.
2. UI containing `Kiểm tra hộp thư của bạn` + `liên kết được gửi đến` + `Gửi lại email` selects magic-link.
3. UI with neither marker returns UNKNOWN and invokes neither OTP reader nor magic-link handler.
4. A stale OCR/XML artifact from a previous activity cannot determine the current mode.

## Shipped implementation (2026-08-11, Tiktok_Reg, consumer-only)

Code landed in `social_reg_v1.py` implementing the rule above. TDD: 7 regression tests in `tests/test_signup_email_transition.py` (RED 4 failed → GREEN 10 passed; full focused set 73 passed).

- `NUMERIC_OTP_SCREEN_HINTS` (flat, strip_accents+lower): `ma gom 6 chu so`, `6 chu so`, `a 6 digit code`, `6-digit code`, `ma xac minh da duoc gui den`, `nhap ma`, `gui lai ma`, `resend code`, `enter the code`, `verification code`, `sent a code`.
- `MAGIC_LINK_POST_SUBMIT_HINTS`: `lien ket duoc gui den`, `lien ket da duoc gui den`, `link duoc gui den`, `duoc gui qua lien ket`, `gui qua lien ket`, `kiem tra hop thu`, `gui lai email`, `sign up with a link`, `dang ky bang lien ket`, `su dung lien ket`, `lien ket nay`.
- `_classify_post_signup_submit_mode(flat)` → `'numeric' | 'magic-link' | 'unknown'` — numeric checked FIRST, magic second, else `'unknown'` (fail-closed).
- `_fill_tiktok_signup_email_and_submit(...)` now recaptures after the form transitions and RETURNS the mode string (not `True`); `False` only when the current XML is not a signup form. All existing callers tolerate the string return (`if not _fill(...)` checks stay truthy-safe).
- `handle_tiktok_email_otp(device_id, email, password, stt=None, *, signup_mode=None)`:
  - `signup_mode='unknown'` (and env `SOCIAL_PREFER_MAGIC_LINK` unset) → `_capture_tiktok_email_otp_final_blocked(..., "SIGNUP_EMAIL_MODE_UNKNOWN")` BEFORE any reader/resend; error text contains `SIGNUP_EMAIL_MODE_UNKNOWN`.
  - `signup_mode='magic-link'` → `prefer_magic_link = True`; `'numeric'` → `False` (modulo the forced env escape hatch). The mode from submit-time recapture WINS over markers on a stale/held screen — this is the STT30 wrong-route fix (numeric code read from a background tab and typed onto a magic screen → `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`).
  - `signup_mode=None` → legacy marker logic unchanged (`MAGIC_LINK_SCREEN_HINTS` + `_classify_after_continue_flat != "registered_otp"` guard) so LOGIN-flow callers (`tiktok_login_v1`, login-fallback at run 12113/12591) keep old behavior. Strict fail-closed applies ONLY to signup-flow call sites.
- Callers that pass `signup_mode`: step 7c in `register()` and the resume path — both classify the fresh `flat` via `_classify_post_signup_submit_mode` and raise `[7c]/[resume] SIGNAL... SIGNUP_EMAIL_MODE_UNKNOWN` on `'unknown'` (capture `fail_<stt>_signup_mode_unknown` / `fail_<stt>_resume_signup_mode_unknown` first).
- A bare `Kiểm tra email`/`check your email` screen (no `Gửi lại mã`/`Nhập mã`/link markers) now classifies `unknown` → fail-closed, matching the user's strict marker list (`kiểm tra hộp thư` ≠ `kiểm tra email`); previously the legacy classifier ran the numeric path on it.
- Env `SOCIAL_PREFER_MAGIC_LINK=1` stays the guarded-recovery escape hatch and beats everything, including `signup_mode='unknown'`.
