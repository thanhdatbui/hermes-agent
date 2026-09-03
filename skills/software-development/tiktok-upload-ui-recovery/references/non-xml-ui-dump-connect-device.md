# non_xml_ui_dump tại CONNECT_DEVICE → B1 ATX-kill bằng adb_client (2026-08-10)

## Root cause

`non_xml_ui_dump` (close_all_apps_start fail khi startup) = **uiautomator service TREO/Killed**,
KHÔNG phải lỗi timeout. Bằng chứng: `adb shell uiautomator dump` trả `Killed`; tăng timeout
dump 10/15s→60s KHÔNG cứu được (log fail sau 16s, không phải 60s).

## Vì sao ladder B1 ATX-kill KHÔNG chạy cho CONNECT_DEVICE (dù code có sẵn)

Ladder 3 bước tồn tại trong `_run_ui_failure_ladder` (B1 `_recover_uiautomator`, B2 relaunch, B3 soft reboot)
nhưng CONNECT_DEVICE không bao giờ tới được nó, 2 lý do đan nhau:

1. `_handle_connect_device` fail ở `close_all_apps_start` → set `is_ui_unavailable=True` + return False
   NGAY attempt 1. Retry wrapper (`_execute_with_ui_retry`) thấy `is_ui_unavailable` → **break, không attempt 2/3**.
2. `adapter=None` tại thời điểm đó — adapter được tạo SAU startup thành công. Mà ladder lấy
   `adb = getattr(adapter, "_adb", None)` → `adb=None` → B1 không có adb để chạy → ladder vô hiệu.
   Adb thật nằm ở `self.context.adb_client` nhưng ladder không dùng.

## Fix (commit 7d01c52)

Trong `_handle_connect_device`, nhánh startup fail (không phải empty-recents hợp lệ):
gọi `_recover_uiautomator(self.context.adb_client, timeout=10, attempts=[], label="connect_device_atx_kill")`
TRƯỚC khi set `is_ui_unavailable` + return False. Log marker: `[ANDROID_STARTUP] Ui dump fail -> B1 ATX-kill tại CONNECT_DEVICE`.

## Verify

- Test: `test_connect_device_ui_dump_failure_runs_b1_atx_kill` — CONNECT_DEVICE startup fail
  `non_xml_ui_dump` → `_recover_uiautomator` được gọi với adb_client.
- Pattern chung: handler fail vì UI/dump mà `adapter` chưa tồn tại (early state) → dùng
  `self.context.adb_client` cho B1, đừng ngầm giả định ladder sẽ tự chạy.