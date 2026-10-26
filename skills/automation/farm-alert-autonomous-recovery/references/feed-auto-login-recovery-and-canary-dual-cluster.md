# Feed Session Auto-Login Recovery & Dual-Cluster Canary Invariants

## 1. Hiện Tượng & Nguyên Nhân Gốc (Root Cause)
Khi ca nuôi feed (`tiktok-luot nuoi acc`) phát hiện thiếu tài khoản mục tiêu (`ACCOUNT_MISSING` / `expected account was not found`) hoặc lệch nick trên thiết bị Admin (máy 201–280):
- **Triệu chứng lỗi:**
  ```text
  CONFIG_ERROR: machine 261 has no serial in workbook
  ```
  hoặc runner văng lỗi:
  ```text
  Host guard error: MACHINE_OUT_OF_RANGE: machine=261 không thuộc host kibe (range 1-80). Dừng fail-closed.
  ```
- **Bản chất lỗi:**
  1. Trong `python_runner/flows/feed_swipe_smoke.py` (`_maybe_recover_missing_account_via_login`), các tham số workbook mặc định của Reconcile (`reconcile_workbook`, `login_workbook`, `proxy_mapping`) bị hardcode cố định về thư mục Kibe (`D:\OneDrive\TaadaaData\kibe\...`). Khi máy thuộc Admin (máy $\ge 200$), script truyền sai workbook của Kibe khiến `reconcile_tiktok_accounts.py` không tìm thấy serial của máy.
  2. Môi trường `clean_env` của tiến trình con Reconcile thiếu biến `TAADAA_HOST_CONFIG = D:\Taadaa\machine-config\admin.yaml`.
  3. Tool `canary_runner.py` khi chạy đơn máy kiểm chứng hotfix cho máy Admin ($\ge 200$) truyền đúng workbook path nhưng thiếu việc nạp `TAADAA_HOST_CONFIG = admin.yaml` và `ADB_SERVER_SOCKET = tcp:192.168.110.119:5037` vào `env` của child process.

---

## 2. Chuẩn Hóa Điều Phối Đa Cụm (Dual-Cluster Invariants)

### A. Tự động nhận diện cụm theo dải máy trong Feed Runner (`feed_swipe_smoke.py`)
Tại hàm `_maybe_recover_missing_account_via_login`:
```python
_cluster = "admin" if (str(machine_id or "").isdigit() and int(machine_id) >= 200) else "kibe"
_root = Path(fr"D:\OneDrive\TaadaaData\{_cluster}")

workbook = Path(
    ctx.config.get("reconcile_workbook")
    or (_root / "taikhoan_run_safe.xlsx")
    or ctx.config.get("safe_workbook")
    or DEFAULT_RECONCILE_WORKBOOK
)

login_workbook = Path(
    ctx.config.get("reconcile_login_workbook")
    or (_root / "taikhoan_dat_v2_updated .xlsx")
    or ctx.config.get("login_workbook")
    or DEFAULT_RECONCILE_LOGIN_WORKBOOK
)

proxy_mapping = Path(
    ctx.config.get("reconcile_proxy_mapping")
    or (_root / "PROXYgandienthoai.xlsx")
    or ctx.config.get("proxy_mapping")
    or DEFAULT_RECONCILE_PROXY_MAPPING
)

clean_env = dict(os.environ)
clean_env.pop("PYTHONPATH", None)
clean_env["TAADAA_HOST_CONFIG"] = str(Path(r"D:\Taadaa\machine-config") / f"{_cluster}.yaml")
```

### B. Môi trường bắt buộc khi chạy Canary máy Admin (`tools/canary_runner.py`)
Khi `canary_runner.py` điều phối máy $m \ge 200$:
```python
env = os.environ.copy()
if "Admin" in cluster or m >= 200:
    env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"
    env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
else:
    env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"
    env.pop("ADB_SERVER_SOCKET", None)
```

---

## 3. Checklist Triage & Hậu Kiểm O(1)
- [ ] Kiểm tra workbook target: Máy 1-80 trỏ về `D:\OneDrive\TaadaaData\kibe`, máy 201-280 trỏ về `D:\OneDrive\TaadaaData\admin`.
- [ ] `openpyxl` kiểu dữ liệu cột Machine trong `taikhoan_run_safe.xlsx`: Luôn ép kiểu `str(cell_value).strip()` vì cột máy lưu dưới dạng chuỗi (`"201"`, `"261"`), tránh so sánh trực tiếp số nguyên `== 261` dẫn đến `Found: False`.
- [ ] Timeout Canary cho Auto-Login Recovery: Flow login bao gồm mở TikTok, kiểm tra UI XML, xử lý OTP IMAP và đổi nick, tổng thời lượng có thể chạm ngưỡng 180s - 420s; cấm đặt timeout canary đơn máy quá ngắn ($\le 60s$).
