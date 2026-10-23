# Preflight XiaoWei & Port 5038 Drain Trong TikTok Feed Session

## 1. Bản Chất Sự Cố
- Khi Tiểu Vi (`放卫安卓投屏` / `xiaowei.exe`) mở trên máy tính, tiến trình `adb.exe -P 5038` kết nối và giữ độc quyền các pipe WinUSB của 80 máy Samsung S7.
- Khi `run-feed-session.ps1` hoặc `tiktok_runner.py` chạy trên cổng mặc định 5037, các cuộc gọi ADB get-state và focus app thất bại với `device not found`, dẫn đến hàng chục máy bị đánh dấu "Mất kết nối ADB/USB" giả tạo.

## 2. Vị Trí Vá & Cơ Chế Pre-flight Gate
- **Tập tin:** `scripts/run-feed-session.ps1` (trước khối kiểm tra device-locks) và `tools/pre_session_device_gate.py` (`filter_healthy_machines`).
- **Logic xử lý:**
  1. Kiểm tra tiến trình `xiaowei` $\rightarrow$ dừng tiến trình bằng `Stop-Process -Force`.
  2. Quét cổng 5038 (TCP Listen). Nếu có tiến trình nghe:
     - Chạy `adb -P 5038 kill-server`.
     - Xác minh danh tính tiến trình sở hữu (chỉ dừng nếu tên là `adb` hoặc path thuộc `xiaowei`).
     - Tạm dừng 2 giây để Windows chuyển giao WinUSB endpoints về cổng 5037.
  3. Hậu kiểm (Post-condition): Kiểm tra lại xem cổng 5038 đã đóng hoàn toàn chưa trước khi tiếp tục.

## 3. Quy Tắc Thẩm Định
- Khi đưa bản vá dọn tiến trình qua Reviewer Closeout Gate, bắt buộc có kiểm tra danh tính tiến trình (chống tác dụng phụ) và hậu kiểm trạng thái giải phóng tài nguyên.
