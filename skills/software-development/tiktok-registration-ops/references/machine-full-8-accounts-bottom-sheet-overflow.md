# MACHINE_FULL_8_ACCOUNTS Bottom-Sheet Overflow & False Alarm Triage

## Bối cảnh & Hiện tượng (Symptom)
Khi preflight reg bù (`ensure_row_accounts.py <row>`) chạy cho các máy thiếu slot Row N (thường là Row 5, 6, 7), hàng loạt máy bị văng lỗi:
`RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
Và báo cáo tổng kết về Telegram hiển thị:
`- Máy N: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`

## Phân biệt 2 tình huống (Triage Mandate)
TUYỆT ĐỐI CẤM vội vàng kết luận máy đã có 8 tài khoản hay vội vàng backfill đè dữ liệu! Bắt buộc trích xuất ảnh dropdown hiện trường:
`D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_*.png` và chạy WinRT OCR (`windows-native-ocr`) để đếm chính xác số username hiển thị:

### Tình huống 1: FALSE ALARM (Máy thực tế chỉ có 7 acc - Phổ biến nhất)
* **Dấu hiệu**:
  - OCR trên ảnh switcher đọc được đúng **7 username**.
  - Đối soát `taikhoan_dat_v2_updated .xlsx` cũng chỉ có đúng **7 dòng tài khoản** cho máy này.
  - Cả máy thật và Excel đều chưa đạt mốc 8 tài khoản.
* **Căn nguyên kỹ thuật**:
  - Màn hình SM-G930F (1080x1920) khi chứa 7 tài khoản trong bottom sheet: 7 account rows chiếm trọn chiều cao màn hình (~1700px), đẩy mục *"Thêm tài khoản"* xuống dưới đáy hoặc ngoài viewport hiển thị.
  - Script `tap_add_account()` trước đây không có thao tác cuộn (`swipe up`), chỉ tìm kiếm ở attempt đầu rồi `break`.
  - Khi không tìm thấy nút *"Thêm tài khoản"*, fallback counter `_acc_count` duyệt `_root.iter("node")` với resource-id `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk", "ng8"]`. Do cả container layout (`lli` - text rỗng) và text node (`ng8`) đều khớp điều kiện, mỗi account bị đếm 2 lần (hoặc container của nút Thêm tài khoản bị đếm gộp thành account), ra kết quả `_acc_count = 14..15 >= 8`.
  - Script ngộ nhận máy đã full 8 acc và ném ngoại lệ sai.
* **Cách khắc phục chuẩn trong `social_reg_v1.py`**:
  1. Trong vòng lặp `attempt in range(3)` của `tap_add_account`, nếu `attempt < 2` và chưa thấy nút, bắt buộc swipe cuộn bottom sheet lên: `swipe(device_id, 540, 1500, 540, 800, 400)`.
  2. Chuẩn hóa `_account_names = set()` chỉ gom các node có text/desc phi rỗng và loại trừ các chuỗi điều hướng ("Thêm tài khoản", "Chuyển đổi", v.v.). Chỉ khi `len(_account_names) >= 8` mới coi là full.

### Tình huống 2: LỆCH EXCEL THẬT SỰ (Máy thực tế đã đủ 8 acc)
* **Dấu hiệu**:
  - OCR trên switcher đọc được đủ **8 username** khác nhau.
  - Trong `taikhoan_dat_v2_updated .xlsx` chỉ có 7 acc (bị thiếu 1 acc do rơi rớt log hoặc chưa sync).
* **Xử lý**:
  - Tìm username ở slot bị thiếu từ kết quả OCR.
  - Truy vết password/email từ backup hoặc log cũ (`taikhoan_dat_v2_updated_BEFORE_RESTORE*.xlsx`, `archive_history`).
  - Backfill đồng bộ 4 nơi: `taikhoan_dat_v2_updated .xlsx` -> `taikhoan_run_safe.xlsx` -> `TikN.xlsx` -> `tiktok_tracker.db`.

## Lưu ý về Xiaowei ADB & Remote Cluster (Admin Host)
- Executable `C:\Program Files (x86)\xiaowei\tools\adb.exe` trên Windows có cơ chế tích hợp tự động đọc biến môi trường `ADB_SERVER_SOCKET` (ví dụ `ADB_SERVER_SOCKET=tcp:192.168.110.119:5037`).
- Khi env này được export trong subprocess, mọi lệnh ADB gọi qua `adb.exe -s <serial> shell ...` tự động điều hướng sang server remote Admin mà không cần truyền cờ `-H` / `-P` thủ công.
