# TikTok REG Existing-Account OTP Screen Classification & False Timeout Root Cause

## Context & Incident Evidence
- **Target Repo:** `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`
- **Function Anchor:** `fill_email_for_stt(...)` around line 3785–3912.
- **Observed Failures:** `fail_243_no_new_email_080610.xml` and `fail_257_no_new_email_080618.xml` raising `[07] Khong the xac dinh trang thai email cho STT {stt} do timeout/mang cham khi bam Tiep tuc ('{em}')`.

## UI Dump Semantic Evidence
When candidate email is entered and "Tiếp tục" / "Continue" is tapped, TikTok may transition directly to an email verification / OTP challenge screen for an already-registered account rather than a new account registration form or a password login prompt.

UI Node attributes from `fail_243_no_new_email_080610.xml`:
- Title: `<TextView text="Xác minh email" resource-id="com.ss.android.ugc.trill:id/f4c" />`
- Subtitle / Prompt: `<TextView text="Sử dụng liên kết này hoặc nhập mã được gửi đến <email>" resource-id="com.ss.android.ugc.trill:id/f2k" />`
- Code Input: `<EditText ... resource-id="com.ss.android.ugc.trill:id/r3x" />`
- Buttons:
  - `<Button text="Gửi lại mã" resource-id="com.ss.android.ugc.trill:id/l6q" />`
  - `<Button text="Bạn cần trợ giúp đăng nhập?" resource-id="com.ss.android.ugc.trill:id/l6y" />`

## Root Cause & Pitfall
1. `detect_after_continue(device_id)` failed to classify this specific variant of OTP verification screen as `registered_otp`.
2. When `detect_after_continue` timed out and returned `None` / `unknown`, the fallback scanner checked `otp_fallback`, but if key Vietnamese phrases or resource IDs were missing (e.g. `"su dung lien ket nay hoac nhap ma"`, `"ban can tro giup dang nhap"`), it fell through to:
   ```python
   save_ui_xml(device_id, f"fail_{stt}_unknown_fallback_{idx}")
   had_timeout_error = True
   ```
3. After exhausting all candidates, `had_timeout_error` tripped the exception `[07] Khong the xac dinh trang thai email ...` instead of recognizing that the email is already registered (`registered_otp`).

## Canonical Rule & Fix Pattern
1. **Definite Existing-Account Classification:**
   - Detectors MUST match the exact text markers (accent-stripped):
     - `"xac minh email"`
     - `"su dung lien ket nay hoac nhap ma"`
     - `"ban can tro giup dang nhap"`
     - `"gui lai ma"`
   - Resource-ID markers: `:id/f4c`, `:id/f2k`, `:id/l6q`, `:id/l6y`.
   - Classification result must be `registered_otp` (already registered), which aborts candidate registration for this email and continues to the next candidate safely.
2. **Never Invent Login Flow:**
   - Under canonical rules (Farm anti-overengineering), registration runners MUST NOT attempt to log in or bypass OTP when encountering existing accounts.
   - Simply classify as registered, back out cleanly (`keyevent 4`), and evaluate the next email.
