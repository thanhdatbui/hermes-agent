# Auto-Login Recovery Cluster Routing & Remote Canary Pitfalls

## 1. Auto-Login Recovery trong Feed Runner (`python_runner/flows/feed_swipe_smoke.py`)
Khi feed session gặp `profile account mismatch` hoặc `account_missing`, hệ thống kích hoạt `_maybe_recover_missing_account_via_login()`:
- **Nguy cơ lỗi:** Hardcode workbook Kibe (`D:\OneDrive\TaadaaData\kibe\...`) khi máy đích thuộc cụm Admin (`machine_id >= 200`) dẫn đến lỗi `CONFIG_ERROR: machine <N> has no serial in workbook`.
- **Chuẩn hóa bắt buộc:**
  ```python
  _cluster = "admin" if (str(machine_id or "").isdigit() and int(machine_id) >= 200) else "kibe"
  _root = Path(fr"D:\OneDrive\TaadaaData\{_cluster}")
  workbook = Path(ctx.config.get("reconcile_workbook") or (_root / "taikhoan_run_safe.xlsx") or ...)
  login_workbook = Path(ctx.config.get("reconcile_login_workbook") or (_root / "taikhoan_dat_v2_updated .xlsx") or ...)
  proxy_mapping = Path(ctx.config.get("reconcile_proxy_mapping") or (_root / "PROXYgandienthoai.xlsx") or ...)
  clean_env["TAADAA_HOST_CONFIG"] = str(Path(r"D:\Taadaa\machine-config") / f"{_cluster}.yaml")
  ```

## 2. Canary Timeout Kỷ Luật (Chống False-Negative)
- Khi chạy Canary đơn máy cho các ca có auto-login recovery (`_run_fast_targeted_login` + `reconcile_tiktok_accounts`):
  Thời gian tương tác UI và giải quyết challenge OTP/2FA qua mạng Remote ADB thường tốn 300s - 400s.
- **Kỷ luật vận hành:** BẮT BUỘC đặt `--timeout >= 720` (12 phút) cho `canary_runner.py`. Tuyệt đối cấm đặt `--timeout 300` gây timeout giả tạo.
