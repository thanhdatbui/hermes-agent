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
- **Quy Chuẩn Tam Giác Đồng Bộ 3 Tầng Khi Gán/Đổi Proxy (Tri-Sync Invariant):** Khi cập nhật hoặc điều chuyển proxy gán cho thiết bị (chuyển cụm R3G 202xx / MikroTik 100xx / MobiProxy), BẮT BUỘC cập nhật đồng thời đủ 3 tầng, cấm làm thiếu:
  1. `farm_master.db` (bảng `machines`, cột `proxy_endpoint`).
  2. File Excel nguồn `PROXYgandienthoai.xlsx` (kèm đẩy qua SSH chunking sang `admin-farm` nếu thuộc cụm Admin).
  3. Cài đặt ADB trên điện thoại S7 thật qua `set_proxy_farm_admin_adb.py` (`settings put global http_proxy 192.168.110.2:<port>`).
  Tuyệt đối cấm chỉ sửa một hoặc hai bên làm lệch dữ liệu giữa Sổ Cái tập trung, file Excel SSOT và máy thật.
- **Giải mã Tuổi Nick O(1) từ UID & Benchmark Follow:** Tra cứu tuổi nick chính xác từ Snowflake UID (`uid >> 32`), đối soát số liệu khả năng follow thực tế (ngưỡng 3 tháng) và kiến trúc ngâm Dual-App TikTok Lite via Google SSO (tránh bẫy Instant-Ban của Hotmail) tại `references/tiktok-uid-snowflake-epoch-and-account-age-benchmarks.md`.
- **Cập nhật & Đồng bộ Thay thế Gmail DIE:** Đã hoàn tất thay thế Hotmail có OAuth Microsoft Graph API cho 18 tài khoản cựu binh dính Gmail DIE (được cập nhật song song SQLite SSOT và Master Excel). Toàn farm còn 23 tài khoản đang chờ cuốn chiếu ngoài ca nuôi acc. Tra cứu quy trình thay thế, cơ chế lock an toàn và cạm bẫy xử lý tại `references/hotmail-replacement-for-die-gmail.md` và `references/migration_reconciliation.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
