# ATX Stub Temporary Instrumentation & ADB Host Reconnect (2026-09-04)

## Hiện tượng hiện trường (Máy 54, serial `ce12160c81c8acae0c`)
- Flow báo `ATX_SESSION_UNAVAILABLE` trong `feed-session-smoke` (baseline hoặc profile navigation).
- `adb shell` bị timeout (`adb command timed out: ... input keyevent 4`, `screencap -p`).
- ATX session trả `ATX_SESSION_STUB_NOT_RUNNING` hoặc `ATX_SESSION_EMPTY_HIERARCHY`.

## Root Cause 1: `adb reconnect device` vs `adb reconnect` (Xiaowei ADB)
- Khi socket USB giữa host Windows và thiết bị Samsung bị nghẽn (USB hub glitch/sụt áp micro-second), `AdbClient._reconnect_device` cũ chỉ gọi `adb -s <serial> reconnect device`.
- Trên bản ADB của Xiaowei (`1.0.32` / `1.0.39`), lệnh `reconnect device` trả về exit code `0` nhưng **không thực sự reset transport socket phía host**.
- Do exit code = 0, nhánh `if res.returncode != 0:` không bao giờ được kích hoạt $\rightarrow$ lệnh `adb -s <serial> reconnect` (host-side reconnect) bị bỏ qua $\rightarrow$ ADB command timeout tiếp diễn vô hạn.
- **Fix:** Luôn gọi trực tiếp `adb -s <serial> reconnect` (host reconnect) để nhận tín hiệu `reconnecting <serial> [device]` và giải phóng ngay kênh truyền.

## Root Cause 2: ATX Agent curl POST `/uiautomator` tạo Process tạm (sống ~18s)
- Trên Samsung S7 (Android 7/8), `atx-agent curl -X POST http://127.0.0.1:7912/uiautomator` kích hoạt `am instrument ...` nhưng runner này tự động kết thúc sau ~18s (`ActivityManager: Force stopping com.github.uiautomator ... finished inst`).
- Vòng lặp `ps -A` trong `reset_atx_agent` ban đầu thấy tiến trình `com.github.uiautomator` xuất hiện trong 18s đầu tiên nên đánh dấu `ready = True` và thoát ra mà **không chạy fallback monkey**.
- Sau 18s, tiến trình chết $\rightarrow$ lượt capture tiếp theo dính ngay `ATX_SESSION_STUB_NOT_RUNNING` $\rightarrow$ `ATX_SESSION_UNAVAILABLE`.
- **Fix:** Trong `reset_atx_agent`, luôn chạy `monkey -p com.github.uiautomator 1` trên Android 7/8 để khởi chạy Activity/Stub bền vững, sau đó mới poll `ps -A` kèm sleep 0.5s để bind JSON-RPC socket.

## Root Cause 3: `_session_dump_attempt` thiếu Restart khi `restart_attempts >= 1`
- Trong `_session_dump_attempt`, các attempt sau (`attempt_number > 1`) chỉ gọi `_ensure_atx_server_running` (chỉ check daemon atx-agent, không restart stub khi stub chết).
- **Fix:** Khi `attempt_number > 1`, tự động gọi `reset_atx_agent(adb, timeout=min(15.0, timeout))` trước khi retry để đảm bảo stub được phục hồi.
