# GPM Login Shifts: Cooldown 24h vs Cumulative Reporting vs Admin Farm GPM Onboarding

## 1. Phân Tách Báo Cáo Ca vs Tài Khoản Gặp Phone Checkpoint (Cooldown 24h)
- Khi Google kích hoạt Secondary Challenge (đòi số điện thoại `PHONE_CHECKPOINT` do đổi IP/fingerprint PC):
  - **Không phải tài khoản DIE**: Tài khoản vẫn LIVE 100% trên điện thoại gốc (Samsung S7).
  - Đưa vào diện `cooldown_7days` với hạn định `retry_after: 24h` để Google reset Risk-Based Authentication (RBA).
  - Script login sau đó giải quyết tự động bằng **Email khôi phục** hoặc **2FA TOTP**, không bị kẹt SMS.
- **Tránh báo động ảo khi đối soát**:
  - Dòng `✗ N` trong báo cáo chốt ca là lũy kế ngày (`total_fail`).
  - Nếu `proxy_count` rỗng và `max_proxy 0/cổng` thì ca hiện tại không chạy và không phát sinh lỗi mới.

## 2. Quy Trình & Điều Kiện Login GPM Cho Gmail Mới Reg Trên Farm Admin (Máy 201-280)
- **Rào cản 1: Soak Period $\ge 7$ ngày bắt buộc trên Android gốc**:
  - Vừa reg trên thiết bị mẹ (S7) mà đưa lên PC login ngay sẽ bị Risk Engine gắn cờ *"New Device Anomaly"*, dẫn đến dính phone checkpoint hoặc chết chùm.
  - Watchdog tự động lọc bỏ (`[CANDIDATE-FILTER] clean_map soak < 7 days`).
- **Rào cản 2: Cấu hình nguồn tuyển chọn (Candidate Scope)**:
  - Watchdog `post_evening_gpm_login_watchdog.py` mặc định đọc sheet `Kibe_Farm_S7` trong `master_gmail_manager.xlsx`.
  - Dàn Gmail Farm Admin nằm ở sheet `Admin_GPM_Pool` / `gmail_clean_v2.xlsx`. Khi tài khoản đủ $\ge 7$ ngày tuổi, cần đồng bộ vào danh sách quét profile GPM.
- **Rào cản 3: Định mức an toàn proxy**:
  - Khung giờ chạy: 3 khung rảnh giữa các ca nuôi (Sáng 09:30-11:20, Chiều 15:30-17:20, Tối 21:30-23:45).
  - Trần định mức: Tối đa 2 tài khoản / cổng proxy / ngày.

## 3. Bằng Chứng Thị Giác Google Hard Checkpoint (QR Code -> SMS Trap) & Kỷ Luật Soi Mắt
- **Đặc điểm & Đường dẫn lưu trữ:**
  - Ảnh chụp màn hình lỗi khi gặp checkpoint được lưu tại: `D:\Taadaa\GPM auto\debug_screenshots\oauth_<email>_hard_phone_checkpoint_<timestamp>.png`.
  - Màn hình hiển thị: Tiêu đề *"Xác minh thông tin để tiếp tục"*, email tài khoản, thông báo *"Google cần xác minh một số thông tin về thiết bị hoặc số điện thoại của bạn trước khi bạn có thể tiếp tục..."*, kèm mã QR ở trung tâm và nút *"Thử cách khác"*.
  - **Bản chất kỹ thuật:** Đây là rào chắn `challenge/iap`. Quét mã QR bằng điện thoại sẽ dẫn thẳng vào form bắt nhập số điện thoại để nhận OTP SMS. Farm không có SIM cho từng máy nên bắt buộc dừng ngay để hạ nhiệt (Cooldown 24h), tránh Google trảm tài khoản vĩnh viễn.
- **Kỷ luật Invariant LLM Soi Mắt Đọc Ảnh:**
  - Do ảnh GPM chụp full màn hình 1920x953 có nền trắng rộng làm loãng nội dung, Coordinator BẮT BUỘC crop phần trung tâm (ví dụ `(0.3*w, 0.1*h, 0.7*w, 0.9*h)`) trước khi gọi `browser_vision` hoặc `WinRT OCR`.
  - Tuyệt đối cấm ném link ảnh mù `MEDIA:<path>` nếu chưa xác nhận tận mắt qua vision tiêu đề, email và nội dung cảnh báo.

## 4. Định Vị & Truy Vết Kết Quả Batch Reg Gmail Trên Admin-PC (Máy 201-280)
- **Cấu trúc thư mục Runtime trên Admin-PC:**
  - Runner `run_parallel.ps1` lưu toàn bộ artifacts của từng đợt chạy tại:
    `D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_<timestamp>\`
- **Các file tra cứu chuẩn xác (O(1) Zero-Scan):**
  - `summary.json`: Báo cáo tổng hợp nhanh nhất, chứa danh sách 15 máy kèm trạng thái (`SUCCESS`, `PHONE_VERIFY`, `FAILED_OTHER`), lý do lỗi cụ thể, email đã tạo và mã exitCode.
  - `results\machine_<stt>.success.json`: Bằng chứng tài khoản đã tạo thành công thực tế của từng máy.
  - `merge_success_summary.json` & `merge_success_summary.txt`: Báo cáo gộp tài khoản vào workbook Excel.
  - `machine_<M>.log`: Chi tiết log chạy của từng máy `M`.
- **Kỷ luật truy vấn từ xa qua `admin_ssh.py`:**
  - Tuyệt đối không dùng lệnh `python -c "import openpyxl..."` qua SSH vì sẽ bị Coordinator Guard chặn do vi phạm allowlist.
  - Dùng PowerShell lệnh `Get-Content` đọc trực tiếp file `summary.json` để lấy thông tin tức thì trong < 3 giây mà không vi phạm guard.
