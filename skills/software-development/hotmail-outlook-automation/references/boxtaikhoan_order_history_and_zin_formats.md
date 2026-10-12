# BoxTaiKhoan Order History & Hotmail Zin vs Recovery Formats

## 1. Phân loại định dạng tài khoản Hotmail từ BoxTaiKhoan (SHOPCLONE7)

Khi mua tài khoản Hotmail từ nguồn `boxtaikhoan.com`, cấu trúc dữ liệu trả về phụ thuộc vào phân loại sản phẩm:

- **Loại 5 trường (Đã có sẵn mail khôi phục):**
  - Tên SP ví dụ: *"Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes - Chưa Qua Dịch Vụ"* (thường bán ~167đ).
  - Cấu trúc: `email|password|refresh_token|client_id|recovery_email` (ví dụ `...|rec@fviainboxes.com` hoặc `...|rec@smvmail.com`).
  - Khi bảo mật / đổi thông tin: Tra cứu OTP khôi phục qua API domain tương ứng (ví dụ `https://fviainboxes.com/messages?username=...&domain=...`).

- **Loại 4 trường (Hotmail Zin trắng 100%):**
  - Tên SP ví dụ: *"Tài Khoản Hotmail Trust - OAuth2 [IMAP/POP3/GRAPH] Live 12 đến 36 Months - Zin 100% - Còn Skip 7 Ngày"* (thường bán ~393đ).
  - Cấu trúc: `email|password|refresh_token|client_id` (chỉ đúng 4 trường, **hoàn toàn KHÔNG có trường thứ 5**).
  - **CẢNH BÁO BẪY RUNNER / CHANGE_INFO:** Trong các script tự động đổi bảo mật Hotmail (như `gpm_change_hotmail_security.py`), tuyệt đối **KHÔNG ĐƯỢC** chặn lỗi `if not rec_email: return False` khiến hàng loạt tài khoản Zin bị đánh dấu `STATUS: BLOCKED`. Nick Zin chưa từng có mail khôi phục từ trước; quy trình hợp lệ là add trực tiếp mail khôi phục chính chủ (`thanhdatbui1995@gmail.com`) và đồng bộ OTP về Gmail theo đúng chính sách farm.

## 2. Quy tắc tra cứu lịch sử đơn hàng trên BoxTaiKhoan (SHOPCLONE7)

- **Bỏ qua câu cảnh báo giao diện 3 ngày:** Trên web `boxtaikhoan.com` có banner cảnh báo tĩnh: *"Lịch sử đơn hàng trên hệ thống chỉ được lưu trong 3 ngày kể từ thời điểm mua. Sau thời gian này, đơn hàng dữ liệu có thể bị xóa và không thể khôi phục."*
  - **Sự thật thực tế:** Đây chỉ là khuyến cáo phòng ngừa rủi ro của chủ shop. Cơ sở dữ liệu SHOPCLONE7 thực tế vẫn lưu trữ toàn bộ lịch sử đơn hàng qua nhiều tháng (đã kiểm chứng thực tế còn nguyên 17 trang / 166 đơn hàng từ tháng 7, 8 đến tháng 9).
  - Tuyệt đối không kết luận "đơn hàng đã bị xóa" chỉ dựa trên việc đọc dòng chữ cảnh báo đó.

- **URL cấu trúc đơn hàng:**
  - Danh sách đơn hàng: `https://boxtaikhoan.com/product-orders` hoặc `https://boxtaikhoan.com/client/product-orders?page=N`.
  - Chi tiết đơn hàng: `https://boxtaikhoan.com/product-order/{trans_id}` (ví dụ `#PCGW6a8de36e9ca7b`).
  - Mở nhanh cho User kiểm tra tay: Gọi lệnh Python:
    ```python
    import webbrowser
    webbrowser.open("https://boxtaikhoan.com/product-order/{trans_id}")
    ```
    Lệnh này sẽ kích hoạt Chrome mở thẳng tab chi tiết đơn hàng trước mặt User.

- **Tải file tài khoản đã mua từ giao diện:**
  - Nút icon đám mây (``) trên từng dòng kích hoạt SweetAlert2 popup *"Bạn có chắc không? Hệ thống sẽ tải về đơn hàng khi bạn nhấn đồng ý"*.
  - Bấm nút **"Đồng ý"** sẽ tải file text mang tên `{trans_id}.txt` về thư mục Downloads của máy.
