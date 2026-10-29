# Admin Cluster Remote ADB Socket Injection & Welcome Back Switcher Triage (29/10/2026)

## 1. Bản Chất Sự Cố (Root Cause)
- **Bối cảnh:** Khi chạy Batch nuôi account / lướt feed trên cụm Admin (Máy 201–280), hệ thống bắn P0 Batch Alert: "Phát hiện máy dính lỗi login / mất phiên".
- **Hai mắt xích lỗi đồng thời:**
  1. **False Positive Login Screen:** TikTok hiển thị bottom-sheet / giao diện danh sách tài khoản đã lưu với tiêu đề *"Chào mừng bạn trở lại"* (Welcome back). Nick cần nuôi (`expected_account`) đã nằm sẵn ở vị trí số 3 trong danh sách. Tuy nhiên, bộ từ điển `_ACCOUNT_SWITCHER_TITLES` thiếu cụm từ này, khiến runner phân loại nhầm thành `manual-needed:login` ("login/account screen detected").
  2. **Dual-Cluster Missing Socket Gap:** Khi bị gán cờ `manual-needed:login`, runner kích hoạt luồng cứu hộ tự động `_maybe_recover_missing_account_via_login` (`reconcile_tiktok_accounts.py`) và `_run_fast_targeted_login` (`tiktok_login_v1.py`). Hai script này được spawn qua subprocess nhưng **thiếu biến môi trường `ADB_SERVER_SOCKET = tcp:192.168.110.119:5037`** và `TAADAA_HOST_CONFIG = D:/Taadaa/machine-config/admin.yaml` khi `machine_id >= 200`. Tiến trình con fallback về local ADB server của Kibe, không thấy thiết bị Admin, dẫn đến bị treo (hang) 17 phút (timeout 420s + 600s).

---

## 2. Quy Tắc Vá Code O(1) Cho Fast Login & Reconcile Environment
Trong `python_runner/flows/feed_swipe_smoke.py`:
1. **Bổ sung Switcher Titles:**
   ```python
   _ACCOUNT_SWITCHER_TITLES = {
       "chuyển đổi tài khoản",
       "chuyen doi tai khoan",
       "switch account",
       "switch accounts",
       "chào mừng bạn trở lại",
       "chao mung ban tro lai",
       "welcome back",
   }
   _ADD_ACCOUNT_OPTION_TEXTS = {
       "thêm tài khoản",
       "them tai khoan",
       "add account",
       "thêm tài khoản khác",
       "them tai khoan khac",
       "add another account",
   }
   ```
2. **Inject Socket Remote ADB Có Điều Kiện (`machine_id >= 200`):**
   ```python
   def _build_fast_login_env(adb_path: str | None, machine_id: int | str | None = None) -> dict[str, str]:
       fast_env = os.environ.copy()
       fast_env.pop("PYTHONPATH", None)
       # ...
       if machine_id is not None and str(machine_id).isdigit() and int(machine_id) >= 200:
           fast_env["TAADAA_HOST_CONFIG"] = str(Path(r"D:\Taadaa\machine-config\admin.yaml"))
           fast_env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
       return fast_env
   ```
3. **Subprocess Reconcile:**
   Trong `_maybe_recover_missing_account_via_login`:
   ```python
   if _cluster == "admin":
       clean_env["TAADAA_HOST_CONFIG"] = str(Path(r"D:\Taadaa\machine-config") / f"{_cluster}.yaml")
       clean_env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
   ```

---

## 3. Canary Runner Isolation & S7 Extended Timeout
- **PIL / _imaging Conflict:** `canary_runner.py` khi spawn runner cần bọc môi trường sạch, ép dùng Python farm (`D:\Taadaa\python-envs\automation\Scripts\python.exe`) và lọc bỏ path `hermes-agent` khỏi `PYTHONPATH` để tránh vỡ binary C-extension của `PIL`.
- **S7 Old Hardware Timeout:** Các dòng Samsung S7 cũ (Android 8, Exynos 8890) khi vừa khởi động lại TikTok vừa xử lý login recovery có thể mất từ 8–15 phút. BẮT BUỘC đặt timeout trần của `canary_runner.py` tối thiểu **1800s (30 phút)** thay vì 360s hoặc 900s để tránh ngắt tiến trình giữa chừng.
