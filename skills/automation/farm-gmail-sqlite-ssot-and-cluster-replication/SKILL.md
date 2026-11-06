---
name: farm-gmail-sqlite-ssot-and-cluster-replication
description: "Quy chuẩn chuyển đổi chuỗi Gmail sang SQLite farm_master.db SSOT, đồng bộ 2 chiều LAN và chốt chặn chống đọc log cũ."
version: 1.0.0
---
# Farm Gmail SQLite SSOT & Cluster Replication Discipline

## 1. Trọng Tâm & Bối Cảnh
- **Thay thế Excel bằng SQLite:** Diệt trừ toàn bộ các lỗi lock file OneDrive (`gmail_clean_v2.xlsx`, `master_gmail_manager.xlsx`) bằng cách chuyển chuỗi nghiệp vụ Gmail về bảng `mailboxes` trong `D:/Taadaa/data/farm_master.db`.
- **Chốt chặn chống đọc lén log cũ (`Anti-Stale Remote Telemetry`):** Khi cluster con (Admin Farm) gặp sự cố không chạy, watchdog tổng hợp tuyệt đối không được nhặt file log cũ của ngày hôm trước để báo cáo ma.

## 2. Quy Chuẩn Kỹ Thuật

### A. Chốt chặn truy vấn log từ xa qua SSH / PowerShell
Mọi lệnh PowerShell đọc file summary/log từ xa bắt buộc phải lọc mốc thời gian của ca hiện tại (`min_mtime`):
```powershell
Get-ChildItem -Path 'D:\CodexRuntime\...\logs_parallel_*\summary.json' -ErrorAction SilentlyContinue |
Where-Object { $_.LastWriteTime -ge (Get-Date '<min_date_str>') } |
Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Raw -Encoding UTF8
```
Nếu Admin không chạy trong ca hiện tại $\rightarrow$ Truy vấn trả về rỗng $\rightarrow$ Watchdog ghi nhận Admin không có sản lượng, tuyệt đối không đắp số liệu cũ vào.

### B. Chuỗi nghiệp vụ Gmail thuần SQLite SSOT
1. **Khâu Reg Gmail (`merge_success_results.py`):**
   - Khi tạo tài khoản mới thành công, bắt buộc gọi hàm `sync_success_items_to_sqlite()` để `INSERT OR REPLACE INTO mailboxes` thẳng vào SQLite `farm_master.db`.
2. **Khâu Replicate 2 chiều Kibe & Admin (`sync_2fa_to_admin.py`):**
   - Định kỳ hàng giờ, kịch bản tự động kéo các mailboxes `owner='admin'` về Kibe và đẩy các mailboxes `owner='kibe'` sang Admin qua lệnh query SQLite nội bộ mạng LAN.
   - Triệt tiêu sự phụ thuộc vào độ trễ đồng bộ OneDrive.
3. **Khâu Bật 2FA Gmail (`post_morning_gmail_2fa_watchdog.py`):**
   - Hàm `get_gpm_candidates()` ưu tiên nạp credentials trực tiếp từ SQLite:
     ```python
     FARM_MASTER_DB = Path(os.environ.get('FARM_MASTER_DB', r'D:\Taadaa\data\farm_master.db'))
     # SELECT lower(email), password, twofa_secret FROM mailboxes
     ```
   - Chỉ fallback về Excel khi CSDL SQLite không tồn tại.
4. **Khâu Xuất Danh Sách Tổng (`sync_gmail_clean_v2_to_tong.py`):**
   - Đọc danh sách email live từ SQLite `mailboxes` để nạp vào `gmail_live_tong.txt`.
