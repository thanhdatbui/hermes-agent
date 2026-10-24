# Evicted Gmail OTP Deadlock & Runtime PYTHONPATH Isolation

## 1. Triệu chứng sự cố (Root Cause)
- Khi Farm Alert báo lỗi `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
- Script `recover_missing_tiktok_login.py` (hoặc `tiktok_login_v1.py`) được gọi để tự động nạp lại tài khoản bị thiếu trên thiết bị.
- Nếu tài khoản trong tracking workbook (`taikhoan_dat_v2_updated .xlsx`) **chưa có mật khẩu TikTok** (`tiktok_pass` rỗng), luồng bắt buộc fallback sang **Email OTP**.
- **Deadlock xảy ra khi**:
  1. Tài khoản đăng ký bằng Gmail (`@gmail.com`).
  2. Gmail này đã từng bị gỡ bỏ khỏi máy S7 (`dumpsys account` có `action_account_remove`) để nhường slot cho tài khoản khác.
  3. Hàm `_try_get_otp_gmail_app` chỉ quét các tài khoản Gmail đang có sẵn trên ứng dụng Gmail của máy S7. Khi không thấy tài khoản, nó thử 4 lần rồi fail-closed và ném lỗi `[7c] Không lấy được OTP`.

## 2. Lỗi False-Positive DIE do PYTHONPATH Leakage
- Khi script chạy từ môi trường host hoặc subagent kế thừa biến môi trường `PYTHONPATH`:
  - Module `check_gmail_live_fast.py` import `playwright`, nhưng lại nạp nhầm package `greenlet` của host venv (lỗi `ModuleNotFoundError: No module named 'greenlet._greenlet'`).
  - Khối `except` trong `tiktok_login_v1.py` xử lý fail-closed, hiểu nhầm ngoại lệ kiểm tra thành tài khoản bị **DIE** (`checker returned DIE -> BLOCK`).
- **Khắc phục chuẩn**:
  - Trong wrapper/runner gọi subprocess (`recover_missing_tiktok_login.py`), BẮT BUỘC xóa `PYTHONPATH` khỏi env:
    ```python
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONUNBUFFERED"] = "1"
    ```

## 3. Quy trình khôi phục tài khoản thiếu mật khẩu & mất Gmail S7
- **Bước 1**: Kiểm tra `dumpsys account` trên máy xem Gmail mục tiêu có trên thiết bị không.
- **Bước 2**: Nếu không có, nạp lại tài khoản Gmail vào thiết bị:
  - Khởi chạy intent: `am start -a android.settings.ADD_ACCOUNT_SETTINGS`
  - Chọn `Google` (hoặc mở `com.google.android.gm.setup.AccountSetupFinalGmail`).
  - Điền email, mật khẩu và sinh mã 2FA TOTP bằng `pyotp` từ secret key trong workbook để xác thực.
- **Bước 3**: Kích hoạt lại `recover_missing_tiktok_login.py --machine <N> --account <user> --resume` để hoàn tất nạp phiên TikTok.
