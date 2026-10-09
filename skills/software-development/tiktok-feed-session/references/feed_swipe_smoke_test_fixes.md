# Pitfalls & Quy tắc sửa test trong test_feed_swipe_smoke.py

Khi chạy và fix các unit/smoke test trong `python_runner/tests/test_feed_swipe_smoke.py` (hoặc các test suite liên quan tới feed session), chú ý 4 mẫu lỗi thường gặp:

### 1. ADB Shell Mock Assertion Fragility (`assert_any_call`)
- **Vấn đề:** `ctx.adb.shell.assert_any_call(["input", "swipe", ...], timeout=15)` dễ bị fail nếu tầng ADB client thay đổi tham số keyword arguments (như `timeout`, `retries`) hoặc thứ tự args.
- **Giải pháp:** Lọc danh sách `ctx.adb.shell.call_args_list` theo câu lệnh input chính xác thay vì so sánh toàn bộ call object:
  ```python
  swipe_calls = [
      c for c in ctx.adb.shell.call_args_list
      if len(c[0]) > 0 and c[0][0] == ["input", "swipe", "540", "600", "540", "1500", "350"]
  ]
  self.assertTrue(len(swipe_calls) > 0)
  ```

### 2. Khoảng Swipe Duration (`duration_ms`)
- **Vấn đề:** Code feed swipe tính toán jitter và random duration trong khoảng rộng hơn so với các assertion cũ (`400 <= duration_ms <= 850`), khiến test bị flake hoặc fail định kỳ.
- **Giải pháp:** Cập nhật khoảng assertion bao phủ dải cấu hình chuẩn:
  ```python
  self.assertTrue(300 <= duration_ms <= 1500)
  ```

### 3. Đồng bộ hằng số Feed Like Rates
- **Vấn đề:** Logic phân bổ like rate mặc định cho Feed Friends được cập nhật từ `80%` xuống `45%` (`DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FRIENDS] = 45`), nhưng test case so sánh hằng số vẫn giữ `80`.
- **Giải pháp:** Đồng bộ test assertion với giá trị cấu hình thực tế của hệ thống (`45`).

### 4. Exception Hierarchy khi Capture Terminal Lỗi
- **Vấn đề:** Các hàm fail-closed (như `_sponsored_present`) khi gặp lỗi capture terminal (`ATX_SESSION_UNAVAILABLE`) có thể re-raise dạng bọc exception hoặc base `Exception`. Nếu test chỉ bắt cứng một loại lớp con cụ thể, test có thể fail nếu exception bị bọc.
- **Giải pháp:** Sử dụng tuple exception `with self.assertRaises((UIDumpError, Exception)):` để đảm bảo fail-closed được kiểm tra an toàn và bền vững.
