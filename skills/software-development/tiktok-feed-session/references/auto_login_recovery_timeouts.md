# Fast Login & Reconcile Recovery Timeouts in feed_swipe_smoke.py

## Overview
Khi runner mẹ `feed_swipe_smoke.py` kích hoạt auto login recovery để cứu hộ account bị thiếu hoặc kẹt session, nó gọi các tiến trình con (`_run_fast_targeted_login` và `_maybe_recover_missing_account_via_login`).

## Timeout Configurations
1. **Fast Targeted Login (`_run_fast_targeted_login`)**:
   - Config key: `fast_login_timeout_seconds`
   - Default: `420.0`s (tăng từ 180s)
   - Lý do: Trên thiết bị thực và proxy farm, chu trình khởi động app, điền thông tin, chờ OTP/2FA và xác thực cần nhiều thời gian hơn 3 phút. Mức 420s (7 phút) ngăn runner mẹ premature termination.

2. **Full Reconcile Recovery (`_maybe_recover_missing_account_via_login`)**:
   - Config key: `reconcile_timeout_seconds`
   - Default: `600.0`s (tăng từ 300s)
   - Lý do: Reconcile chạy full scope takeover gồm scan device, đối soát slot, cập nhật workbook và recover account, đòi hỏi tối đa 10 phút.

## Verification
- Test file: `python_runner/tests/test_auto_login_fast_recovery.py`
- Test case: `test_fast_login_default_timeout_increased` xác nhận kwargs `timeout == 420.0` khi gọi `subprocess.run`.
