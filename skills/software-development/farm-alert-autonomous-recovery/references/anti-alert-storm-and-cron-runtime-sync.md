# Anti-Alert Storm & Multi-Location Cron Runtime Synchronization

## 1. Nguyên nhân Gây Bão Alert (Alert Storm) Trong Farm
Khi một cronjob thất bại (ví dụ `NameError`, cú pháp hoặc lỗi thiết bị diện rộng), Telegram thường bị bắn dồn dập hàng chục alert ("bắn cả đống alert") do 3 cơ chế cộng dồn:
1. **Double-Fire (2 alert cho 1 lần crash):**
   - Script bắt ngoại lệ `except Exception as exc:` rồi tự gọi hàm alert (ví dụ `send_farm_script_alert()`) bắn trực tiếp 1 tin qua Telegram Bot API.
   - Script sau đó gọi `raise` dẫn đến exit code 1. Hermes Cron Scheduler (với `deliver: telegram:...` và `no_agent: true`) bắt được exit code 1 và stderr, tự động bắn thêm 1 tin thất bại nữa vào cùng nhóm Telegram.
2. **Cron Tick Frequency (Nhịp chạy định kỳ):**
   - Các job cron dọn dẹp hoặc watchdog thường chạy mỗi 5–15 phút (`*/15 * * * *`). Một lỗi không được sửa sẽ kích hoạt 4–12 lần/giờ × 2 alerts = 8–24 alerts dội về liên tục.
3. **Thiếu Cooldown / Debounce ở cả 2 đầu:**
   - Script không lưu vết lỗi đã báo trong ngày/ca (`state_data.get("last_script_err")`).
   - Hàm alert dùng chung (`send_farm_script_alert()`) không có bộ nhớ đệm cooldown theo hash `(script_name, error_reason)`.

## 2. Kỷ Luật & Giải Pháp Chống Alert Storm
1. **Debounce 1 giờ tại Framework (`automation_core.alerts`):**
   - `send_farm_script_alert()` tự động băm hash `(script_name, error_reason)` và kiểm tra cooldown (mặc định 3600s). Nếu cùng lỗi xảy ra liên tục trong 1 giờ, hệ thống bắt buộc IM LẶNG (`SILENT`), không gửi tin nhắn Telegram trùng lặp.
   - Bỏ qua cooldown khi chạy unit test (`FORCE_TEST_ALERT_DISPATCH=1`) hoặc có cờ `FARM_ALERT_DISABLE_COOLDOWN=1`.
2. **Debounce Ngoại Lệ Trong Script:**
   - Trong khối `except Exception as exc:`, chỉ gửi script alert khi `state_data.get("last_script_err") != err_msg`. Lưu lại `last_script_err` vào state file trước khi `raise`.
3. **Hiểu Rõ Semantics của `no_agent: true` trong Hermes Cron:**
   - Hermes Cron Scheduler đã tự động gửi cảnh báo khi script thoát với code != 0. Hạn chế tự gọi thêm Telegram Bot API trong `except` trừ khi cần format actionable card đặc biệt, và nếu có gọi bắt buộc phải debounce.

## 3. Quy Trình Đồng Bộ Runtime Cron (Multi-Location Sync)
Cron script trong hệ thống Taadaa tồn tại ở 3 vị trí:
1. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/` (Repo git source)
2. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/` (Bản đồng bộ OneDrive dùng chung Kibe/Admin)
3. `%LOCALAPPDATA%/hermes/scripts/` (Runtime thực tế mà Hermes Scheduler nạp để chạy)

### Cạm bẫy chết người:
- **Chỉ sửa file trong repo mà không đồng bộ sang runtime:** Khi Hermes scheduler kích hoạt relative script (`cron_clear_tiktok_cache.py`), nó đọc trực tiếp từ `%LOCALAPPDATA%/hermes/scripts/`. Sửa repo mà quên sync thì runtime vẫn chạy code cũ và crash lặp lại.
- **Kiểm chứng đồng bộ:** Khi sửa bất kỳ cron script nào, bắt buộc phải cập nhật đồng thời cả 3 nơi và kiểm chứng qua lệnh `cronjob action='run', job_id='...'` để xác nhận `execution_success: true` và `last_status: ok`.
