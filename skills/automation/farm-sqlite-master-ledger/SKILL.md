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

## 3. Quy Chuẩn Hiển Thị Trên Web Dashboard (`http://kibe:1905`)
File hiển thị: `D:/Taadaa/tools/dashboard/ledger_component.py` (tích hợp vào `tiktok_dashboard.py`).
- **Phân tách Danh Mục Lớn (Top-level Category Navigation):**
  - Sổ Cái Farm (SQLite) BẮT BUỘC nằm ở thanh tab danh mục lớn (`.main-category-tabs`) độc lập ở đầu trang (`[📊 Giám Sát TikTok]` vs `[📓 Sổ Cái Farm (SQLite)]`).
  - CẤM TUYỆT ĐỐI nhồi nút Sổ Cái thành một nút lọc phụ bé trong hàng `.filter-buttons` của bảng nick TikTok.
  - Khi người dùng chọn tab `📓 Sổ Cái Farm (SQLite)`, hệ thống BẮT BUỘC ẩn toàn bộ khu vực KPI và thanh toolbar lọc của TikTok (`.kpi-grid`, `.toolbar`, `#row-cluster`, `#row-tik-filter`) để giao diện hiển thị thẳng thống kê Sổ Cái, thanh tìm kiếm/lọc cụm và lưới máy, tránh gây nhiễu và trùng lặp ô tìm kiếm.
- **Kỷ luật Mã Nguồn JS/F-string:** Toàn bộ JavaScript điều khiển giao diện Sổ Cái (`window.switchMainCategory`, `window.initLedger`, `window.setView`) BẮT BUỘC đóng gói trong `LEDGER_VIEW_JS` dưới dạng raw-string (`r"""..."""`) tại `ledger_component.py`. TUYỆT ĐỐI CẤM viết JS trực tiếp vào f-string `render_html_page` trong `tiktok_dashboard.py` để tránh lỗi cú pháp dấu ngoặc nhọn `{}` (`SyntaxError: f-string: invalid syntax`).
- **Quy tắc hiển thị 2FA:** BẮT BUỘC in trực tiếp chuỗi Secret Key dạng thẻ nổi bật `🔑 2FA: <SECRET_KEY>` để người dùng chạm vào là copy được ngay vào app Authenticator. Tuyệt đối CẤM chỉ hiển thị nhãn chữ `2FA` chung chung hoặc ẩn đi.
- **Quy tắc hiển thị Mật khẩu:** In rõ ràng `🔑 Pass: <PASSWORD>` (TikTok) và `✉️ Pass Mail: <MAIL_PASSWORD>`.
- **Phân loại Badge trực quan:**
  - `🔵 Gmail App`: Hòm thư Gmail đăng nhập qua ứng dụng.
  - `🟢 OAuth Live`: Hotmail có token OAuth Graph API còn sống/sẵn sàng.
  - `🟡 Pass Outlook`: Hotmail dùng mật khẩu đăng nhập trực tiếp.
- **Nút Xuất Excel:** Bắt buộc có nút xuất CSV (UTF-8 BOM) để người dùng tải về mở bằng Microsoft Excel quen thuộc.
- **Khởi động / Restart:** Chạy `python D:/Taadaa/tools/restart_tiktok_dashboard.py`.
- **Tài liệu tham khảo chi tiết:** Xem `references/migration_reconciliation.md` về quy trình snapshot, audit hash SHA256 và script reconcile đối soát 1-1.

## 4. Tầng Truy Xuất Data Access Layer (`farm_db.py`)
Mọi script bot trong farm (`Tiktok_Reg`, `social_reg_v1.py`, `tiktok_login_v1.py`, `inspect_machine.py`) khi đọc thông tin máy / nick / hòm thư bắt buộc gọi qua `D:/Taadaa/tools/farm_db.py`:
```python
import farm_db

account = farm_db.get_account("huynhthiloan112")
machine_accounts = farm_db.get_accounts_by_machine(270)
mailbox = farm_db.get_mailbox_credentials("shackmierez11@hotmail.com")
machine_info = farm_db.get_machine_info(270)
```
- **Kỷ luật DAL:** Dùng truy cập có tên trường qua `sqlite3.Row` (`row['username']`), CẤM TUYỆT ĐỐI truy xuất theo chỉ số cột kiểu Excel (`row[2]`, `row[5]`).

## 5. Quy Trình Cắt Chuyển Script & Đối Soát Reconcile An Toàn (Anti-Data-Loss)
- **Snapshot trước khi cắt chuyển:** BẮT BUỘC sao lưu snapshot toàn bộ các file Excel nguồn sang `D:/Taadaa/snapshots/YYYYMMDD/` và tính mã SHA256 kiểm chứng trước khi chuyển đổi (`python D:/Taadaa/tools/snapshot_excel_data.py`).
- **Thẩm định Đối soát 100% (Reconciliation Check):**
  Chạy đối soát tự động `python D:/Taadaa/tools/reconcile_excel_sqlite.py` để xác nhận:
  - `account`: 1.270 / 1.270 tài khoản khớp 100% (username, password, 2fa, email).
  - `mailbox`: 1.455 / 1.455 hòm thư khớp 100% (password, token, client_id).
  - `machine`: 160 / 160 máy khớp 100% (proxy_endpoint, device_serial).
- **Thứ tự cắt chuyển script bot:**
  1. `inspect_machine.py`: Thay thế hàm đọc Excel serial bằng `farm_db.get_machine_info(machine_id)["device_serial"]`.
  2. `hotmail_provider.py`: Bổ sung lookup qua `farm_db.get_mailbox_credentials(email)` lên đầu hàm `resolve_graph_credentials` trước khi fallback sang Excel.
  3. `multi_machine_feed_session.py`: Trong `_is_ip_breaker_tripped`, ưu tiên lấy proxy từ `farm_db.get_machine_info(m)["proxy_endpoint"]` trước khi mở `openpyxl` từ `PROXYgandienthoai.xlsx`.
  4. `tiktok_login_v1.py`: Trong `load_tracking_accounts_for_stt(stt)`, ưu tiên load danh sách 8 slot từ `farm_db.get_accounts_by_machine(stt)` kèm `device_serial` và pass mail từ `farm_db.get_mailbox_credentials` trước khi fallback sang Excel `taikhoan_dat_v2_updated .xlsx`.
  5. Chạy focused tests offline (ví dụ: `pytest tests/test_hotmail_provider.py`, `pytest tests/test_tiktok_login_v1.py`) xác nhận PASS 100% trước khi commit.

## 6. Đồng Bộ Proxy Endpoint Khi Điều Chỉnh Mạng Farm (Full-Spectrum Standardization)
Khi thực hiện rebalance/offload proxy cho máy (ví dụ chuyển dàn máy sang proxy mới `:202xx` hoặc dải proxy vệ tinh):
- **BẮT BUỘC** cập nhật đồng thời trường `proxy_endpoint` trong bảng `machines` của `farm_master.db`:
  ```python
  import sqlite3
  conn = sqlite3.connect("D:/Taadaa/data/farm_master.db")
  conn.execute("UPDATE machines SET proxy_endpoint = ? WHERE machine_id = ?", (new_proxy, str(m)))
  conn.commit()
  ```
- **Ý nghĩa:** Tránh lệch pha giữa file Excel SSOT (`PROXYgandienthoai.xlsx`) và database trung tâm, đảm bảo Web Ledger (`kibe:1905`) hiển thị đúng thời gian thực và các bot runner truy xuất qua DAL `farm_db.get_machine_info(m)['proxy_endpoint']` lấy đúng địa chỉ proxy mới nhất.
