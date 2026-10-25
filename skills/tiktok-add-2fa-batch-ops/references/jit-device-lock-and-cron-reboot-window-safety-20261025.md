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
     - Khử trùng lặp đa target trên cùng một thiết bị (`seen_machines`) để tránh trường hợp 2 worker cùng can thiệp vào 1 máy.
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

## 4. Kỷ Luật Target-Bound Differential Canary Cho Tác Vụ State-Mutating
- **Nguyên tắc "Sửa đâu — Canary nhắm trúng đó":**
  - Không chạy generic full-flow bừa bãi trên máy thật đối với script biến đổi dữ liệu (2FA, đổi Password, Upload video, Đăng ký): tránh làm lệch workbook, tốn OTP, hoặc đăng clip rác lên kênh đang nuôi.
  - Phân tách theo vết diff (`canary_matrix.json` & `canary_plan.py`):
    - *Exempt:* Diff chỉ ở tests, docs, config -> tự động miễn trừ Canary máy thật.
    - *Lock / Dispatcher hook:* Chỉ kiểm tra JIT lock và kế hoạch launch, không đi sâu vào luồng đổi mật khẩu/OTP.
    - *UI Probe hook:* Chỉ mở đúng màn hình mục tiêu (ví dụ Switcher, Form Bảo mật) -> chụp ảnh `MEDIA:` -> WinRT OCR xác nhận từ khóa -> đóng app về Home (`input keyevent KEYCODE_HOME`).
    - *In-Ca / Farm Busy Fallback:* Khi các máy đều đang bận ca nuôi, kích hoạt `--dry-run` chạy unit test suite của repo để cấp receipt an toàn mở khóa `safe_push` mà không cướp máy.

## 5. Quy Trình Đối Soát Workbook Trước Khi Probe Máy Thật
- **Hàm `freeze_targets` tự động lọc bỏ:**
  - Logic điều phối đọc workbook nguồn và tự động bỏ qua các máy/tài khoản đã có đầy đủ Password và 2FA (`has_2fa and not needs_pwd`).
  - **Bài học hiện trường:** Các máy trong báo cáo sự cố (như Máy 4, Máy 13) thực tế đã có đầy đủ 2FA từ trước trong workbook. Nếu chỉ định chạy 2FA trên các máy này, runner sẽ nhận 0 target và skip ngay.
  - **Kỷ luật:** Trước khi probe hoặc test thực địa, bắt buộc đọc workbook kiểm tra xem máy đó còn thiếu 2FA/Password hay không. Nếu tất cả đều đủ, chọn máy test chuyên dụng hoặc tài khoản chưa hoàn tất (unprotected).
