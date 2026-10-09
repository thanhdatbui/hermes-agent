# Preflight Gmail Live Check & Dual Cleanup (2026-09-17)

## Bối Cảnh & Vấn Đề
Khi chạy batch đăng ký TikTok qua Gmail (`_run_all_targets.py`), nhiều máy S7 gặp lỗi `[7c][BLOCKED_GMAIL_OTP_TIMEOUT]`:
- Máy S7 vào TikTok, điền email, gửi mã xác minh nhưng đợi timeout 150s không nhận được OTP.
- **Nguyên nhân gốc rễ**: Gmail nguồn thực chất đã bị Google vô hiệu hóa (DIE) từ trước đó, app Gmail trên máy không thể tải thư mới hoặc TikTok không phát mã về hòm thư chết.

## Giải Pháp: Preflight Check Live Qua Web (checkmail.live)
1. **Module Check Live Batch (`D:/Taadaa/tools/check_gmail_live_fast.py`)**:
   - Dùng Playwright kết nối web `https://checkmail.live/` qua proxy Mobi1.
   - Hàm `check_gmail_live_batch(emails: list[str], max_batch_size: int = 50) -> dict[str, bool]`:
     - Nạp toàn bộ danh sách Gmail vào editor, kích hoạt nút check 1 lần duy nhất cho cả batch.
     - Parse kết quả `[LIVE]` và `[DIE]`.
     - **Fail-open an toàn**: Mọi lỗi timeout/mạng hoặc không parse được đều mặc định giữ `True` (LIVE) để tránh loại nhầm tài khoản khi mạng chập chờn. Chỉ khi có nhãn `[DIE]` rõ ràng mới trả về `False`.

2. **Quy Tắc Dọn Dẹp Kép (Dual Cleanup) Khi Gmail DIE**:
   - **Yêu cầu bắt buộc từ User**: Khi phát hiện Gmail DIE ở bước check live, PHẢI DỌN DẸP Ở CẢ EXCEL LẪN TRÊN THIẾT BỊ MÁY S7, không được chỉ xóa ở Excel rồi để lại acc rác trên máy.
   - **Thao tác 1 (Excel)**: Gọi `remove_captcha_dead_email_from_source(email)` xóa khỏi `gmail_clean_v2.xlsx`.
   - **Thao tác 2 (Máy S7)**: Gọi `remove_device_account_fast(serial, email)` trong `D:/Taadaa/tools/remove_device_google_account.py` để gỡ bỏ tài khoản Google khỏi cài đặt Android (Settings -> Cloud and accounts -> Accounts -> Google -> Remove account).

3. **Tích hợp Pipeline (`_run_all_targets.py` & `scripts/gmail_preflight_filter.py`)**:
   - Tách module `scripts/gmail_preflight_filter.py` độc lập.
   - Chạy kiểm tra preflight TRƯỚC bước cắt quota `--max-targets` để quota máy chạy thật không bị hao hụt.
   - Thêm CLI option `--skip-live-check` khi cần bypass thủ công.
