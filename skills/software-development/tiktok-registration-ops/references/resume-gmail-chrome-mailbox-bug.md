# `--resume` từ Gmail/Chrome foreground KHÔNG đọc mail (bug + fix 2026-08-13)

## Symptom (thực tế STT34/38/57)

Chạy `social_reg_v1.py <stt> --resume` khi máy đang ở foreground **Gmail app** (STT34) hoặc **Chrome/Outlook** (STT38/57):

```
[resume-dbg] package=gmail kiem_tra_email=N gui_lai_ma=N ...   # STT34
[resume-dbg] package=other  kiem_tra_email=N gui_lai_ma=N ...   # STT38/57
[8b] Handle post-auth screens
[8b] Đã vào màn chính → dừng
[9] Wait for login success
✅ SUCCESS
```

**Không có** log `handle_tiktok_email_otp` / `[otp-gmail]` / Outlook reader. Kết quả `SUCCESS` + profile JSON **không chứng minh đã đọc mail mới nhất** — chỉ chứng minh session TikTok đã authenticated (vì máy đã ở Profile).

## Root cause

Trong resume block của `social_reg_v1.py`:

```python
if in_gmail and not in_tiktok:
    ...
    xml_now = _return_to_tiktok_via_recents(device, resume_component=..., current_xml=xml_now)
    if APP_PACKAGE not in (xml_now or ""):
        raise RuntimeError("[resume] TIKTOK_TASK_NOT_RECAPTURED_FROM_GMAIL")
    flat_now = strip_accents(xml_now).lower()
    in_tiktok = APP_PACKAGE in xml_now
```

`_return_to_tiktok_via_recents()` trả về task TikTok **CUỐI CÙNG trong Recents** = `MainActivity`/`Profile` (đã login), **KHÔNG phải màn OTP**. Về tới Profile → không có marker OTP (`kiem tra email`/`nhap ma`/`gui lai ma`) → rơi vào `handle_post_auth_screens` → `wait_login_success` → báo `SUCCESS` **mà chưa hề đọc mail**.

Mailbox-read path (`handle_tiktok_email_otp` / `_request_and_read_fresh_tiktok_email_otp`) **chỉ được gọi khi đã ở màn OTP TikTok có marker** — điều kiện đó không bao giờ thỏa khi bắt đầu từ Gmail/Chrome foreground.

## Fix (đã SHIP 2026-08-13)

Helper mới `_resume_read_mailbox_then_return_to_tiktok(device_id, email, password, stt=None)`:

1. Gọi `handle_tiktok_email_otp(device_id, email, password, stt=stt, signup_mode=None)` để **đọc mailbox qua canonical reader** (Gmail app cho `@gmail.com` → `_try_get_otp_gmail_app`; Chrome/Outlook cho Hotmail/Outlook/Live → `_try_get_otp_outlook_newest`). Đây đúng ý "phần vào gmail lấy otp / chrome đọc mail" có sẵn trong script.
2. Quay về TikTok qua Recents như cũ.
3. **Fail-closed** nếu Recents trả Profile/post-auth (không có marker OTP/signup):
   ```python
   if in_tiktok and not any(h in flat_now for h in _otp_markers + _signup_forms):
       raise RuntimeError(
           "[resume] MAILBOX_READ_BUT_NO_OTP_SCREEN: recents returned Profile "
           "after mailbox read; cannot enter OTP/link"
       )
   ```
   → KHÔNG rơi vào `handle_post_auth_screens` / `wait_login_success` (false SUCCESS).

Resume block gọi helper thay vì chỉ `_return_to_tiktok_via_recents`.

## Regression test

`tests/test_resume_mailbox_read.py` (offline, mock):

- Gmail foreground + `_return_to_tiktok_via_recents` trả Profile → `pytest.raises(RuntimeError, match="MAILBOX_READ_BUT_NO_OTP_SCREEN")`; assert `handle_tiktok_email_otp` (mailbox reader) **ĐÃ được gọi**, `handle_post_auth_screens` **KHÔNG** được gọi.
- Gmail foreground + Recents trả màn OTP (`kiem tra email`/`nhap ma`) → helper trả `(code, xml, flat, in_tiktok)`, `in_tiktok=True`.

## Read-only classifier (khi user chỉ muốn đọc/phân loại mail, KHÔNG login/reg)

Script pattern (standalone, không touch TikTok UI):

```python
import social_reg_v1 as social
social._tap_verified_tiktok_magic_link = lambda *a, **k: False  # patch tap -> no-op
result = social._try_get_otp_gmail_app(serial, email, not_before=None, exclude_codes=None)
# hoặc social._try_get_otp_outlook_newest(serial, email, pw, stt=stt) cho Hotmail
xml = social.get_ui_xml(serial)            # đang ở màn message TikTok
flat = social.strip_accents(xml).lower()   # phân loại theo text
```

Phân loại: `MAGIC_LINK` + text có `chao mung`/`welcome`/`kich hoat` → `SIGNUP_COMPLETION`; `MAGIC_LINK` không rõ → cần đọc text; code 6 số + `ma dang nhap` → `LOGIN_OTP`; code + `xac minh`/`dang ky` → `SIGNUP_OTP`. **KHÔNG enter OTP, KHÔNG tap link, KHÔNG login, KHÔNG reg.**

## Lưu ý verify worker

Worker (delegate) từng trả diff 653 dòng nhưng **KHÔNG sửa block `if in_gmail and not in_tiktok:`** (chỉ rename 2 lời gọi OTP thành `_handle_signup_email_otp_from_current_screen` passthrough) → bug gốc nguyên vẹn. Luôn `git diff -- <file> | grep` đúng seam (`in_gmail`, `_return_to_tiktok_via_recents`, `MAILBOX_READ_BUT_NO_OTP_SCREEN`) trước khi tin worker "done".
