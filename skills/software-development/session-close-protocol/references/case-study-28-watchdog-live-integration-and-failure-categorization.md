## 28. Case Study 68 -> 77 -> 82 -> 84 -> 91/100 (APPROVED) trong repo `Hermes` (`cron_chatgpt_web_pool_watchdog.py`) — Bẫy Mock Nông (15/25), Thiếu Failure Categorization, Live Integration Test Với Daemon Cục Bộ (:20129, :19995), SQLite Rollback & Van An Toàn 7 Ngày

### 1. Bẫy Mock Nông Bị Đánh Tụt Test Evidence (15/25 -> 22/25đ):
- Khi watchdog script có quy mô lớn (>900 dòng), việc chỉ dùng unit test mock thuần túy sẽ bị Sol Auditor đánh rớt ở các mức 68-84/100 với nhận xét: *"Bằng chứng hiện tại chỉ bao phủ các hàm đơn giản bằng mock. Phần cốt lõi quyết định chất lượng watchdog là tự động hóa tài khoản thật và thao tác farm chưa được chứng minh."*
- **Khắc phục triệt để**:
  1. **Live Integration Tests**: Bổ sung test cases kết nối thực tế tới daemon cục bộ đang chạy:
     - Query danh sách connection thực tế từ OmniRoute daemon `http://127.0.0.1:20129/api/providers`.
     - Query danh sách profile từ GPMLogin API `http://127.0.0.1:19995/api/v3/profiles`.
     - Kiểm tra schema bảng `provider_connections` và `combos` trực tiếp trên SQLite `storage.sqlite`.
     - Lưu ý: Dùng `self.skipTest(...)` an toàn nếu daemon tạm thời không reachable để không làm fail CI.
  2. **SQLite Schema Mutation Test Thực Tế**: Tạo file sqlite tạm thời với schema chuẩn của OmniRoute, thực hiện update và assert trực tiếp các trường `is_active=1`, `test_status='active'`, và append model `chatgpt-web/gpt-5.6-sol-high` vào `combos.data`.
  3. **Rollback Transaction Test**: Bọc khối DB bằng `try...except...conn.rollback()...finally: conn.close()`, kèm test case inject lỗi I/O assert `mock_conn.rollback.assert_called_once()`.

### 2. Bẫy Thiếu Failure Categorization Trong Telemetry (Kẹt 84/100 Thiếu Đúng 1 Điểm):
- **Hiện tượng**: Mảng `failures` trong telemetry payload chỉ lưu chuỗi thô `error: str(err)[:100]`. Reviewer Sol Auditor đánh giá: *"Telemetry thiếu metric latency, failure category, retry count để phục vụ triage và điều tra sự cố"*, khiến điểm dừng ở 84/100 (REJECTED).
- **Khắc phục**: Tự động phân loại lỗi trước khi emit telemetry:
  ```python
  categorized_failures = []
  for a, err in all_failed:
      err_str = str(err).lower()
      cat = "UNKNOWN"
      if "phone" in err_str or "số điện thoại" in err_str:
          cat = "PHONE_CHECKPOINT"
      elif "timeout" in err_str:
          cat = "TIMEOUT"
      elif "proxy" in err_str:
          cat = "PROXY_ERROR"
      elif "recaptcha" in err_str:
          cat = "CAPTCHA_CHALLENGE"
      categorized_failures.append({"account": a, "category": cat, "error": str(err)[:100]})
  ```

### 3. Bẫy Dead Code Van An Toàn 7 Ngày GPM (Safety Valve Dead Code):
- **Hiện tượng**: Code định nghĩa hàm `is_profile_aged_7_days(profile, min_days=7)` nhưng trong luồng `refresh_antigravity_account_via_gpm` lại không gọi tới. Reviewer chỉ trích: *"Van an toàn 7 ngày được implement nhưng không được gọi trong controller Antigravity recovery"*.
- **Khắc phục**: Enforce ngay ở đầu hàm:
  ```python
  if profile_data and not is_profile_aged_7_days(profile_data, min_days=7):
      return False, "Van an toàn: Profile GPM chưa đủ 7 ngày tuổi để thực hiện OAuth Antigravity"
  ```
  Kèm unit test kiểm tra profile 10 ngày tuổi (True) vs profile 2 ngày tuổi (False + chặn gọi recovery).

### 4. Bẫy Telemetry Crash Khi Ổ Đĩa Lỗi (Telemetry Resilience):
- Telemetry là tầng giám sát, tuyệt đối không được làm sập tiến trình nghiệp vụ chính khi gặp lỗi đĩa đầy hoặc từ chối quyền ghi. Bọc `save_telemetry_metrics` bằng `try...except Exception: log("[TELEMETRY-CRITICAL-ALERT]...") return False`. Kèm unit test mock `builtins.open` ném `IOError` để chứng minh hệ thống vẫn tiếp tục chạy an toàn.
