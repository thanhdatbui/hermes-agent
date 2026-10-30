# Sổ Cái Tập Trung SQLite (farm_master.db) & Giao Diện Web Dashboard kibe:1905

## 1. Bối cảnh & Vấn đề giải quyết
- **Lỗi OneDrive Lock & Latency:** Việc các bot đọc trực tiếp các file Excel (`taikhoan_dat_v2_updated .xlsx`, `gmail_clean_v2.xlsx`, `PROXYgandienthoai.xlsx`) qua OneDrive thường xuyên bị dính `RecallOnDataAccess`, lỗi `Permission denied` hoặc đọc lệch index cột (`row[2]`, `row[5]`).
- **Phân mảnh 2 cụm:** Cụm Kibe (M1-M80) và Cụm Admin (M201-M280) bị chia tách trên 8 file Excel riêng lẻ.
- **Giải pháp chuyển dịch:** Gom toàn bộ dữ liệu về SQLite local `D:/Taadaa/data/farm_master.db` và đưa giao diện trực quan lên `kibe:1905` để người dùng quản lý, tra cứu trên điện thoại / PC.

## 2. Cấu Trúc Database (`farm_master.db`)
- `machines`: Lưu 160 máy (Kibe 1-80, Admin 201-280), proxy MikroTik/MobiProxy (`proxy_endpoint`), serial máy (`device_serial`).
- `mailboxes`: Lưu 1.517 hòm thư (cả Hotmail và Gmail), mật khẩu, 2FA, `oauth_refresh_token`, `oauth_client_id`, `oauth_status`.
- `tiktok_accounts`: Lưu 1.270 nick TikTok, mật khẩu, 2FA, email hòm thư liên kết (`email`), slot máy (`slot_no` 1-8), slot video (`video_slot` 1-640).
- `slot_assignments`: Sổ cái liên kết cứng giữa `machine_id` + `slot_no` và `tiktok_username`.

## 3. Quy Trình Di Trú Dữ Liệu (`migrate_excel_to_sqlite.py`)
- Script: `D:/Taadaa/tools/migrate_excel_to_sqlite.py`
- Kiểm thử đối soát không ghi đĩa:
  ```bash
  python D:/Taadaa/tools/migrate_excel_to_sqlite.py --dry-run
  ```
- Nạp chính thức và kiểm tra toàn vẹn ràng buộc (`foreign_key_check`, `integrity_check`):
  ```bash
  python D:/Taadaa/tools/migrate_excel_to_sqlite.py --apply
  ```
- **Lưu ý chuẩn hóa:** Header tiếng Việt trong Excel (`tài khoản gmail`, `pass mail`, `máy`) phải được chuẩn hóa bỏ dấu NFD và lowercase trước khi map alias (`canon_header`).

## 4. Tầng Truy Cập Dữ Liệu Cho Bot (`farm_db.py`)
Mọi script bot trong tương lai không được query bằng index số cột mà bắt buộc gọi qua module chuẩn `D:/Taadaa/tools/farm_db.py`:
```python
import farm_db

# Lấy thông tin tài khoản và vị trí máy
acc = farm_db.get_account("huynhthiloan112")
# -> {'username': 'huynhthiloan112', 'email': 'shackmierez11@hotmail.com', 'machine_id': 270, 'slot_no': 4, ...}

# Lấy đủ 8 nick trên 1 máy
m_accs = farm_db.get_accounts_by_machine(270)

# Lấy thông tin xác thực hòm thư & OAuth Token đọc OTP Graph API
mailbox = farm_db.get_mailbox_credentials("shackmierez11@hotmail.com")
# -> {'email': '...', 'password': '...', 'oauth_refresh_token': '...', 'oauth_client_id': '...', ...}

# Lấy proxy và serial của máy
info = farm_db.get_machine_info(270)
```

## 5. Tích Hợp Web Dashboard (`kibe:1905`)
- Tích hợp tab **"📑 Sổ Cái Farm (SQLite)"** vào `D:/Taadaa/tools/tiktok_dashboard.py` thông qua component `D:/Taadaa/tools/dashboard/ledger_component.py`.
- **API Endpoint:** `GET /api/ledger/data` trả về tổng quan 160 máy, 1.268 nick, 806 token OAuth và chi tiết từng slot.
- **Tính năng giao diện:**
  - Lọc theo cụm máy (Tất cả / Kibe 1-80 / Admin 201-280).
  - Tìm kiếm thời gian thực (instant filter) theo username `@...` hoặc email.
  - Bấm vào máy bất kỳ bung ra chi tiết 8 slot nick, email, proxy, trạng thái token.
  - Nút **"Xuất Excel"** cho phép người dùng tải ngay file CSV/Excel về máy.
- **Khởi động lại Dashboard:** Khi sửa code dashboard, chạy `python D:/Taadaa/tools/restart_tiktok_dashboard.py` để diệt các process cũ và chạy nền qua `wscript.exe start_tiktok_dashboard_hidden.vbs` (tránh xung đột port 1905).
