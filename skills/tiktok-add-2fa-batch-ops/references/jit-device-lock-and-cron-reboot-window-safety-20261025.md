# Tối Ưu Hóa Device Lock: Chuyển Đổi Sang Just-In-Time (JIT) Lock (2026-10-25)

## 1. Vấn Đề Xung Đột Của Cơ Chế Khóa Hàng Loạt (Bulk Pre-Reservation)
- **Hiện tượng (Sự cố Ca 1 - 25/10/2026):**
  - Tool 2FA quét danh sách nick chưa có 2FA trên Farm Admin (44 máy).
  - Tiến trình cha gọi `acquire_device_lock(status="queued", project="tiktok-add-bao-mat-f2a")` đồng loạt cho toàn bộ 44 máy và ghi 44 file `.lock.json` vào `C:\Users\Admin\.codex\device-locks\`.
  - Trong khi 2FA chỉ chạy song song vài worker theo `max_workers`, hàng chục máy còn lại bị giữ lock vô ích ở trạng thái chờ (`queued`).
  - Cùng lúc đó, batch Upload Video khởi chạy và kiểm tra thiết bị, gặp file lock của 2FA -> Kích hoạt fail-closed an toàn của `automation-core`, ném lỗi `[NEEDS_USER_DECISION] ACQUIRE_LOCKS` trên 44 máy.

## 2. Giải Pháp: Just-In-Time (JIT) Lock
- **Nguyên tắc:** "Làm tới máy nào, lock máy đó; xong máy nào, nhả máy đó".
- **Kiến trúc luồng xử lý:**
  1. Trong tiến trình cha `python_runner/run_batch_live_2fa.py`:
     - Bỏ hoàn toàn vòng lặp giữ lock trước (`pre-reservation`) cho tất cả targets.
     - Lập `launch_plan` phân bổ máy theo độ trễ giãn cách (stagger ms) và đưa trực tiếp vào `ThreadPoolExecutor`.
     - Không sinh ra bất kỳ file lock `queued` nào ở tiến trình cha.
  2. Trong tiến trình con `python_runner/run_capture_phase_b.py`:
     - Từng worker khi bắt đầu thực thi trên thiết bị sẽ tự gọi `acquire_device_lock(command="phase-b-live")`.
     - Chỉ có những máy đang thực sự được worker thao tác mới có file `.lock.json`.
     - Ngay khi worker hoàn thành hoặc gặp lỗi, lock được release/handoff ngay lập tức, giải phóng thiết bị cho các batch khác (Upload, Feed, Follow).

## 3. Lịch Trình Cron Cả Ngày & An Toàn Khung Giờ Reboot
- Khi cấu hình job 2FA chạy cả ngày, bắt buộc bọc trong hàm kiểm tra khung giờ an toàn `is_safe_rolling_window()`:
  - Né triệt để các khung giờ bảo trì / reboot máy (ví dụ: các khung đệm trước giờ nuôi và khung reboot định kỳ).
  - Khi gần đến giờ reboot hoặc chuẩn bị cho ca cron mới, watchdog tự động hoãn (skip) không dispatch worker mới để tránh bị reboot ngắt quãng giữa chừng.
