# Bước 07 magic-link verify đang chờ sẵn — gap fix 2026-08-07 (máy 34)

Session detail cho SKILL.md mục "Bước 07 `fill_email_and_next`". Repo `D:\Taadaa\Tiktok_Reg`,
file `social_reg_v1.py` (provider-local, KHÔNG đổi automation-core).

## Gap (live máy 34, run 20260807-235541)

Máy ĐANG Ở SẴN màn magic-link verify khi bước 07 bắt đầu (chưa submit email nào trong run):

- "Kiểm tra hộp thư của bạn" + "Gửi lại email sau 41 giây" + "Đăng nhập bằng mật khẩu"

Trước fix: `fill_email_and_next` check màn nhập email
(`wait_for_text(["Email hoac TikTok","Email","TikTok ID"], timeout=10)`) → fail →
`save_ui_xml(f"fail_{stt}_email_screen_{idx}")` + `screenshot` + log "✗ Khong thay man nhap email"
→ `continue` → bỏ qua email → cuối run raise `[07] Tat ca N email cua STT ... da co TK TikTok`
(SAI — email chưa có TK, TikTok vừa gửi magic link qua email, email CHƯA nhận được link).

## Fix (social_reg_v1.py ~L3564-3577, trong vòng lặp candidates của fill_email_and_next)

```python
if not wait_for_text(device_id, ["Email hoac TikTok", "Email", "TikTok ID"], timeout=10):
    xml_pending = get_ui_xml(device_id)
    flat_pending = strip_accents(xml_pending).lower()
    if _classify_after_continue_flat(flat_pending) == "verify_email_pending":
        if _mailbox_key(em) not in used_emails:
            log(f"   ✓ {em}: CHUA co TK, TikTok dang cho xac minh magic link (man Kiem tra hop thu) → giu email, di tiep flow verify")
            return em, pw, dob
        log(f"   → {em}: man magic-link verify nhung email da co TK trong tracking → bo qua")
    else:
        save_ui_xml(device_id, f"fail_{stt}_email_screen_{idx}")
        screenshot(device_id, f"fail_{stt}_email_screen_{idx}")
        log("   ✗ Khong thay man nhap email")
    continue
```

- Tái sử dụng helper chung `_classify_after_continue_flat(flat)` (commit 6615ac4) —
  KHÔNG duplicate marker list.
- `used_emails` = `load_registered_tiktok_emails()` (tracking workbook, mailbox-key set).
- `return (em, pw, dob)` → bước 7c `handle_tiktok_email_otp` (đã có magic-link path:
  mở mail → tap link → `MAGIC_LINK`).

## Marker groups (social_reg_v1.py L1652-1667, priority REAL_OTP TRƯỚC)

```python
REAL_OTP_LOGIN_HINTS = ["xac minh email","verify email","nhap ma","gui lai ma",
    "resend code","ma xac nhan","ma xac minh","verification code","enter the code","sent a code"]
MAGIC_VERIFY_HINTS = ["kiem tra email","kiem tra hop thu","check your email","check email",
    "gui lai email","resend email"]
```

`_classify_after_continue_flat`: REAL_OTP trước (màn OTP login thật thường kèm text
"Kiểm tra email" → cả 2 nhóm cùng xuất hiện vẫn là `registered_otp`), MAGIC_VERIFY sau →
`verify_email_pending`, else `None`.

## Test (tests/test_login_magiclink_classify.py — 8 tests)

XML fixtures dùng trong test:

```python
MAGIC_VERIFY_XML = """<hierarchy>
  <node text="Kiểm tra hộp thư của bạn" class="android.widget.TextView" />
  <node text="Gửi lại email sau 46 giây" class="android.widget.TextView" />
  <node text="Đăng nhập bằng mật khẩu" class="android.widget.TextView" />
</hierarchy>"""
RESEND_EMAIL_ONLY_XML = """<hierarchy>
  <node text="Gửi lại email sau 46 giây" class="android.widget.TextView" />
</hierarchy>"""
```

3 test mới cho bước 07 (mock I/O qua `_mock_fill_email_and_next_env`):
- `test_fill_email_and_next_keeps_email_on_magic_verify_screen` — magic XML → giữ email,
  trả `("foo@hotmail.com","pw123","dob")`, KHÔNG gọi save_ui_xml/screenshot.
- `test_fill_email_and_next_keeps_email_on_resend_email_screen` — resend-email-only → giữ email.
- `test_fill_email_and_next_skips_email_when_screen_is_not_email_or_magic` — màn thường
  (không nhập email, không magic) → vẫn bỏ qua + lưu fail screen (RuntimeError "Tat ca").

Mock set: `load_emails_from_excel`, `load_registered_tiktok_emails`,
`load_hotmail_candidates_for_stt`, `dismiss_samsung_keyboard_tutorial`, `wait_for_text`→False,
`get_ui_xml`→XML, `log`, `save_ui_xml`/`screenshot` (record calls).

## UI.md (docs/ui-compatibility.md)

Entry mới: `## Bước 07 nhận màn magic-link verify đang chờ sẵn 2026-08-07 (gap fix)` —
ID/owner `tiktok-reg-magiclink-verify-step07-entry-20260807`, đặt TRƯỚC entry cũ
`## Magic-link verify screen "Kiểm tra hộp thư" ≠ registered_otp 2026-08-07` (giữ nguyên
header entry cũ khi chèn entry mới — dễ vô tình nuốt header entry cũ vì cùng cụm
"Core version/consumer bị ảnh hưởng ... đổi automation-core." xuất hiện 2 lần).

## Verification evidence

- Pytest: `tests/test_login_magiclink_classify.py` 8 passed (5 classify cũ + 3 bước 07 mới);
  cùng với `test_detect_after_continue.py` → 11 passed; 5 file theo task → 29 passed.
- Command: `PYTHONPATH="D:\Taadaa\python-envs\tiktok-reg-recovery\Lib\site-packages;D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail" "D:\Taadaa\python-envs\tiktok-reg-recovery\Scripts\python.exe" -m pytest tests/test_login_magiclink_classify.py -v -p no:cacheprovider`
- Ad-hoc verify script (tempfile `hermes-verify-*`, đã dọn): 3/3 PASS —
  magic→giữ email; magic+tracked→skip; plain→skip+fail screen.
- `git diff --check` sạch (warning LF→CRLF chỉ ở file không liên quan).
- CRLF: cả 3 file sửa giữ CRLF (0 LF-only) — repo dùng CRLF, patch tool giữ nguyên.
- Task yêu cầu "không commit" — diff để lại: 3 files, +103/-3.

## Pitfalls

- Chèn entry UI.md: chuỗi `- Core version/consumer bị ảnh hưởng ... đổi automation-core.`
  xuất hiện 2 lần trong file — patch phải kèm context header entry kế tiếp để unique match.
- `search_files` tool lỗi `rg: IO error` với path `D:\...` trên git-bash → dùng
  `rg -n "pattern" -g '*.py' .` qua terminal thay thế.
