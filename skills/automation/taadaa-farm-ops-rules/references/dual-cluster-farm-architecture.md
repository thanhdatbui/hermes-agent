# Dual-Cluster Farm Architecture & Operations Reference

## 1. Dual-Cluster Concept & Topology
- **Cluster Definition**: Trong hạ tầng Taadaa Farm, một **Cluster** là một cụm gồm 80 điện thoại Samsung Galaxy S7 kết nối qua 4 Hub USB 20 cổng vào một máy tính chủ (Host PC).
- **Topology hiện tại (160 máy)**:
  * **Cụm 1: Kibe Local**:
    - Dải máy: `1 <= M <= 80` (M01 – M80).
    - Kết nối: Cáp USB cắm trực tiếp vào PC Kibe.
    - ADB Endpoint: Local ADB daemon (`localhost:5037`).
    - Dữ liệu cấu hình: `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` -> `Tik8.xlsx`, `taikhoan_run_safe.xlsx`.
    - Host Config: `D:\Taadaa\machine-config\kibe.yaml`.
    - Runtime: `D:\Taadaa\runtime\kibe`.
  * **Cụm 2: Admin Remote**:
    - Dải máy: `201 <= M <= 280` (M201 – M280).
    - Kết nối: Cáp USB cắm vào PC Admin, nối mạng LAN sang PC Kibe qua IP `192.168.110.119`.
    - ADB Endpoint: Remote ADB Server Socket `tcp:192.168.110.119:5037` (qua cờ `-H 192.168.110.119 -P 5037`).
    - Dữ liệu cấu hình: `D:\OneDrive\TaadaaData\admin\Tik1.xlsx` -> `Tik8.xlsx`, `taikhoan_run_safe.xlsx`.
    - Host Config: `D:\Taadaa\machine-config\admin.yaml`.
    - Runtime: `D:\Taadaa\runtime\admin`.

## 2. Kibe Master Orchestration Pattern (Thin Worker Model)
- Để triệt tiêu hoàn toàn race condition, desync mã nguồn và xung đột lock giữa 2 bot, hệ thống sử dụng mô hình **Kibe Master $\leftrightarrow$ Admin Thin Worker**:
  * PC Kibe đóng vai trò **Master Coordinator duy nhất**: Quản lý lịch cron, dispatch tác vụ, chạy watchdog và theo dõi trạng thái cho toàn bộ 160 máy.
  * Toàn bộ cron nuôi acc/tác vụ nền trên PC Admin được **PAUSE an toàn**.
  * Mọi lệnh can thiệp sang Admin được Kibe dispatch trực tiếp qua:
    1. Remote ADB Socket: `env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"`.
    2. Hoặc cờ ADB trực tiếp: `adb.exe -H 192.168.110.119 -P 5037 -s <serial> <command>`.
    3. Hoặc SSH điều khiển lệnh hệ điều hành: `ssh admin-farm "<command>"`.

## 3. Dual-Cluster Utility Pattern (Ví dụ: Clear-Cache, Provisioning, Watchdog)
Mọi script bảo trì/watchdog chạy trên Kibe cần tuân thủ khuôn mẫu cấu trúc 2 Cụm:

```python
CLUSTERS = [
    {
        "name": "kibe",
        "label": "FARM KIBE - MÁY 1-80",
        "workbook": r"D:\OneDrive\TaadaaData\kibe\Tik1.xlsx",
        "adb_socket": None,
        "adb_args": [],
        "host_config": r"D:\Taadaa\machine-config\kibe.yaml",
        "fleet_range": (1, 80),
    },
    {
        "name": "admin",
        "label": "FARM ADMIN - MÁY 201-280",
        "workbook": r"D:\OneDrive\TaadaaData\admin\Tik1.xlsx",
        "adb_socket": "tcp:192.168.110.119:5037",
        "adb_args": ["-H", "192.168.110.119", "-P", "5037"],
        "host_config": r"D:\Taadaa\machine-config\admin.yaml",
        "fleet_range": (201, 280),
    },
]
```

### Các quy tắc triển khai:
1. **Quét thiết bị online**:
   - Cluster Kibe: Gọi `adb.exe devices`.
   - Cluster Admin: Gọi `adb.exe -H 192.168.110.119 -P 5037 devices`.
2. **Nạp danh sách serial**: Đọc độc lập từ workbook tương ứng của từng cluster (`kibe\Tik1.xlsx` vs `admin\Tik1.xlsx`).
3. **Thực thi lệnh trên máy con**:
   - Truyền biến môi trường: `env["ADB_SERVER_SOCKET"] = cluster["adb_socket"]` và `env["TAADAA_HOST_CONFIG"] = cluster["host_config"]`.
   - Trong bước teardown bắt buộc (force-stop, HOME, portrait lock): gọi ADB kèm cờ `cluster["adb_args"]` để đảm bảo lệnh kết nối đúng máy chủ ADB của cluster đó.
4. **Báo cáo kết quả**:
   - Nhóm danh sách thành công và thất bại theo từng `cluster['label']` rõ ràng để người vận hành nắm bắt ngay máy thuộc cụm nào.

## 4. Triage Sự Cố Dual-Cluster Thường Gặp
1. **Lỗi Sập Cả Hub USB 20 Cổng (Bulk Device Offline)**:
   - Dấu hiệu: Toàn bộ 20 máy liên tiếp (ví dụ M261–M280) bị `device '<serial>' not found`.
   - Bản chất: Mất kết nối phần cứng (lỏng cáp uplink USB vào PC host hoặc sập adapter nguồn Hub) -> Không can thiệp phần mềm, phải cắm lại cáp hoặc bật lại nguồn Hub.
2. **Lỗi Lệch Timestamp Khi Ghép Batch Alert (Sibling Desync)**:
   - Khi Kibe và Admin xuất phát lệch giờ (do 1 bên phải chờ reg bù), `batch_aggregator` không ghép được thành `【TOÀN FARM】` do tên folder timestamp con khác nhau (`20260929-000252` vs `20260929-001707`).
   - Phải kiểm tra cả 2 thư mục live để xác nhận cả 2 cụm đều đã chạy xong.
