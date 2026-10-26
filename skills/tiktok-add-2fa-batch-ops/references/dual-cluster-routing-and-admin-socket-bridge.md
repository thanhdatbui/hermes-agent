# Dual Cluster Routing & Admin Socket Bridge (201-280)

## 1. Hiện Tượng Thực Tế
- Khi chạy batch 2FA TikTok toàn farm ban đêm, toàn bộ các máy thuộc Cụm Admin (201-280) bị đánh fail 100% (69/69 máy lỗi) ngay từ bước preflight:
  `{"status": "blocked", "reason": "DEVICE_NOT_CONNECTED"}`
- Trong khi đó phần cứng và ADB của cụm Admin (`192.168.110.119:5037`) vẫn online bình thường.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch ADB Socket:**
   - Trong `run_capture_phase_b.py`, `AdbClient()` mặc định kết nối tới `127.0.0.1:5037` (Kibe Local). Vì các serial của máy Admin không tồn tại trên daemon ADB local của Kibe, kiểm tra `serial not in adb.list_devices()` lập tức trả về `DEVICE_NOT_CONNECTED`.
2. **Lệch Host Config & Proxy Mapping:**
   - `automation_core.preflight.resolve_proxy_mapping_path()` dựa vào biến môi trường `TAADAA_HOST_CONFIG`. Nếu không set rõ `admin.yaml`, runner sẽ đọc nhầm file mapping của Kibe và làm fail VPN gate.
3. **Thiếu Fallback Path trên Remote Host:**
   - Khi chạy qua SSH trên Admin-farm bằng Python hệ thống, nếu `PYTHONPATH` chưa bao gồm `D:\Taadaa\automation-core\src` thì tiến trình văng ngay `ModuleNotFoundError: No module named 'automation_core'`.

## 3. Quy Tắc & Giải Pháp Bắt Buộc

1. **Endpoint Resolution Helper:**
   Trong `run_capture_phase_b.py`:
   ```python
   def resolve_cluster_adb_endpoint(machine: str):
       if int(machine) >= 200:
           return "192.168.110.119", 5037, r"D:\Taadaa\machine-config\admin.yaml"
       return None, None, r"D:\Taadaa\machine-config\kibe.yaml"
   ```
2. **Thiết lập Host Config & truyền Host/Port vào AdbClient:**
   ```python
   host, port, host_cfg = resolve_cluster_adb_endpoint(cfg.machine)
   os.environ.setdefault("TAADAA_HOST_CONFIG", host_cfg)
   adb = AdbClient(
       adb_path=resolve_adb_path(cfg.adb_path),
       serial=cfg.serial,
       host=host,
       port=port,
   )
   ```
3. **Nạp `TAADAA_HOST_CONFIG` trong Subprocess Environment của Batch Runner:**
   Trong `run_batch_live_2fa.py`:
   ```python
   worker_env["TAADAA_HOST_CONFIG"] = (
       r"D:\Taadaa\machine-config\admin.yaml"
       if int(target.machine) >= 200
       else r"D:\Taadaa\machine-config\kibe.yaml"
   )
   ```
4. **Fallback sys.path cho `automation-core`:**
   Tại đầu mọi script runner standalone:
   ```python
   AUTO_CORE_SRC = Path(r"D:\Taadaa\automation-core\src")
   if AUTO_CORE_SRC.is_dir() and str(AUTO_CORE_SRC) not in sys.path:
       sys.path.insert(0, str(AUTO_CORE_SRC))
   ```
