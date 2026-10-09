# Auto Login Recovery Subprocess Pattern in Feed Session

Khi feed session (`feed_swipe_smoke.py`) phát hiện account bị thiếu trên device và kích hoạt flow phục hồi qua login reconcile (`_maybe_recover_missing_account_via_login`), cần đảm bảo các nguyên tắc kỹ thuật sau:

1. **Khử nhiễm môi trường (`PYTHONPATH`)**:
   - Subprocess gọi script reconcile (thường nằm ở repo khác như `tiktok-log-in` hoặc runner riêng) có thể bị ô nhiễm module nếu kế thừa trực tiếp `PYTHONPATH` của `tiktok-luot nuoi acc`.
   - Pattern chuẩn:
     ```python
     clean_env = dict(os.environ)
     clean_env.pop("PYTHONPATH", None)
     proc = subprocess.run(
         cmd,
         capture_output=True,
         text=True,
         env=clean_env,
         timeout=timeout_sec,
     )
     ```

2. **Timeout hợp lý cho Reconcile**:
   - Timeout mặc định không nên để quá dài (như 900s = 15 phút), vì sẽ gây nghẽn toàn bộ batch feed session của máy.
   - Nên đặt trần mặc định 300s (5 phút) và cho phép override qua config `reconcile_timeout_seconds`.
