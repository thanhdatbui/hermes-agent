# Pitfall Bẫy Underage / DatePicker Ngày Sinh Trên Samsung S7 (Case 2026-09-19)

## 1. Hiện tượng & Vấn đề gốc
Trong flow đăng ký TikTok (`social_reg_v1.py` / `Tiktok_Reg`):
- Sau khi nhập email và điền thành công mã OTP xác nhận (qua Graph API hoặc Outlook app), TikTok chuyển tiếp sang màn hình **"Ngày sinh của bạn là ngày nào?"** (`DatePicker` 3 cột: ngày, tháng, năm).
- Mặc định trên một số thiết bị Samsung S7 (Android 7), con lăn chọn năm có thể trỏ vào năm gần hiện tại (hoặc năm < 18 tuổi, ví dụ 2015).
- Nếu script bấm **"Tiếp tục"** khi năm sinh chưa đủ 13 tuổi (hoặc < 18 tuổi):
  - TikTok lập tức hiện thông báo chặn:
    > *"Rất tiếc, có vẻ như bạn không đủ điều kiện tham gia TikTok... Nhưng cảm ơn vì đã đến với chúng tôi!"*
  - **Hậu quả nghiêm trọng:** TikTok đánh dấu cờ **Underage Lockout** vĩnh viễn trên phiên đăng ký của email đó. Dù sau đó người dùng hoặc script có ấn OK, chỉnh lại năm sinh thành 1969/1999/2001 và submit lại nhiều lần, TikTok vẫn từ chối và chặn cứng email này ("không đủ điều kiện tham gia TikTok"), làm hỏng (burn) tài khoản mail zin vừa nạp.

## 2. Quy tắc phòng ngừa & Fix chuẩn
1. **Kiểm tra năm sinh TRƯỚC KHI bấm Tiếp tục:**
   - Tuyệt đối KHÔNG tap submit / "Tiếp tục" nếu chưa cuộn con lăn năm sinh lùi về trước ít nhất 18-25 năm (năm sinh hợp lệ: 1990 - 2004).
   - Đọc giá trị TextView hiển thị ngày sinh đã chọn (ví dụ node text `19 tháng 9, 2015` vs `19 tháng 9, 1999`) qua ATX XML dump. Bắt buộc regex kiểm tra năm $\le \text{current\_year} - 18$ mới được bấm Tiếp tục.

2. **Cách cuộn DatePicker trên Android (Samsung S7):**
   - Cột Năm thường nằm ở $x \approx 720..960$ ($x_{center} \approx 840$).
   - Cuộn từ trên xuống (`swipe 840 1200 840 1500`) trên NumberPicker Android làm giảm năm (lùi về quá khứ).
   - Thực hiện cuộn lặp có kiểm tra giá trị text đọc được cho đến khi năm đạt ngưỡng an toàn (ví dụ 1995 - 2002).

3. **Xử lý khi đã lỡ dính Underage Block:**
   - Email đã dính block Underage trên TikTok KHÔNG THỂ tái sử dụng để reg TikTok tiếp được nữa.
   - Bắt buộc loại bỏ email này khỏi danh sách reg của máy, đánh dấu trạng thái hỏng do underage và thay thế bằng mail Zin khác từ kho sạch.
