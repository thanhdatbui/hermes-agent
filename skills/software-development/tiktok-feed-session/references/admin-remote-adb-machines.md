# Quy tắc Máy Admin (Machine >= 200) & Remote ADB Host

## Kiến trúc Điều Khiển Máy Admin
- Các máy số hiệu `machine >= 200` (ví dụ: 201, 202, ...) là máy Admin farm.
- Remote ADB host cho các máy này:
  - **Host:** `192.168.110.119`
  - **Port:** `5037`

## Cấu Hình Trong Child Context
- Khi điều phối multi-machine session (`multi_machine_feed_session.py`), hàm `_build_child_context` phải khởi tạo `AdbClient` với remote host/port tương ứng:
  ```python
  is_admin_remote = account.machine >= 200
  child_adb = AdbClient(
      adb_path=str(child_config.get("adb_path", "adb")),
      serial=account.serial,
      default_timeout=float(_cfg_subdict(child_config, "timeouts").get("adb_seconds", 15)),
      host="192.168.110.119" if is_admin_remote else None,
      port=5037 if is_admin_remote else None,
  )
  ```
- Các máy farm thông thường (`machine < 200`):
  - `host=None`, `port=None` (sử dụng daemon ADB cục bộ).

## Kiến trúc Cron Multi-Cluster Runner (`tiktok_runner.py`)
- Cron wrapper `tiktok_runner.py` quản lý danh sách `CLUSTERS`:
  - `kibe`: `host_config: D:\Taadaa\machine-config\kibe.yaml`, `adb_server_socket: None`
  - `admin`: `host_config: D:\Taadaa\machine-config\admin.yaml`, `adb_server_socket: tcp:192.168.110.119:5037`
- Khi spawn session con (`_spawn_feed_session`), BẮT BUỘC inject vào `child_env`:
  - `TAADAA_HOST_CONFIG = host_config` (để vượt qua `taadaa_host.py` host guard range [200, 999]).
  - `ADB_SERVER_SOCKET = adb_server_socket` (để mọi sub-process `adb.exe`, Xiaowei ADB hoặc script Python CLI downstream tự động trỏ đến daemon ADB Remote LAN thay vì local daemon).
- KHÔNG dùng heuristic kiểm tra chuỗi `admin` trong path, phải cấu hình tường minh thuộc tính trong dict cluster và log telemetry `[host=... socket=...]` khi spawn.

## Lưu Ý Thao Tác & Codebase
- CẤM chạy `grep -rn` hoặc quét đĩa diện rộng trong repo `tiktok-luot nuoi acc/python_runner` vì các thư mục `runs/`, `artifacts/` chứa lượng lớn dữ liệu gây treo lệnh (timeout 180s).
