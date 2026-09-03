# Mocking Farm Alerts in Consumer Tests

## Pitfall: Unmocked `send_farm_machine_alert` spams Telegram Farm Alerts
Khi consumer repos (như `tiktok-luot nuoi acc`, `Tiktok_Reg`, `tiktok-follow`, v.v.) bắt lỗi trong multi-machine batch runner, chúng thường gọi `automation_core.alerts.send_farm_machine_alert()`.
Nếu trong unit test (`pytest`), các test case giả lập lỗi máy (dummy account, fake serial, exception) không mock `send_farm_machine_alert`, tiến trình test sẽ gửi request HTTP multipart thật lên Telegram Bot API và spam tin nhắn/ảnh chụp thật vào channel/group Telegram Farm Alerts (`-5373649734`).

## Solution
1. **Mock ở fixture/test level:** Luôn mock `automation_core.alerts.send_farm_machine_alert` hoặc mock trực tiếp import tại module đang test.
2. **Kiểm tra autouse fixture:** Đặt fixture autouse trong `conftest.py` của test suite để ngăn chặn việc rò rỉ network call tới Telegram khi test lỗi.
