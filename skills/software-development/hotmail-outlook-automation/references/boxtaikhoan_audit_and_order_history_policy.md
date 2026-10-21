# BoxTaiKhoan Audit & Order History Policy

## 1. Kiểm tra nhanh Token API Hotmail (Tra cứu trực tiếp DB, cấm suy đoán)
- Khi user hỏi tài khoản có Token API Live hay không, hoặc nghi ngờ lúc nhập dữ liệu bị lưu thiếu:
  - Mở trực tiếp file canonical `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Sheet `Gmail Accounts`):
    * Cột 1: STT / Máy
    * Cột 2: Email
    * Cột 3: Password
    * Cột 5: Mail khôi phục (`@fviainboxes.com`)
    * Cột 9: `token` (Refresh Token)
    * Cột 10: `client_id` (Application ID)
  - Đối chiếu thêm `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`).
  - Nếu Cột 9 và Cột 10 để trống (`None`), tài khoản đó KHÔNG CÓ Token API trong database. Trả lời dứt khoát kết quả đọc từ dòng dữ liệu thực tế, không dông dài lý thuyết hay thanh minh.

## 2. Chính sách lưu trữ đơn hàng BoxTaiKhoan (boxtaikhoan.com)
- **Quy tắc 3 ngày cứng**: `https://boxtaikhoan.com/product-orders` hiển thị cảnh báo chính thức:
  > *"Lịch sử đơn hàng trên hệ thống chỉ được lưu trong 3 ngày kể từ thời điểm mua. Sau thời gian này, đơn hàng dữ liệu có thể bị xóa và không thể khôi phục."*
- **Hệ quả khi tra cứu**:
  * Các đơn hàng mua quá 3 ngày (ví dụ các đợt mua tháng 8/2026) chắc chắn đã bị web server xóa khỏi trang quản trị cá nhân.
  * Việc cố gắng crawl hoặc tìm lại đơn hàng cũ trên web BoxTaiKhoan sau 3 ngày là vô hiệu.
  * Bằng chứng truy xuất nguồn gốc đơn cũ bắt buộc dựa vào:
    1. Các file txt mua về lưu tại `D:\Taadaa\Hotmail\` (`latest_bought_70.txt`, `hotmail_all_60_bought.txt`, `hotmail_input.txt`...).
    2. File backup Excel theo mốc thời gian (`D:\OneDrive\TaadaaData\kibe\_backup\` hoặc `gmail_clean_v2_before_*.xlsx`).
    3. Git commit history của repo `Hotmail` và `Tiktok_Reg`.

## 3. Phân biệt Hotmail OAuth vs Hotmail Via thường
- **Gói Hotmail OAuth (Mua qua API tool `buy_hotmail.py`)**:
  * BoxTaiKhoan Product ID `129` hoặc CloneFBIG Product ID `3470`.
  * Định dạng trả về chuẩn gồm 4–5 trường: `email | password | refresh_token | client_id | [recovery_email]`.
  * Script `buy_hotmail.py` tự động ghi đầy đủ Refresh Token vào Cột 9 và Client_ID vào Cột 10. Không có tình trạng lưu thiếu một nửa.
- **Gói Hotmail Via / Basic nhập tay (Đợt đầu tháng 8/2026)**:
  * Định dạng bán chỉ gồm 3 trường: `email | password | recovery_email` (mail khôi phục ảo `@fviainboxes.com`).
  * Hoàn toàn không kèm Refresh Token OAuth từ lúc bán.
- **Cách chứng minh tài khoản vốn dĩ không có OAuth Token từ đầu**:
  * Kiểm tra log lần đầu lấy OTP reg TikTok trong `D:\Taadaa\Tiktok_Reg\social_reg_log.txt`:
    - Nếu xuất hiện log: `[otp-outlook-app] Non-Gmail target -> read via Outlook app` -> chứng minh ngay tại thời điểm khởi tạo, hệ thống đã nhận diện mail không có OAuth token nên phải ủy quyền mở app Outlook trên điện thoại để đọc thư.
