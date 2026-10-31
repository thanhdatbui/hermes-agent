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

## 4. Hiện Tượng Khuyết Email Do Lịch Sử DIE Gmail & Đối Soát GPM
- **Nguyên nhân gốc:** Khi Gmail cũ bị Google khóa/die, người vận hành trước đây đã đưa vào `master_gmail_manager.xlsx` (sheet `Gmail_DIE_Archive`) và xóa trắng ô `GMAIL` trong `taikhoan_dat_v2_updated .xlsx`. Khi nạp vào `farm_master.db`, các tài khoản này (`@doanmai0701` M25, `@lieuhoan03` M02, `@tanglam024` M42) có `email = NULL` nhưng vẫn có đủ Password TikTok và 2FA Secret.
- **Cách tra cứu vết:** 
  - Mở `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx` lọc theo `Số Máy Farm` để lấy lại địa chỉ Gmail cũ đã lưu trữ.
  - Kiểm tra trạng thái session web GPM qua `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/profile_data.db` và đọc cookie an toàn read-only (`file:<path>/Cookies?mode=ro`, kiểm tra `SID/SSID` cho Google, `AUTH` cho Microsoft).
- **Quy tắc xử lý:** Tuyệt đối không xóa nick TikTok đang chạy bình thường; bổ sung email thay thế từ pool Hotmail OAuth Graph API hoặc cập nhật ghi chú `[DIE]` vào database.

## 5. Quy Trình Cấp Hotmail Mới & Cơ Chế Gán Mail TikTok Khi Mail Cũ Đã DIE
- **Trích xuất Hotmail sạch có sẵn OAuth Graph API:**
  - Truy vấn pool `mailboxes` chưa gán:
    ```sql
    SELECT mb.email, mb.password, mb.oauth_refresh_token, mb.oauth_client_id
    FROM mailboxes mb
    LEFT JOIN tiktok_accounts ta ON lower(mb.email) = lower(ta.email)
    WHERE ta.username IS NULL AND mb.provider = 'hotmail' AND mb.oauth_refresh_token != ''
    LIMIT N;
    ```
  - Cập nhật trường `email` trong `tiktok_accounts` và đồng bộ Master DAT (`taikhoan_dat_v2_updated .xlsx`).
- **Cơ chế và giới hạn khi vào TikTok gán Hotmail mới:**
  - **Trường hợp A (TikTok chưa từng liên kết email):** Vào *Cài đặt và quyền riêng tư* -> *Tài khoản* -> *Thông tin người dùng* -> *Thêm email* -> Điền Hotmail mới -> TikTok gửi OTP về Hotmail -> Gọi Graph API bóc OTP 6 số điền vào -> Liên kết thành công 100%.
  - **Trường hợp B (TikTok đã liên kết Gmail cũ nhưng Gmail đã DIE):** Khi bấm đổi email, TikTok BẮT BUỘC gửi mã OTP về Gmail cũ để xác minh chính chủ trước. Do Gmail cũ đã die nên không thể đọc OTP bước này -> Không thể đổi mail trực tiếp trong app TikTok.
  - **Bảo vệ tài khoản farm:** Nick TikTok vẫn an toàn 100% vì app Android đang chạy native session; đăng nhập lại trên máy mới thực hiện bằng **Username + Password TikTok + 2FA TOTP offline (`pyotp`)** mà không cần tới email.


