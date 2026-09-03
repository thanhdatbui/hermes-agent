# Magic-link verify screen bị classify nhầm registered_otp — chi tiết session 2026-08-07

Bug class: classifier marker-overlap trong `social_reg_v1.py` `detect_after_continue`
(called from `fill_email_and_next` sau khi type email + submit). Same class as the
profile-vs-feed false positive — marker lists phải tách theo NGHĨA màn, không gộp
theo "giống nhau về mặt OTP".

## Symptom (live máy 34)
Màn magic-link verify của email CHƯA đăng ký:
- "Kiểm tra hộp thư của bạn"
- "Gửi lại email sau 46 giây"
- "Đăng nhập bằng mật khẩu"

bị classify `registered_otp` → caller bỏ qua email → `RuntimeError("[07] Tat ca N
email cua STT X da co TK TikTok")` dù email chưa đăng ký → registration chết oan.

## Root cause
List `otp_hints` cũ gộp chung 2 nhóm marker:
- OTP login thật (email ĐÃ có TK): "xac minh email", "verify email", "nhap ma",
  "gui lai ma", "resend code", "ma xac nhan", "ma xac minh", "verification code",
  "enter the code", "sent a code"
- Magic-link verify (email CHƯA có TK): "kiem tra email", "kiem tra hop thu",
  "check your email", "check email", "gui lai email", "resend email"

## Fix (đã verify, KHÔNG commit)
```python
REAL_OTP_LOGIN_HINTS = [ ... ]  # nhóm 1 → 'registered_otp'
MAGIC_VERIFY_HINTS = [ ... ]    # nhóm 2 → 'verify_email_pending'

def _classify_after_continue_flat(flat):
    if any(h in flat for h in REAL_OTP_LOGIN_HINTS):
        return "registered_otp"
    if any(h in flat for h in MAGIC_VERIFY_HINTS):
        return "verify_email_pending"
    return None
```
- `detect_after_continue` dùng helper; trả `verify_email_pending` cho magic-verify.
- Caller `fill_email_and_next`: nhánh `result == "verify_email_pending"` ĐẶT TRƯỚC
  `registered_otp` → `return em, pw, dob` (giữ email) → flow 7c
  `handle_tiktok_email_otp` mở mail → tap magic link → `MAGIC_LINK` → TikTok tự xử lý.
- Fallback unknown (else branch): thay list `otp_fallback` duplicate bằng
  `_classify_after_continue_flat(flat_backup)` — không duplicate marker list
  (DRY), giữ `reg_fallback` cũ ("da co tai khoan", "email nay da co", "mat khau",
  "password").

## Priority case (bắt buộc có test negative)
Màn OTP login thật thường kèm text "Kiểm tra email của bạn" → cả 2 nhóm match.
Priority REAL_OTP trước → vẫn `registered_otp`. Nếu làm ngược (magic trước) sẽ
nuốt nhầm OTP login thật thành verify_email_pending → flow sai chiều.

## Tests
`tests/test_login_magiclink_classify.py` (5 tests, CRLF — repo dùng CRLF, file mới
phải convert):
1. magic-only XML → `verify_email_pending` (KHÔNG phải registered_otp)
2. OTP-only XML ("Nhập mã xác minh" + "Gửi lại mã") → `registered_otp`
3. NEGATIVE: cả 2 nhóm → `registered_otp` (priority)
4. resend-email-only ("Gửi lại email sau 46 giây") → `verify_email_pending`
5. helper unit: priority + empty → None

Mock pattern (theo mẫu `test_detect_after_continue.py`):
```python
def _fast_time(monkeypatch):
    times = iter([0.0, 0.2, 1.1])  # end=1.0, lần 1 (0.2) chạy body
    monkeypatch.setattr(social.time, "time", lambda: next(times))
    monkeypatch.setattr(social.time, "sleep", lambda _seconds: None)
monkeypatch.setattr(social, "get_ui_xml", lambda _device: XML)
assert social.detect_after_continue("serial", timeout=1) == "..."
```

## Verify command (env chuẩn)
```
PYTHONPATH="D:\Taadaa\python-envs\tiktok-reg-recovery\Lib\site-packages;D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail" \
"D:\Taadaa\python-envs\tiktok-reg-recovery\Scripts\python.exe" -m pytest \
  tests/test_login_magiclink_classify.py tests/test_detect_after_continue.py \
  tests/test_login_method_entry.py tests/test_gmail_otp_marker_node_fix.py \
  tests/test_hotmail_mail_die_alive_guard.py -q -p no:cacheprovider
# → 26 passed; git diff --check clean; KHÔNG commit (yêu cầu task)
```
Lưu ý: `search_files` (rg) KHÔNG truy cập được ổ D: — dùng `grep -n` trong terminal
cho mọi search trên repo này.

## Liên quan
- `docs/ui-compatibility.md` entry: `tiktok-reg-magiclink-verify-classify-20260807`.
- State `verify_email` của `_classify_post_auth` (L4189-4191) KHÁC state mới
  `verify_email_pending` — đừng lẫn. `otp_screen_hints` bước 7c (L9386+) giữ
  nguyên (chờ OTP screen, không phải classifier registered/new).
- Working tree có nhiều file modified pre-existing (worker khác) — check
  `git status --short` trước; `docs/ui-compatibility.md` có thể đã modified sẵn
  (diff 300+ dòng pre-existing); chỉ thêm entry vào cuối, không đụng diff cũ.
