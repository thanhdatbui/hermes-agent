---
name: farm-sqlite-master-ledger
description: "Use when managing farm SQLite database, DAL, or web ledger."
---
# Farm SQLite Master Ledger & Web Dashboard Operations

## 1. Trọng Tâm & Bối Cảnh
- **Thay thế Excel bằng SQLite:** Chuyển đổi toàn bộ các file Excel phân mảnh trong OneDrive (`taikhoan_dat_v2_updated .xlsx`, `gmail_clean_v2.xlsx`, `taikhoan_run_safe.xlsx`, `PROXYgandienthoai.xlsx`) sang cơ sở dữ liệu SQLite tập trung đặt tại ổ đĩa local: `D:/Taadaa/data/farm_master.db`.
- **Mục tiêu:** Diệt trừ 100% lỗi lock file OneDrive (`RecallOnDataAccess`, `PermissionError`), đồng thời cung cấp giao diện Web trực quan tại `http://kibe:1905` cho người dùng tra cứu nhanh, quản lý và copy 2FA / Mật khẩu.

## 2. Cấu Trúc Cơ Sở Dữ Liệu (`farm_master.db`)
- `machines`: `machine_id` (PK, 1-80 Kibe, 201-280 Admin), `owner`, `proxy_endpoint`, `device_serial`, `source`.
- `tiktok_accounts`: `username` (PK), `password`, `twofa_secret`, `email`, `machine_id`, `video_slot`, `owner`.
- `mailboxes`: `email` (PK), `password`, `twofa_secret`, `oauth_refresh_token`, `oauth_client_id`, `oauth_status`, `provider`.
- `slot_assignments`: `machine_id`, `slot_no` (1-8), `tiktok_username`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
