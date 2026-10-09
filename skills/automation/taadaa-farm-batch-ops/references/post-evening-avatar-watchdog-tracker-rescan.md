# Post Evening Avatar Watchdog & TikTok Tracker SQLite Rescan

## 1. Mục đích & Kiến trúc Watchdog
Watchdog `post_evening_avatar_watchdog.py` (nằm tại `AppData/Local/hermes/scripts/`, `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`, và OneDrive sync):
- Chạy tự động sau ca tối (20:15 - 23:45 HCMC) để upload Avatar cho các acc chưa có avatar.
- Im lặng khi kích hoạt batch, chỉ báo cáo 1 lần duy nhất khi hoàn tất 100% hoặc hết khung giờ (sau 23:30/23:45).

## 2. Truy vấn Source of Truth từ SQLite `tiktok_tracker.db` (Lọc theo Host)
Bảng dữ liệu:
- `farm_account_info m`: Chứa danh sách tài khoản theo máy (`may`), Tik (`tik`), `host_id`.
- `snapshots s`: Chứa lịch sử crawl profile (`username`, `status`, `has_avatar`, `id`, `timestamp`).

### Quy tắc phân lập Host (Tránh đè / trộn dải máy):
Khi query cần lọc chính xác theo `host_id` để tổng số máy mỗi Tik không vượt quá 80:
- **Admin**:
  ```sql
  WHERE m.tik = ? AND (m.host_id = 'admin' OR m.may >= 200)
  ```
- **Kibe**:
  ```sql
  WHERE m.tik = ? AND (m.host_id = 'kibe' OR m.host_id IS NULL OR m.host_id = '') AND m.may < 200
  ```

### Query chuẩn với CTE lấy snapshot mới nhất:
```sql
WITH Ranked AS (
    SELECT s.username, s.status, s.has_avatar,
           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
    FROM snapshots s
)
SELECT m.may, r.has_avatar, r.status
FROM farm_account_info m
LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
WHERE m.tik = ? AND {host_condition}
ORDER BY m.may
```
Nếu `has_avatar == 1` -> Đã có avatar. Ngược lại đưa vào danh sách cần upload.
Nếu SQLite lỗi hoặc trả rỗng, luôn có fallback đọc trực tiếp từ Excel workbook `Tik{tik}.xlsx`.

## 3. Tự động Rescan sau khi hoàn thành Batch
Sau khi PowerShell script `run_tiktok_upload_avatar.ps1` chạy xong một batch máy:
1. Trong `check_batch_status()`: Khi process PowerShell kết thúc, lấy `running.get("machines", [])` và gọi `rescan_completed_machines(machines)`.
2. Hàm `rescan_completed_machines()`:
   - Dùng Python: `D:\Taadaa\python-envs\automation\Scripts\python.exe`
   - Script: `D:\Taadaa\tools\tiktok_account_tracker.py`
   - Cờ: `--machines <m1,m2,...> --workers 10`
   - Giúp cập nhật snapshot `has_avatar = 1` vào SQLite ngay lập tức.
3. Trước khi gọi `report_final_summary()`: Kiểm tra nếu còn máy nào chạy trong phiên chưa được rescan thì rescan bổ sung để số liệu trong báo cáo Farm Alert là mới nhất.
