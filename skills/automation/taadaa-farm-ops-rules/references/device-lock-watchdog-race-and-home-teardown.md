# Race Condition Giữa Device Lock Auto-Reaper Và Watchdog Cảnh Báo

## 1. Bản chất vấn đề
- Hệ thống có cơ chế tự động giải phóng lock hết hạn TTL (ví dụ status `blocked` tối đa 60 phút, hoặc tiến trình owner đã chết) qua script `reap-dead-owner-locks.py`.
- Khi thiết bị chạm ngưỡng 60 phút, Reaper ở chu kỳ kế tiếp sẽ tự động dọn lock vào quarantine và force-stop app đưa máy về HOME sạch sẽ.
- **Race Condition / Báo ảo:** Nếu Watchdog (`watch_device_locks.py`) cũng đặt ngưỡng cảnh báo bằng đúng 60 phút (`ALERT_THRESHOLD = 60`), Watchdog sẽ phát hiện lock vừa chạm 66-70 phút và bắn cảnh báo khẩn cấp lên Telegram ngay trước hoặc cùng thời điểm Reaper chuẩn bị dọn. Điều này tạo ra cảnh báo thừa thãi ("sắp được quét nhả lock tự động mà tự nhiên còn báo").

## 2. Quy tắc thiết kế chuẩn hóa
1. **Ngưỡng Watchdog phải cao hơn TTL của Auto-Reaper (Fail-safe Alert):**
   - TTL của Reaper cho `blocked`: 60 phút (3600s).
   - Ngưỡng cảnh báo của Watchdog (`ALERT_THRESHOLD_MINUTES`, `ALERT_THRESHOLD_BLOCKED_MINUTES`): BẮT BUỘC đặt ở mức **90 phút** (hoặc 120 phút).
   - Ý nghĩa: Từ 0-60p là thời gian giữ hiện trường hợp lệ; từ 60-65p Reaper tự động dọn âm thầm không làm phiền người dùng. Chỉ khi nào lock kẹt >90p (Reaper đã quét nhiều vòng mà lock vẫn kẹt do lỗi file/tiến trình bất tử) thì Watchdog mới phát báo động lên Telegram.
2. **Tăng tần suất chạy Auto-Reaper:**
   - Đặt lịch cron của Reaper chạy dày hơn (`*/5 * * * *` thay vì `*/15 * * * *`) để đảm bảo lock hết hạn được dọn trong vòng 1-5 phút, không ngâm máy quá lâu làm lỡ ca chạy sau.
3. **Quy tắc Teardown bắt buộc đưa về HOME (All Scripts):**
   - Mọi script chạy xong (dù thành công hay gặp exception/failure) BẮT BUỘC trong khối `finally:` phải force-stop package và gửi `input keyevent 3` (KEYCODE_HOME).
   - Không ngâm màn hình app live khi lỗi; hiện trường lỗi đã được số hóa qua dump XML + Screencap PNG + Log.
