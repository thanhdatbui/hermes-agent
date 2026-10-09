# BoxTaiKhoan Catalog & Pricing Quirks (Hotmail/Outlook)

Cập nhật: 2026-09-20.

## 1. Cờ `is_private = 1` trên BoxTaiKhoan
- Một số sản phẩm trên BoxTaiKhoan (như ID 129 - Hotmail Zin Graph API 166đ) có thể xuất hiện trong API catalog `/api/products.php?api_key=...` với tồn kho lớn (hơn 10.000 mail).
- Tuy nhiên trường `is_private: 1` cho biết đây là sản phẩm riêng tư/ẩn.
- **Hệ quả**: Nếu gọi API mua công khai `buyProduct` qua `POST /ajaxs/client/product.php` hoặc tải modal mua `/ajaxs/client/modal/view-product.php?id=129`, backend sẽ chặn và báo `"Sản phẩm không tồn tại trong hệ thống"`.
- **Giải pháp**: Phải đăng nhập tài khoản trực tiếp trên web bằng trình duyệt xem user có được cấp quyền mua sản phẩm này hay không.

## 2. Bản chất giá Hotmail: Hàng Zin (166đ) vs Hàng Đã Qua Dịch Vụ (382đ)
- **Hàng Zin Chưa Qua Dịch Vụ / New Reg (VD: ID 129 ~166đ)**:
  - Sinh bằng tool reg tự động hàng loạt gần đây.
  - Mail khôi phục thường là domain tạm (`fviainboxes.com`).
  - Giá sỉ rất rẻ để đẩy nhanh số lượng, nhưng do mới tạo nên độ ngâm (aged) thấp.
  - Phù hợp nhất cho mục đích Reg TikTok mới vì chưa bị cấm/đánh dấu dịch vụ.
- **Hàng Đã Qua Dịch Vụ / Aged Mail (VD: ID 21128 ~382đ)**:
  - Tên ghi `already used the service`, thường đã qua các dịch vụ khác (như Facebook hoặc các trang mạng).
  - Bản chất là mail đã ngâm lâu (6–12+ tháng), độ trust của Microsoft rất cao.
  - Rất khó bị dính checkpoint hoặc khóa tài khoản khi login trên thiết bị/IP mới.
  - Tích hợp sẵn API lấy mã khôi phục từ cả `fviainboxes.com` và `smvmail.com`.
  - Giá cao hơn chủ yếu do chi phí thời gian ngâm tài khoản.
