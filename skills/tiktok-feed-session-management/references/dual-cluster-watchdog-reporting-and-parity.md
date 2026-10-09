# Dual-Cluster Watchdog Reporting & 3-Way Parity (Farm Kibe & Admin)

## 1. Kiến Trúc Dual-Cluster

Farm TikTok mở rộng thành 2 cụm máy độc lập chạy song song:
- **Farm Kibe (Máy 1 - 80)**:
  - `runtime_root`: `D:\Taadaa\runtime\kibe`
  - `live_root`: `D:\Taadaa\runtime\kibe\live`
  - `account_workbook`: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`
  - Dải máy: `1` đến `80`
- **Farm Admin (Máy 201 - 280)**:
  - `runtime_root`: `D:\Taadaa\runtime\admin`
  - `live_root`: `D:\Taadaa\runtime\admin\live`
  - `account_workbook`: `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx`
  - Dải máy: `201` đến `280`

Cấu hình khai báo trong `feed_session_watchdog.py`:
```python
CLUSTERS = [
    {
        "name": "kibe",
        "label": "FARM KIBE - MÁY 1-80",
        "runtime_root": r"D:\Taadaa\runtime\kibe",
        "live_root": r"D:\Taadaa\runtime\kibe\live",
        "account_workbook": r"D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx",
        "fleet_min": 1,
        "fleet_max": 80,
    },
    {
        "name": "admin",
        "label": "FARM ADMIN - MÁY 201-280",
        "runtime_root": r"D:\Taadaa\runtime\admin",
        "live_root": r"D:\Taadaa\runtime\admin\live",
        "account_workbook": r"D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx",
        "fleet_min": 201,
        "fleet_max": 280,
    },
]
```

## 2. Helper Đọc Expected Machines Từ Workbook `taikhoan_run_safe.xlsx`

- Sheet `Accounts` chứa 80 máy, mỗi máy có 8 dòng tương ứng với 8 slot (Row 1 đến Row 8).
- Cột A (index 0) = `May`, Cột C (index 2) = `ID`.
- Với mỗi ca nuôi đang chạy ở `row_num`, slot tương ứng là `slot_idx = int(row_num) - 1`.
- Nếu slot có ID hợp lệ (không rỗng, khác `None`), máy đó nằm trong `expected_machines`.
- Fallback an toàn: Nếu workbook lỗi, bị khóa file (I/O lock) hoặc không tồn tại, trả về toàn bộ fleet máy `fleet_min..fleet_max`.

```python
def get_expected_machines_for_cluster(cluster: dict, row_num: Any) -> set:
    fleet_machines = {str(i) for i in range(cluster["fleet_min"], cluster["fleet_max"] + 1)}
    wb_path = cluster.get("account_workbook")
    if not wb_path or not os.path.exists(wb_path):
        return fleet_machines
    try:
        import openpyxl
        wb = openpyxl.load_workbook(wb_path, data_only=True, read_only=True)
        sheet = wb.active
        m_slots = defaultdict(list)
        for r in sheet.iter_rows(values_only=True):
            if not r or r[0] is None:
                continue
            m_str = str(r[0]).strip()
            if not m_str.isdigit():
                continue
            uid = ""
            if len(r) > 2 and r[2] is not None:
                uid = str(r[2]).strip()
                if uid.lower() == "none":
                    uid = ""
            m_slots[m_str].append(uid)
        wb.close()

        slot_idx = int(row_num) - 1
        expected = set()
        for m in fleet_machines:
            slots = m_slots.get(m, [])
            if 0 <= slot_idx < len(slots) and slots[slot_idx]:
                expected.add(m)
        return expected if expected else fleet_machines
    except Exception as e:
        logger.warning("Error reading workbook %s: %s", wb_path, e)
        return fleet_machines
```

## 3. Format Báo Cáo Telegram Gộp

Báo cáo phiên kết hợp header chung và các khối cluster đang hoạt động:
```text
📊 [TIKTOK NUÔI ACC] Ca 1 - Phiên 1/2 (Sáng) hoàn tất (Row 1)

🏢 【FARM KIBE - MÁY 1-80】
• Tổng máy xử lý: 80 máy
• Lướt Feed:
  + Success (72): 1, 2, 3...
  + Fail (2): M15, M30
  + Trống slot/chưa có nick (6): 5, 8, 12...
  + Thả tim: ...
  + Đọc comment: ...
• Chế độ Dưỡng Sinh (nếu có): ...
• Follow chéo: ...
• Đăng Video: ...

🏢 【FARM ADMIN - MÁY 201-280】
• Tổng máy xử lý: 80 máy
• Lướt Feed:
  ...
```

## 4. Quản Lý Trạng Thái Session & 3-Way Parity

- **Graceful Cluster Absence:** Trong thực tế, một trong hai cluster (ví dụ Admin) có thể chưa khởi tạo thư mục `live` (`os.path.exists(cluster["live_root"]) == False`). Vòng lặp `main()` và bước gom `dates_to_check` BẮT BUỘC kiểm tra sự tồn tại của thư mục trước khi `os.listdir`, tránh crash `FileNotFoundError`.
- **State File:** `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json` (dùng chung cho việc claim session key `{date}_ca{ca}_phien{phien}`).
- **3-Way Parity Invariant:** Mọi chỉnh sửa watchdog BẮT BUỘC phản ánh đồng nhất trên cả 3 file:
  1. `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`
  2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\feed_session_watchdog.py`
  3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\feed_session_watchdog.py`
- Kiểm tra cú pháp sau khi ghi: `python -m py_compile <path>` cho cả 3 đường dẫn.
