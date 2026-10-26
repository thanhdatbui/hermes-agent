# Điều Phối Dual Cluster (Kibe & Admin) & Fallback Automation-Core (26/10/2026)

## 1. Hiện Tượng & Nguyên Nhân
- Báo cáo 2FA ban đêm ghi nhận Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 22 | Lỗi 69.
- Nguyên nhân:
  1. Máy Admin (≥ 200) nằm trên host Admin điều khiển qua socket `192.168.110.119:5037` và nạp cấu hình `D:/Taadaa/machine-config/admin.yaml`.
  2. Sub-worker `run_capture_phase_b.py` trước đây mặc định khởi tạo `AdbClient()` về local socket, khiến toàn bộ 69 target bị trượt ngay từ khâu preflight (`DEVICE_NOT_CONNECTED`).
  3. Khi gọi python trực tiếp trên Admin-farm, môi trường thiếu fallback path `D:/Taadaa/automation-core/src` dẫn đến `ModuleNotFoundError: No module named 'automation_core'`.

## 2. Giải Pháp Kỹ Thuật Chuẩn Hóa
1. **Routing Endpoint Theo Machine Number:**
   ```python
   def resolve_cluster_adb_endpoint(machine: str):
       if int(machine) >= 200:
           return "192.168.110.119", 5037, r"D:\Taadaa\machine-config\admin.yaml"
       return None, None, r"D:\Taadaa\machine-config\kibe.yaml"
   ```
   Trước khi khởi tạo `AdbClient`: nạp `TAADAA_HOST_CONFIG` và truyền `host`, `port` tương ứng.

2. **Cấu Hình Đường Dẫn `automation-core` An Toàn:**
   ```python
   DEFAULT_AUTO_CORE_SRC = Path("D:/Taadaa/automation-core/src")

   def _configure_automation_core_path() -> Path | None:
       configured = os.environ.get("TAADAA_AUTOMATION_CORE_SRC", "").strip()
       candidates = ([Path(configured).expanduser()] if configured else []) + [DEFAULT_AUTO_CORE_SRC]
       for candidate in candidates:
           try:
               resolved = candidate.resolve()
           except (OSError, RuntimeError):
               continue
           if not resolved.is_dir():
               continue
           if "automation_core" in sys.modules or str(resolved) in sys.path:
               return resolved
           sys.path.append(str(resolved))
           return resolved
       return None
   ```
   - Hỗ trợ biến môi trường `TAADAA_AUTOMATION_CORE_SRC`.
   - Dùng `sys.path.append()` thay vì `insert(0)` để tránh ghi đè package đã cài đặt trong venv.

3. **Chống Rerun Bão Spam Ban Đêm:**
   - Trong `cron_night_tiktok_2fa_watchdog.py`: `already_ran_today()` chỉ kiểm tra `last_2fa_date == today_str`.
   - Một khi đã quét xong toàn bộ máy trong ca đêm (kể cả có `partial_failure`), ca đêm coi như đã chạy xong, không được phép rerun tự phát gây nghẽn máy giữa ngày.
