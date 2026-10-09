# Fast Targeted Login Recovery Pattern (Feed Session)

## Bối cảnh & Yêu cầu chuẩn hóa (Vượt ngưỡng audit 85đ)

Trong `python_runner/flows/feed_swipe_smoke.py`, cơ chế `_run_fast_targeted_login` phục hồi nhanh tài khoản bằng `tiktok_login_v1.py` trước khi fallback sang reconcile đầy đủ. Để đạt chuẩn audit code và telemetry truy vết:

1. **Timeout linh hoạt:**
   - Thay vì hardcode timeout dài (180s) khiến luồng swipe/smoke bị nghẽn khi gặp lỗi treo máy, sử dụng:
     ```python
     timeout_sec = float(ctx.config.get("fast_login_timeout_seconds", 90.0))
     ```
   - Timeout mặc định là 90s, có thể tinh chỉnh từ runner config.

2. **Telemetry Correlation ID:**
   - Cần đảm bảo mọi log action của fast login đều có `correlation_id` để kết nối phiên feed session với luồng sub-process login.
   - Trích xuất:
     ```python
     correlation_id = str(ctx.config.get("session_id") or getattr(ctx, "run_id", "") or f"fast_login_{machine_id}_{int(time.time())}")
     ```
   - Bổ sung `"correlation_id": correlation_id` vào trường `extra` của tất cả 4 hành động log:
     - `start_fast_login`
     - `finish_fast_login`
     - `fast_login_failed_fallback_reconcile`
     - `fast_login_exception_fallback_reconcile`

3. **Kiểm thử hồi quy (Unit Test):**
   - File test: `python_runner/tests/test_auto_login_fast_recovery.py`
   - Bắt buộc assert có mặt `"correlation_id"` và `"duration_seconds"` trong mock call log của cả các nhánh: thành công, thất bại trả mã lỗi, và timeout/exception fallback.
