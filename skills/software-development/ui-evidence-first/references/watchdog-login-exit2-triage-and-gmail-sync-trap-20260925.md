# Watchdog Subprocess Exit=2 and Gmail Sync Pitfall (2026-09-25)

## 1. Bẫy Device Lock Tự Khóa (Parent Lock Self-Deadlock & Exit 2)
- Khi một watchdog script (ví dụ `cron_m3_restore_...py`) chiếm lock thiết bị qua `acquire_device_lock(machine=N, serial=DEV, project="...")`, sau đó gọi subprocess `tiktok_login_v1.py` mà KHÔNG truyền `--allow-parent-lock`:
  + Tiến trình con `tiktok_login_v1.py` cố lấy lại lock cho máy `N`, phát hiện conflict và kích hoạt `DeviceLockNeedsUserDecision`.
  + Script con lập tức dừng và trả về `exit=2` trong vòng < 2 giây, hoàn toàn chưa hề chạm vào thiết bị hay thực hiện bất kỳ bước login nào.
  + Hơn nữa, nếu project name của watchdog không nằm trong whitelist `PARENT_LOCK_PROJECTS`, thì ngay cả khi truyền `--allow-parent-lock`, script con vẫn bị từ chối kế thừa lock và trả về `exit=2`.
  + Nếu watchdog dùng `subprocess.run(..., capture_output=True)` nhưng không in `stdout`/`stderr` ra console, lỗi bị nuốt hoàn toàn và chỉ hiển thị `Login result exit=2`.

## 2. Kỷ luật Chẩn đoán Exit Code 2 của Subprocess
- `exit=2` trong `tiktok_login_v1.py` có ít nhất 3 nhánh độc lập:
  1. `DeviceLockNeedsUserDecision` (xung đột lock, thiếu `--allow-parent-lock`).
  2. `VPN GATE BLOCKED` (VPN/proxy chưa kết nối hoặc adb probe thất bại).
  3. `PENDING LOGIN` khi hoàn tất flow login mà không thành công (thiếu OTP, sai pass, timeout).
- TUYỆT ĐỐI CẤM suy diễn `exit=2` là do mật khẩu hay do tài khoản bị lỗi khi chưa đọc trực tiếp log của tiến trình con.
- Bắt buộc kiểm tra: (a) Lệnh gọi subprocess có cờ kế thừa lock không; (b) VPN status; (c) Trạng thái màn hình và log chi tiết từng bước.

## 3. Bẫy Gmail "Cảnh báo" (Action Required) & Kẹt "Đang nhận thư của bạn…"
- `dumpsys account` chỉ chứng minh tài khoản Google đã được thêm vào hệ điều hành Android (`AccountManagerService`).
- Sự tồn tại trong OS Account KHÔNG đồng nghĩa với việc app Gmail hoạt động bình thường:
  + Khi tài khoản bị Google phát hiện hoạt động bất thường / cần xác minh mật khẩu ("Cảnh báo" / Action Required), app Gmail sẽ bị treo ở trạng thái:
    `text="Đang nhận thư của bạn…"` kèm ProgressBar xoay liên tục.
  + Gmail account switcher không load được tài khoản đích hoặc kẹt sync, dẫn đến timeout tìm OTP sau 150s.
  + Khi nghi ngờ lỗi OTP Gmail, BẮT BUỘC kiểm tra UI XML màn hình Gmail để tìm node `text="Đang nhận thư của bạn…"` hoặc chuỗi `"Cảnh báo"` bên cạnh tên tài khoản.

## 4. Pre-login Gmail Live Gate (Kiểm tra Live trước khi Login)
- **Bắt buộc**: Trước khi mở app TikTok và bắt đầu form đăng nhập trong `tiktok_login_v1.py`, nếu tài khoản là Gmail (`@gmail.com` hoặc dùng `--otp-only`), BẮT BUỘC gọi hàm kiểm tra live trước (`check_gmail_is_live(email)` từ `D:/Taadaa/tools/check_gmail_live_fast.py`).
- **Fail-fast**: Nếu xác nhận Gmail DIE (`is_live is False`), chặn ngay từ đầu (`[gmail-live-gate] BLOCKED`), ghi log rõ ràng, không mở app và không chiếm màn hình thiết bị.

## 5. Kỷ luật Báo Cáo Không Viện Cớ Công Cụ (Anti-Excuse Invariant)
- Khi gặp lỗi lệnh môi trường (ví dụ `adb: command not found`), Coordinator TUYỆT ĐỐI CẤM:
  + Vội vàng kết luận "công cụ adb bị hỏng / thiếu trong PATH" làm blocker cho toàn bộ phiên.
  + Bắt buộc tra cứu đường dẫn chuẩn trong repo (như `C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc `inspect_machine.py`) trước khi phát ngôn.
  + Trả lời thẳng thắn, ngắn gọn, đi vào bản chất vấn đề thay vì thanh minh lý do kỹ thuật ngoài lề.
