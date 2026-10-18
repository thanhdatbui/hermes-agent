# Gateway Routing Schema Drift & Reboot Preserve Crash (18/10/2026)

## 1. Hiện Tượng & Sự Cố
- Vào mốc 05:20 sáng ngày 18/10/2026, Task Scheduler kích hoạt `farm_preflight_daily_reset.py` để reboot chuẩn bị cho Ca 1 (06:00).
- Tuy nhiên, script crash ở bước kiểm tra bảo toàn phiên Hermes:
  `[RESUME] preserve_in_flight_sessions loi khong xu ly duoc, huy reboot ca Admin va Kibe PC de bao toan session: preserve_in_flight_sessions that bai: schema SessionDB khong khop: bang gateway_routing thieu cot ['key', 'value']`
  `[SUMMARY] {"outcome": "aborted_preserve_failed"}`
- **Hệ quả dây chuyền:**
  1. Fail-safe huỷ bỏ lệnh reboot của cả Kibe PC và Admin PC để bảo toàn dữ liệu.
  2. Mốc 11:20 trưa tiếp theo bị `[SKIP]` do có active device lock của tiến trình nuôi acc trước đó.
  3. Máy tính chạy liên tục hơn 20 tiếng không được xả bus USB 2.0 EHCI.
  4. Đến đầu mỗi phiên (Ca 1 lúc 06:05 và Ca 2 lúc 12:00), khi 80 máy đồng loạt bắn command kiểm tra focus và dump XML, bus USB bị nghẽn đệm.
  5. Các lệnh `dumpsys` và `screencap` bị delay 5–10s khiến hàm `_wait_for_profile_loading_spinner` tưởng app đang xoay vòng `tux_loading_hud` hoặc `account-switcher-not-open`, làm gần 150 máy bị báo fail oan ở Phiên 1.

## 2. Nguyên Nhân Gốc Rễ (Schema Drift giữa Fake DB trong Test vs Real SQLite)
- Trong `farm_preflight_daily_reset.py`, biến `_SESSION_SCHEMA_REQUIREMENTS` định nghĩa:
  ```python
  _SESSION_SCHEMA_REQUIREMENTS = {
      "gateway_routing": ("scope", "key", "value"),  # <--- SAI LỆCH VỚI REAL DB
      "messages": ("id", "session_id", "role", "tool_calls", "timestamp", "active"),
  }
  ```
- Nhưng bảng `gateway_routing` trong SQLite thực tế (`hermes_state.py`) có schema:
  ```sql
  CREATE TABLE gateway_routing (
      scope TEXT NOT NULL DEFAULT '',
      session_key TEXT NOT NULL,
      entry_json TEXT NOT NULL,
      updated_at REAL NOT NULL,
      PRIMARY KEY (scope, session_key)
  );
  ```
- Tên cột thực tế là `session_key` và `entry_json`, không phải `key` và `value`.
- Bộ unit test cũ dùng `FakeSessionDB` với schema giả lập `(scope, key, value)` nên 130 test vẫn xanh 100%, tạo điểm mù che giấu lỗi khi chạy thực tế trên Host.

## 3. Bản Vá Chuẩn Hóa O(1)
1. **Sửa `_SESSION_SCHEMA_REQUIREMENTS`:**
   ```python
   _SESSION_SCHEMA_REQUIREMENTS = {
       "gateway_routing": ("scope", "session_key", "entry_json"),
       "messages": ("id", "session_id", "role", "tool_calls", "timestamp", "active"),
   }
   ```
2. **Đồng bộ unit test `FakeSessionDB`:**
   Cập nhật `FakeSessionDB` tạo đúng cột `session_key` và `entry_json`, đồng bộ câu lệnh SQL `SELECT session_key, entry_json` và `UPDATE gateway_routing SET entry_json = ? WHERE scope = ? AND session_key = ?`.
3. **Đồng bộ file triển khai:**
   Copy bản vá từ repo quản lý `D:/Taadaa/tools/services/Taadaa_Service/farm_preflight_daily_reset.py` sang đường dẫn chạy trên hệ điều hành `C:/Taadaa_Service/farm_preflight_daily_reset.py`.

## 4. Kiểm Thử Nghiệm Thu
- Chạy unit test: `python -m pytest D:/Taadaa/tools/tests/test_farm_preflight_daily_reset.py -q` $\rightarrow$ 130/130 PASSED.
- Kiểm thử trực tiếp trên DB thật của Hermes Gateway:
  `preserve_in_flight_sessions(lookback_minutes=60)` chạy thành công, bảo toàn an toàn các session đang dở mà không bị văng ngoại lệ schema.
