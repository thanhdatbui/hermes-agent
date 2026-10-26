# Canary Remote Cluster Timeout & Auto-Login Recovery Pitfalls

## 1. Hiện Tượng Vấp Bẫy (Timeout False-Negative & Host Guard)
Khi chạy Canary nghiệm thu trên máy thuộc cụm từ xa (FARM ADMIN - máy 201-280) gặp lỗi thiếu nick (`ACCOUNT_MISSING` / `profile account mismatch`):
1. **Lỗi `MACHINE_OUT_OF_RANGE` (Host Guard Fail-Closed):**
   `canary_runner.py` chỉ truyền đường dẫn workbook của Admin (`taikhoan_run_safe.xlsx`) nhưng không gán biến môi trường:
   - `TAADAA_HOST_CONFIG = r"D:\Taadaa\machine-config\admin.yaml"`
   - `ADB_SERVER_SOCKET = "tcp:192.168.110.119:5037"`
   -> Runner văng ngay ở giây thứ 9 do `taadaa_host.py` kiểm tra máy 201+ ngoài phạm vi 1-80 của Kibe.
2. **Lỗi `CANARY_TIMEOUT` do đặt Timeout quá ngắn (300s):**
   - Khi thiếu tài khoản, feed runner kích hoạt chu trình phục hồi tự động gồm 2 tầng: Fast Login (`tiktok_login_v1.py`, timeout tối đa 420s) và Fallback Reconcile (`reconcile_tiktok_accounts.py`, timeout tối đa 600s).
   - Qua kết nối mạng LAN tới ADB Remote (`192.168.110.119:5037`), độ trễ dump UI XML và kiểm tra màn hình khiến quá trình này kéo dài từ 320s - 400s.
   - Nếu Coordinator đặt `--timeout 300`, Canary sẽ bị cắt ngang giữa chừng và báo `CANARY_VERDICT: FAILED` dù logic đang hoạt động bình thường!

---

## 2. Quy Chuẩn Thiết Lập Canary Nghiệm Thu Cụm Remote (Admin)

### A. Thời gian chờ BẮT BUỘC >= 720s
Với các ca Canary có can thiệp auto-login recovery hoặc máy remote:
```bash
python D:/Taadaa/tools/canary_runner.py --repo "tiktok-luot nuoi acc" --machine <M> --row <ROW> --timeout 720
```
- Tuyệt đối CẤM đặt `--timeout 300` khi test máy có auto-login recovery.

### B. Đồng bộ cấu hình Host trong `canary_runner.py`
Khi `m >= 200` hoặc cluster chứa `"Admin"`:
```python
if "Admin" in cluster or m >= 200:
    env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"
    env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
else:
    env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"
    env.pop("ADB_SERVER_SOCKET", None)
```

---

## 3. Khắc Phục Lỗi Hardcode Workbook Trong `feed_swipe_smoke.py`

Khi `_maybe_recover_missing_account_via_login` gọi `reconcile_tiktok_accounts.py`, bắt buộc phải phân giải workbook theo cụm thiết bị:
```python
_cluster = "admin" if (str(machine_id or "").isdigit() and int(machine_id) >= 200) else "kibe"
_root = Path(fr"D:\OneDrive\TaadaaData\{_cluster}")
workbook = Path(
    ctx.config.get("reconcile_workbook")
    or (_root / "taikhoan_run_safe.xlsx")
    or ctx.config.get("safe_workbook")
    or DEFAULT_RECONCILE_WORKBOOK
)
```
Và nạp `clean_env["TAADAA_HOST_CONFIG"] = str(Path(r"D:\Taadaa\machine-config") / f"{_cluster}.yaml")` trước khi thực thi subprocess.
