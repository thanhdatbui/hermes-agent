# Account Switcher & Slot Elimination Testing

## Nguyên tắc & Lưu ý
Khi test hoặc mở rộng logic account switcher / slot elimination trong `feed_swipe_smoke.py` (`_find_user_placeholder_switch_options`):
- `_find_user_placeholder_switch_options(xml_text, expected_account="", machine=None, known_other_accounts=None)` hỗ trợ nhận `known_other_accounts: list[str] | None = None`.
- Khi `known_other_accounts` được truyền vào, hàm sử dụng danh sách này trực tiếp thay vì cố gắng đọc `hermes_cron_source_config.json` từ đĩa. Điều này giúp unit test chạy nhanh, cách ly và deterministic hoàn toàn.
- Lệnh chạy unit test:
  ```bash
  pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_user_placeholder_switcher.py" -v
  ```
