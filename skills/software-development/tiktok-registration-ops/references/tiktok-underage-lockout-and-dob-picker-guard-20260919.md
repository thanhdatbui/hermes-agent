# Bẫy Underage Lockout & DatePicker Guard Trong TikTok Registration (2026-09-19)

## 1. Hiện tượng & Triệu chứng
Tại màn hình chọn ngày sinh sau khi đã nhập OTP / xác minh email thành công:
- DatePicker trên một số máy Android (đặc biệt các dòng Samsung Galaxy S7 Android 7) khi cuộn năm sinh có thể vô tình trúng năm sinh < 13 tuổi (ví dụ năm 2015, 2024).
- Khi bấm nút **"Tiếp tục"**, TikTok lập tức bật popup cảnh báo:
  > *"Rất tiếc, có vẻ như bạn không đủ điều kiện tham gia TikTok... Nhưng cảm ơn vì đã đến với chúng tôi!"*
  (English: *"Sorry, it looks like you're not eligible for TikTok... But thanks for checking us out!"*)

## 2. Bản chất kỹ thuật (Server-side Underage Lock)
- Theo chính sách bảo vệ trẻ vị thành niên (COPPA / Minors policy), TikTok gắn cờ `underage_lock` trên server đối với phiên đăng ký và địa chỉ email đó.
- **Hậu quả vĩnh viễn:** Kể cả khi:
  - Thoát app ra màn hình Home hoặc force-stop app TikTok.
  - Xóa cache / mở lại quy trình đăng ký từ đầu với email đó.
  - Lấy mã OTP mới điền vào và chọn năm sinh chuẩn (ví dụ 1999, 1980 - đủ 18+ tuổi).
  - Vừa bấm "Tiếp tục", server TikTok vẫn nhớ email đã từng khai tuổi < 13 và tiếp tục từ chối tạo tài khoản.
- **Kết luận:** Địa chỉ email đã dính cờ Underage **KHÔNG THỂ DÙNG ĐỂ REG TIKTOK ĐƯỢC NỮA**.

## 3. Quy tắc phòng ngừa & Xử lý (Invariant)
1. **DatePicker Pre-submit Guard:**
   - Trong script chọn ngày sinh (`fill_birthday`), trước khi tap nút **"Tiếp tục"** (hoặc submit DatePicker), BẮT BUỘC phải đọc XML của node hiển thị ngày đã chọn (ví dụ text dạng `19 tháng 9, 2000`).
   - Parse trích xuất số năm bằng regex `r"\b(19\d{2}|20\d{2})\b"`.
   - Nếu `current_year - selected_year < 18` (ví dụ năm > 2006): **TUYỆT ĐỐI CẤM BẤM TIẾP TỤC**. Phải cuộn tiếp bánh xe năm sinh lùi về trước cho đến khi năm sinh <= 2005 mới được submit.
2. **Xử lý khi đã bị Underage Lock:**
   - Đánh dấu email đó là `UNDERAGE_BLOCKED` trong kho mail nội bộ (`gmail_clean_v2.xlsx`).
   - Loại bỏ email này khỏi danh sách reg, không retry lặp lại gây mất thời gian.
   - Cấp phát và nạp một tài khoản Hotmail Zin mới chưa từng dính cờ ngày sinh để tiếp tục phiên.
