# Quy tắc Preflight Check Live Gmail & Dọn dẹp Kép (Dual Cleanup)

## 1. Hiện tượng & Nguyên nhân gốc
- **Triệu chứng:** Khi chạy batch reg TikTok (`_run_all_targets.py`), nhiều máy S7 văng lỗi:
  `[7c][BLOCKED_GMAIL_OTP_TIMEOUT] <email>`
  khiến máy con phải treo chờ OTP đủ 150s (`GMAIL_OTP_ATTEMPT_TIMEOUT = 150`) mới dừng.
- **Nguyên nhân:** Tài khoản Gmail đã bị Google vô hiệu hóa / DIE từ trước, TikTok không thể phát thư OTP về inbox và app Gmail trên thiết bị không thể đồng bộ thư mới.

## 2. Cơ chế Preflight Check Live Batch
- Tích hợp công cụ `D:/Taadaa/tools/check_gmail_live_fast.py` vào trước khi chia batch trong `_run_all_targets.py`.
- **Batching:** Dùng hàm `check_gmail_live_batch(emails)` đưa toàn bộ danh sách Gmail cần reg vào `checkmail.live` qua Playwright + proxy mobi1 trong 1 phiên duy nhất (tối đa 50 mail/chunk).
- **Phân loại:**
  - Tag `[LIVE]`: Đủ điều kiện reg TikTok.
  - Tag `[DIE]`: Lập tức kích hoạt quy trình dọn dẹp kép và loại khỏi danh sách reg của đợt chạy.
- **Fail-open:** Khi gặp sự cố mạng, timeout hoặc không parse được, mặc định giữ `True` (live) để không vô tình loại nhầm tài khoản hợp lệ.
- **CLI flag:** Hỗ trợ `--skip-live-check` khi cần bỏ qua bước tiền kiểm tra này.

## 3. Quy tắc Dọn Dẹp Kép Bắt Buộc khi Gmail DIE (Dual Cleanup Invariant)
> **Quy tắc bất biến (User chỉ đạo trực tiếp):** *"Khi gmail die ở khâu check live thì nhớ dọn ở cả máy nhé chứ k chỉ ở excel đâu"*.

Khi bất kỳ Gmail nào bị xác nhận DIE ở khâu preflight hoặc in-flight:
1. **Dọn dẹp trên Excel (Source):**
   - Bắt buộc gọi `remove_captcha_dead_email_from_source(email)` để xóa vĩnh viễn dòng email này khỏi `gmail_clean_v2.xlsx`.
   - Tạo backup trước khi xóa, verify không còn dòng trùng lặp để các lượt detect tương lai không bốc lại.
2. **Dọn dẹp trên Thiết bị Android S7 (Device):**
   - Bắt buộc kiểm tra danh sách tài khoản hiện có trên máy con qua `dumpsys account` bằng Xiaowei ADB (`C:\Program Files (x86)\xiaowei\tools\adb.exe`).
   - Nếu tài khoản Google DIE vẫn còn đăng nhập trên máy: phải tiến hành gỡ bỏ tài khoản (`remove account`) khỏi hệ thống Android.
   - **Mục đích:** Giữ máy sạch slot, chống kẹt sync nền, chống popup Google đòi mật khẩu/captcha làm nghẽn các tác vụ sau.
