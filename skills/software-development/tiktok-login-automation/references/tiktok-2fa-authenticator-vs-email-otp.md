# TikTok 2FA classifier: Authenticator App vs Email OTP

## Trigger
Use when `tiktok_login_v1.py` classifies the current TikTok login UI from normalized UI XML/text.

## Core rule
TikTok may show generic wording such as `Xác minh 2 bước` / `2-step verification` on both flows. Never use that wording alone to dispatch the Authenticator/TOTP handler.

Classify as **Authenticator App** only when the screen explicitly contains an authenticator signal, such as:
- `ung dung xac thuc`
- `authenticator app`
- `google authenticator`

Classify as **Email OTP** when the screen has generic 2FA wording, or has email-delivery plus OTP wording, unless an explicit authenticator signal wins first. Route it to `handle_tiktok_email_otp(device_id, email, mail_pass, stt=stt)`.

## Implementation shape
Keep separate hint lists:
- `TWOFA_AUTHENTICATOR_HINTS`: strict, app-specific terms only.
- `TWOFA_GENERIC_HINTS`: generic 2-step terms; route to Email OTP by default.
- `TWOFA_EMAIL_HINTS`: email-delivery terms; require an OTP hint as an additional guard to avoid matching unrelated email screens.

Authenticator detection must run before Email OTP detection. Preserve the existing normalized/diacritic-insensitive text path.

## Regression matrix
At minimum, probe these cases:

| UI text | Expected route |
|---|---|
| `Xác minh 2 bước` | Email OTP |
| `Xác minh 2 bước` + `Email` + `nhập mã` | Email OTP |
| `Xác minh 2 bước` + `Ứng dụng xác thực` | Authenticator App |
| `Authenticator app code` | Authenticator App |

Verify both classifier behavior and the ordering of the two dispatch branches. Do not use live devices, email, or OTP retrieval for this focused check.

## Pitfall
A broad list containing `xac minh 2 buoc` under the Authenticator branch silently sends an email-code screen to the TOTP handler. This can leave the login loop spinning even though UI text detection appears to succeed.
