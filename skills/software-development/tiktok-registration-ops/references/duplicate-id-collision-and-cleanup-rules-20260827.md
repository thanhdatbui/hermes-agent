# Nguyên Nhân Sinh ID Trùng Lặp & Quy Tắc Dọn Dẹp Workbook (2026-08-27)

## 1. Root Cause Cơ Chế Sinh ID Trùng Lặp Trong `social_reg_v1.py`

### Triệu chứng
Nhiều hàng trên cùng một máy trong `taikhoan_dat_v2_updated .xlsx` bị ghi trùng ID TikTok (ví dụ: máy 11 có 2 hàng `minh.thu3282`, máy 13 có 2 hàng `m.my7409`, máy 38 có 2 hàng `benghxmk3zu`...).

### Cơ chế gây lỗi
1. **Lỗi nhận diện thành công giả (`wait_login_success`):**
   - Khi chạy reg tài khoản cho email mới trên máy đã có sẵn nick đăng nhập từ trước:
   - Nếu bước mở Switcher để tạo tài khoản mới bị trượt, kẹt popup, hoặc văng về Home feed/Profile.
   - Hàm `wait_login_success` quét UI XML thấy các từ khóa chung ("Trang chủ", "Hồ sơ", "Bạn bè", "Đề xuất") của **nick cũ đang mở trên máy** -> hàm trả về `True` (tưởng lầm đã tạo xong nick mới).
2. **Lỗi đọc ID ghi đè vào Excel (`ensure_profile_completed_and_track`):**
   - Sau khi nhận định thành công, script điều hướng vào Profile và gọi `extract_profile_identity(xml)`.
   - Hàm đọc `@handle` hiện tại trên màn hình (chính là ID của nick cũ) và gọi `upsert_tracking_account` / `write_deferred_tracking_result` ghi handle đó vào hàng của email mới.
   - Hệ quả: Nick cũ bị ghi đè lên hàng của email mới, tạo ra 2 hàng trùng ID trên cùng một máy.

### Biện pháp phòng chống trong code
- Bắt buộc kiểm tra danh tính tài khoản mới tạo (hoặc kiểm tra profile handle không được trùng với các nick đã có trên máy).
- Khi mở profile sau reg, nếu handle trúng với ID của slot khác trên cùng máy -> fail-closed, không ghi đè vào tracking.

---

## 2. Quy Tắc Dọn Dẹp Hàng Trùng Trên Workbook `taikhoan_dat_v2_updated .xlsx`

1. **Sao lưu trước khi chỉnh sửa:**
   - Luôn tạo bản sao lưu trong `D:\Taadaa\BACKUP_ALL\` trước khi thao tác trên file master.
2. **Xử lý xóa hàng trùng:**
   - Khi phát hiện hàng trùng ID do lỗi ghi đè reg:
     - Hàng trùng thiếu info (Pass = None, 2FA = None) hoặc hàng user chỉ định xóa: **Xóa sạch toàn bộ thông tin tài khoản ở các cột 3..9 (ID, PASS, 2FA, GMAIL, PASS MAIL, DOB, CREATED)**.
     - **Bảo toàn cấu trúc Slot vật lý:** Tuyệt đối giữ nguyên Cột 1 (`Máy`), Cột 2 (`Folder Video`), Cột 10 (`device ID`) để slot trống sẵn sàng chờ cấp nick mới.
3. **Đồng bộ sau khi dọn:**
   - Chạy ngay script đồng bộ `hermes_taikhoan_sync_cron.py` / `sync-safe-workbook.py` để cập nhật danh sách nick sạch sang `taikhoan_run_safe.xlsx`.

---

## 3. Xử Lý Máy Kẹt Màn Hình "Thêm Tên Bạn Mong Muốn" Khi Switch Account

### Triệu chứng
Máy kẹt ở màn hình con đổi tên TikTok (`com.ss.android.ugc.trill:id/tv_content_name` / "Thêm tên bạn mong muốn") khi thực hiện preflight switch account hoặc vào Profile.

### Khắc phục
1. Nhập display name tiếng Việt chuẩn qua `AdbKeyboard` (`am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64>`).
2. Bấm nút **"Lưu"** ở góc trên bên phải (bounds `[925,72][1056,204]`).
3. Bấm xác nhận dialog cảnh báo 7 ngày ("Xác nhận" bounds `[541,1104][960,1247]`).
4. Khôi phục lại bàn phím hệ thống `com.sec.android.inputmethod/.SamsungKeypad` và quay về Profile root.
