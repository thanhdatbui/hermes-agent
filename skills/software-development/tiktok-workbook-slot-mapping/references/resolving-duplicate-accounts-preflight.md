# Quy trình điều tra & khắc phục triệt để lỗi Duplicate Account (Preflight Validator)

## 1. Mục đích
Hướng dẫn cách xử lý dứt điểm khi `excel_preflight_validator.py` báo lỗi Rule 2 (Trùng lặp tài khoản giữa các slot / giữa các file `Tik*.xlsx` và `taikhoan_dat_v2_updated .xlsx`).

## 2. Lệnh kiểm tra xác thực (Invariant Gate)
```bash
python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error
```

## 3. Các bước điều tra nguồn gốc tài khoản
Khi phát hiện lỗi trùng lặp (ví dụ nick X xuất hiện ở cả slot A và slot B của cùng một máy hoặc khác máy):

1. **Xác định tọa độ slot & folder**:
   - Công thức chuẩn: `Folder Video = (máy - 1) * 8 + slot`.
   - Ví dụ: Máy 10 slot 3 -> Folder 75; Máy 62 slot 3 -> Folder 491.

2. **Kiểm tra thông tin chi tiết trong `taikhoan_dat_v2_updated .xlsx`**:
   - Mở Sheet `'Tài Khoản'`.
   - Đối chiếu dòng tương ứng: kiểm tra Cột ID, PASS, GMAIL, PASS MAIL, NGÀY TẠO.
   - Đánh giá xem slot bị trùng có thông tin email riêng hay không.

3. **Tra cứu CSDL SQLite xác định máy chính chủ**:
   - Chạy truy vấn O(1) trên `D:/Taadaa/data/tiktok_tracker.db`:
     `SELECT may, tik, username FROM farm_account_info WHERE username = '<id>';`
   - Xác định chính xác máy nào là máy sở hữu thực sự của nick trên Farm theo CSDL để tránh xóa nhầm máy chính chủ.

4. **Tra cứu lịch sử backup**:
   - Liệt kê các bản backup gần nhất tại `D:\OneDrive\TaadaaData\kibe\workbook-backups\` hoặc `taikhoan_dat_v2_updated .xlsx.bak*`.
   - Tìm kiếm theo email hoặc số máy để tìm ra username gốc đã từng tồn tại trước khi bị copy đè (ví dụ trường hợp `tranvantrang9810` gán cho mail `thachnha1103199810@gmail.com` ở Máy 10).

5. **Xác định phương án sửa**:
   - **Trường hợp khôi phục nick gốc**: Nếu tìm được username thực sự của email đó, cập nhật ID về username đúng.
   - **Trường hợp nick ký sinh / tàn dư máy cũ**: Set ID về `None` trên máy cũ để giải phóng duplicate và chỉ giữ nick trên máy chính chủ.

## 4. Quy tắc chỉnh sửa an toàn & Đồng bộ tam phương (3-Way Synchronization)
1. **Bắt buộc Backup trước khi ghi đè**:
   - Tạo file `.bak_before_clear_parasite_{YYYYMMDD_HHMMSS}.xlsx` cho cả 3 file:
     * `taikhoan_dat_v2_updated .xlsx`
     * `Tik<Slot>.xlsx`
     * `taikhoan_run_safe.xlsx`
2. **Đồng bộ tam phương bắt buộc (3-Way Synchronization)**:
   Khi xóa tàn dư nick trùng lặp trên máy cũ, bắt buộc cập nhật đồng bộ đủ 3 file để tránh sót vi phạm Rule 5:
   - **File 1 — Master Tracking** (`taikhoan_dat_v2_updated .xlsx`, Sheet `'Tài Khoản'`):
     + Set `None` cho các cột: Cột 3 (ID), Cột 4 (PASS), Cột 5 (2FA), Cột 6 (GMAIL), Cột 7 (PASS MAIL), Cột 8 (DOB), Cột 9 (NGÀY TẠO), Cột 11 (placeholder), Cột 12 (PASS CHATGPT).
     + Giữ nguyên tuyệt đối: Cột 1 (Máy), Cột 2 (Folder Video), Cột 10 (Device ID).
   - **File 2 — Tik Slot Workbook** (`Tik<Slot>.xlsx`, Active Sheet):
     + Cột 3 (ID): set về `None`.
     + Cột 8 (`Video Đã Đăng`): reset về `0`.
     + Cột 9 (`Kiểm Tra Dữ Liệu`): set về `'MISSING_ID'`.
     + Giữ nguyên tuyệt đối: Cột 1 (Máy), Cột 2 (Device ID), Cột 4 (Folder Video), Cột 5 (Video Gốc), Cột 6 (Keyword Video), Cột 7 (Hashtag Pool).
   - **File 3 — Safe Workbook** (`taikhoan_run_safe.xlsx`, Sheet `'Accounts'`):
     + Cột 3 (ID): set về `None`.
     + Cột 4 (`Video Đã Đăng`): reset về `0`.
     + Cột 5 (`Ngày Tạo`): set về `None`.
     + Giữ nguyên tuyệt đối: Cột 1 (May), Cột 2 (Device ID).
3. **Nghiệm thu 2 tầng (Gate Closure & Cron Recovery)**:
   - **Tầng 1 (Invariant Validation)**:
     `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error`
     Bắt buộc đạt `PASS 100% - Toàn bộ Invariant Rules hợp lệ (0 cảnh báo)`.
   - **Tầng 2 (Cron Sync Recovery)**:
     Chạy kiểm chứng launcher:
     `python "C:/Users/Kibe/AppData/Local/hermes/scripts/taikhoan_sync_cron_launcher.py"`
     Hoặc kích hoạt `cronjob action='run' job_id='95f8cd3f4e52'` (`taikhoan-run-safe-sync`).
     Bắt buộc trả về exit code 0 (`last_status: ok`) để đảm bảo pipeline cron sync farm được thông suốt.
