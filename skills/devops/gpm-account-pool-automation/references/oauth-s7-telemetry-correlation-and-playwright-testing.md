# OAuth S7 Telemetry Correlation ID & Playwright Test Verification

## 1. Chuẩn hóa correlation_id telemetry cho pipeline OAuth S7
Khi truyền telemetry tracking qua luồng OAuth S7 (`run_oauth_s7_pipeline.py`):
- Định dạng chuẩn: `correlation_id = f"m{mid:02d}_{int(time.time())}"`.
- Các hàm phụ trợ (`send_telegram_otp_alert`, `wait_for_otp_or_code`) phải nhận tham số `correlation_id: str = ""`.
- Nếu caller không truyền, hàm fallback tạo `cid = correlation_id or f"m{mid:02d}_{int(time.time())}"`.
- Đảm bảo tính nhất quán: Trong `process_account`, sinh `session_cid` một lần cho cả phiên chờ OTP và truyền thống nhất vào cả `send_telegram_otp_alert(..., correlation_id=session_cid)` và `wait_for_otp_or_code(..., correlation_id=session_cid)`.
- Log format chuẩn: `[M{mid:02d}] [TELEMETRY] correlation_id={cid} ...` để log parser và audit trace dễ dàng lọc và liên kết sự kiện.

## 2. Playwright Context Integration Testing & Pytest Scope Pitfall
- Trong test harness của Playwright CDP OAuth:
  - Khi mock/test `trigger_hot_chatgpt_oauth(page, ctx, email, mid, port, p_res)`, luôn mock đầy đủ cả `page` và `ctx` (với `ctx.pages = [page]`, `ctx.new_page = MagicMock(return_value=page)`).
- **Pitfall khi chạy pytest trong repo GPM auto**:
  - Chạy `pytest tests` trực tiếp có thể fail do import lỗi ở các suite cũ không có package `src` trong PYTHONPATH.
  - Luôn chỉ định rõ test target và cấu hình PYTHONPATH:
    ```bash
    PYTHONPATH=. pytest tests/test_run_oauth_s7_pipeline.py -v
    ```
