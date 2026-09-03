# UI Capture Retry Budget & Deadline Timer Invariants

## Context & Root Cause
Trong `python_runner/core/ui_capture.py`, logic `capture_required_ui_result` tính toán thời gian còn lại cho ATX retry và hard-reset:
```python
remaining_budget = bounded_deadline - (time.monotonic() - loop_start)
```
Nếu `loop_start = time.monotonic()` không được gán trước các vòng thử capture, khi ATX capture gặp lỗi hoặc cần retry, biến `loop_start` không tồn tại sẽ kích hoạt `NameError: name 'loop_start' is not defined`. Lỗi này làm gãy hàng loạt luồng worker (40-60 máy) trong batch nuôi acc.

## Invariant Rules
1. **Khởi tạo thời gian đo deadline ngay đầu hàm**: Mọi hàm capture/poll có sử dụng hiệu số thời gian `time.monotonic() - start_time` phải khởi tạo `loop_start = time.monotonic()` ngay sau khi xác định `bounded_deadline`.
2. **Không nuốt ngoại lệ không mong muốn**: Bọc retry phải bắt đúng ngoại lệ dự kiến (như `UIDumpError`, `Exception` giao tiếp ADB) nhưng không che giấu lỗi cú pháp/mã nguồn cục bộ.
3. **Chạy kiểm thử trước khi commit**: Luôn chạy `pytest python_runner/tests/test_feed_session_smoke.py` và `test_ui_dump.py` để verify mọi branch retry/reset ATX không bị lỗi `NameError` hay gãy hợp đồng dữ liệu.
