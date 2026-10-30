# Script Migration & Reconciliation Reference

## 1. Công cụ Snapshot
- **File:** `D:/Taadaa/tools/snapshot_excel_data.py`
- **Chức năng:** Sao lưu 8 file Excel Kibe/Admin vào `D:/Taadaa/snapshots/YYYYMMDD/` và tạo manifest mã băm SHA256.

## 2. Công cụ Đối soát Reconcile
- **File:** `D:/Taadaa/tools/reconcile_excel_sqlite.py`
- **Chức năng:** Đối chiếu 1-1 từng bản ghi tài khoản, hòm thư, máy giữa SQLite `D:/Taadaa/data/farm_master.db` và snapshot Excel.
- **Tiêu chí PASS:** Khớp 100% không có issue/mismatch nào.

## 3. Thứ tự các file bot đã cắt chuyển sang SQLite
1. `D:/Taadaa/tools/inspect_machine.py`:
   - Hàm `get_serial_for_machine`: Dùng `farm_db.get_machine_info(machine_id)["device_serial"]`.
2. `D:/Taadaa/Tiktok_Reg/hotmail_provider.py`:
   - Hàm `resolve_graph_credentials`: Truy vấn trước từ `farm_db.get_mailbox_credentials(email)` lấy `oauth_refresh_token` và `oauth_client_id`.
