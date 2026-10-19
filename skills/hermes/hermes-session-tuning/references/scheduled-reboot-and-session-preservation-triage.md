# Quy Trình Triage Auto-Reboot 3 Ca & Cơ Chế Bảo Toàn Session Hermes

## 1. Mục Đích & Lịch Trình Auto-Reboot Của Farm
- **Lịch trình cố định:** 3 mốc trong ngày: **`05:20` | `11:20` | `17:20`** (tạo vùng đệm an toàn 40 phút trước mỗi ca nuôi TikTok 06:00, 12:00, 18:00).
- **Mục tiêu:** Tự động khởi động lại Kibe PC và Admin PC để giải phóng RAM, reset bus USB, dọn sạch zombie process và refresh socket ADB trước ca làm việc mới.
- **Tiến trình thực thi:** Windows Task Scheduler gọi `C:\Taadaa_Service\farm_preflight_daily_reset.py`. Nhật ký ghi nhận tại `C:\Taadaa_Service\daily_reset.log`.

## 2. Kiểm Tra An Toàn (Preflight Gates) Trước Khi Reboot
Trước khi kích hoạt `shutdown.exe`, script bắt buộc kiểm tra 3 điều kiện fail-closed:
1. **Né Game:** Quét tiến trình `LeagueClientUx.exe`, `War3.exe`... Nếu đang trong trận đấu thì HỦY reboot.
2. **Né Automation Đang Chạy:** Quét danh sách tiến trình quan trọng (`run_tiktok.py`, `feed_session`, `download_by_niche`...) và active device locks (`~/.codex/device-locks/*.lock.json`). Nếu có máy đang chạy thì HỦY reboot.
3. **Parity Kibe & Admin:** Gửi lệnh SSH reboot Admin PC trước. Nếu Admin offline hoặc lỗi thì HỦY reboot Kibe PC để bảo toàn tính đồng bộ.

## 3. Hiện Tượng "Máy Bị Treo / Khựng" Lúc HH:20:07
- Tại thời điểm `HH:20:07`, `shutdown.exe /r` phát tín hiệu `WM_QUERYENDSESSION` và buộc đóng toàn bộ socket/process của các ứng dụng đang mở (GPMLogin, Chromium, Node.js, Python runner).
- Windows cần 5–10 giây để thu hồi tài nguyên, giải phóng bộ nhớ và flush disk cache, gây ra hiện tượng chuột/màn hình khựng tạm thời trước khi chuyển sang màn hình xanh *Restarting*.
- **Kết luận:** Đây là hành vi clean shutdown bình thường của hệ điều hành (ghi nhận Event ID 1074 bởi `User32` / `shutdown.exe`), hoàn toàn không phải treo máy, crash phần cứng hay BSOD (Event ID 41).

## 4. Cơ Chế Bảo Toàn Session Hermes (`preserve_in_flight_sessions`)
Ngay trước khi kích hoạt lệnh reboot (lúc `HH:20:04`), module `preserve_in_flight_sessions(lookback_minutes=20)` thực hiện:
1. **Quét các session active:** Đọc SQLite session database của Hermes Gateway.
2. **Phân loại trạng thái tin nhắn cuối:**
   - **Đang chạy dở (In-flight):** Tin nhắn cuối là `user`, `tool`, hoặc `assistant` có `tool_calls` đang pending.
     -> Đánh dấu `resume_pending = True`, ghi nhận `resume_reason = "restart_interrupted"`, xóa file `.clean_shutdown`.
     -> Khi Gateway khởi động lại sau reboot, Hermes sẽ **tự động resume tiếp tục thực thi** task đang dở.
   - **Đã hoàn tất (Idle/Completed):** Tin nhắn cuối là `assistant` (text thuần).
     -> Ghi nhận `Bo qua <key>: tin cuoi la 'assistant' (da tra loi xong)`.
     -> Không đánh dấu resume để tránh spam lại prompt cũ khi khởi động lại.
3. **Đối soát log khi User thắc mắc:**
   - Đọc `C:\Taadaa_Service\daily_reset.log`: Nếu ghi nhận `Tong so session duoc bao toan: 0` có nghĩa là toàn bộ các session trước thời điểm reboot đều đã trả lời xong và đang ở trạng thái chờ lệnh mới, không có phiên nào bị đứt gánh.

## 5. Quy Trình Kiểm Tra Nhanh O(1) (Triage Runbook)
Khi User hỏi "Nãy máy reboot à? Có treo hay rớt session nào không?":
1. **Kiểm tra Uptime thực tế:**
   ```python
   import ctypes
   uptime_hours = ctypes.windll.kernel32.GetTickCount64() / (1000 * 3600)
   print(f"Uptime: {uptime_hours:.2f}h")
   ```
2. **Đọc Event Log Windows:**
   Dùng `win32evtlog` đọc System Log:
   - Event ID 1074: Xác nhận clean restart bởi `shutdown.exe`.
   - Event ID 6005/6006: Thời điểm dừng và khởi động lại EventLog service.
3. **Đọc `C:\Taadaa_Service\daily_reset.log`:**
   Đọc 20 dòng cuối để lấy correlation ID, trạng thái sentinel, và xác nhận số session được bảo toàn (`Tong so session duoc bao toan: N`).
