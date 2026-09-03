# Mocking Farm Alerts in Unit Tests

## Pitfall: Unmocked `send_farm_machine_alert` spams Telegram Farm Alerts
Khi chạy test runner (`pytest`) trên các module điều phối máy (như `multi_machine_feed_session.py`, `feed_swipe_smoke.py`, v.v.):
- Các failure branches thường gọi `automation_core.alerts.send_farm_machine_alert(machine=..., serial=..., error_reason=...)` để gửi cảnh báo realtime kèm ảnh chụp màn hình lên Telegram `Farm Alerts` group (`-5373649734`).
- Nếu test case giả lập lỗi (vd: `MagicMock` result, `NoneType`, proxy mapping failure, vpn disconnect) mà không mock `send_farm_machine_alert`, mỗi lần chạy test sẽ spam tin nhắn và ảnh chụp máy live thật lên nhóm Telegram.

## Best Practice
Luôn patch/mock `send_farm_machine_alert` ở cấp độ test suite hoặc test case:
```python
with (
    patch("flows.multi_machine_feed_session.send_farm_machine_alert"),
    # hoặc patch trực tiếp từ automation_core:
    patch("automation_core.alerts.send_farm_machine_alert"),
):
    ...
```
Hoặc trong fixture chung `conftest.py` tự động mock `send_farm_machine_alert` để bảo vệ test runner.
