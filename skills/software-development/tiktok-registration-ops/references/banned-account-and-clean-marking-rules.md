# Banned Account Handling & Clean Mailbox Status Marking Rules

## 1. Quy tắc xử lý tài khoản TikTok bị ban / die

- **Trong bảng tracking `taikhoan_dat_v2_updated .xlsx`:**
  - Xóa sạch thông tin tài khoản ở slot đó: xóa `ID`, `PASS`, `2FA`, `GMAIL`, `PASS MAIL`, `NGÀY SINH`, `NGÀY TẠO`.
  - Giữ lại cấu trúc `Máy`, `Folder Video / Tik`, `device ID` với các giá trị tài khoản là `None` (ô trống) để phục vụ cho các lần đăng ký acc mới sau này.

- **Trong bảng kho mail sạch `gmail_clean_v2.xlsx`:**
  - **BẮT BUỘC GIỮ LẠI DÒNG MAIL TRONG KHO**, tuyệt đối KHÔNG xóa dòng khỏi file (để lưu vết kho và không làm lệch cấu trúc mail trên máy).
  - Điền giá trị vào cột **`trạng thái`** (Cột K / Cột 11) với một trong các từ khóa: `banned`, `die`, `khoa`, `used`, `da dung`, `skip`, `loi`, `blocked`.
  - Bộ lọc trong `_detect_clean.py` và hàm `load_emails_from_excel()` trong `social_reg_v1.py` tự động đọc cột `trạng thái` và loại bỏ 100% các email này, đảm bảo không bao giờ cấp lại cho bất kỳ máy nào để reg.

---

## 2. Quy tắc takeover máy đơn lẻ từ cohort đang chạy

- **Không dừng cả phiên nuôi acc:** Khi một máy trong dàn đang chạy nuôi acc chung (parent process điều phối nhiều máy), tuyệt đối không dùng `taskkill` hoặc lệnh dừng cả phiên làm ảnh hưởng đến các máy khác.
- **Giải phóng lock độc lập:** Sử dụng script nhả lock chuẩn của repo:
  ```bash
  python python_runner/scripts/release-device-lock.py --machine <N> --serial <SERIAL> --reason "takeover-for-reg"
  ```
- Sau khi lock của máy/serial đó được giải phóng an toàn, khởi chạy runner reg riêng cho máy đó với cờ `DEVICE_LOCK_ENABLED=1`.

---

## 3. Xử lý thanh cảnh báo "UPLOAD BLOCKED" của Excel trên OneDrive

- **Hiện tượng:** Mở file `gmail_clean_v2.xlsx` hoặc workbook trong thư mục OneDrive (`D:\OneDrive\TaadaaData\kibe\`) thấy thanh màu vàng/đỏ ghi `UPLOAD BLOCKED: We couldn't verify you have permissions to upload the file`.
- **Nguyên nhân:** File trên đĩa vừa được cập nhật bởi script Python ngầm trong khi bộ nhớ đệm Office Document Cache của Excel vẫn giữ phiên bản cũ.
- **Cách xử lý chuẩn:**
  1. Bấm nút **`Discard Changes`** trên thanh màu vàng.
  2. Khi hộp thoại xác nhận hiện ra (*"Discard local changes?"*), bấm **`Yes`**.
  3. Excel sẽ hủy bản cache cũ và tải lại chính xác dữ liệu mới nhất từ ổ đĩa.
