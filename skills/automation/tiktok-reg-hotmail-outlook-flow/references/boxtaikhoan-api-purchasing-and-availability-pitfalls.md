# BoxTaiKhoan API Purchasing & Availability Pitfalls (2026-09-20)

## 1. Trạng Thái Sản Phẩm Hotmail trên BoxTaiKhoan
- **Gói 129**: `Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes - Chưa Qua Dịch Vụ`
  - Đơn giá: 166đ (modal hiển thị 167đ).
  - Tồn kho: Thường lớn (>9.000 mail).
  - Đặc điểm: Mail new reg sạch, chưa từng tạo dịch vụ nào (Zin 100%), định dạng OAuth2 / Graph API có kèm mail khôi phục `fviainboxes.com`.
  - Phù hợp nhất cho việc đăng ký tài khoản TikTok trên Farm.
- **Gói 21128**: `HOTMAIL TRUST LIVE already used the service`
  - Đơn giá: 382đ.
  - Tồn kho: Rất lớn (>25.000 mail).
  - Đặc điểm: Mail đã từng liên kết dịch vụ khác (như FB), nhưng là mail cổ (Aged mail ngâm lâu 6-12 tháng) có độ trust cao, khó checkpoint.

## 2. Pitfall Kiểm Tra Trạng Thái Mở Bán (Web vs API)
- Tránh false negative: API backend (`/api/products.php?api_key=...`) có thể tạm thời gắn cờ `is_private = 1` hoặc một số endpoint trả về không đầy đủ.
- Trước khi kết luận sản phẩm bị đóng/ẩn, **bắt buộc kiểm tra trực tiếp qua**:
  1. Web slug: `https://boxtaikhoan.com/product/<slug>` xem nút "MUA NGAY" có active không.
  2. Modal order: `https://boxtaikhoan.com/ajaxs/client/modal/view-product.php?id=<id>` xem có render giao diện "Xác nhận đơn hàng" hay báo "Sản phẩm không tồn tại".

## 3. Pitfall Mua Hàng Qua API (`action=buyProduct`)
- Endpoint: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- Payload:
  ```json
  {
    "action": "buyProduct",
    "id": "129",
    "variant_id": "0",
    "amount": "1",
    "coupon": "",
    "api_key": "<KEY>",
    "user_input": "{}"
  }
  ```
- **Hiện tượng lỗi**:
  - Trừ tiền số dư tài khoản.
  - Backend gặp sự cố ở khâu phân bổ account Hotmail từ kho trả về qua API.
  - Trả về JSON lỗi:
    ```json
    {
      "status": "error",
      "msg": "Không thể xử lý đơn hàng lúc này, vui lòng thử lại sau ít phút. Tiền đã được hoàn về tài khoản."
    }
    ```
  - Tiền lập tức được rollback/hoàn lại vào tài khoản (`money` giữ nguyên).
- **Cách xử lý**:
  - TUYỆT ĐỐI CẤM loop spam lệnh mua API khi đã nhận thông báo này.
  - Chuyển sang mua trực tiếp trên giao diện trình duyệt Web (hoặc qua CDP Chrome port 9222) bằng session đăng nhập người dùng thật. Web checkout xử lý đơn hàng mượt mà và chuyển hướng vào `/product-order/<trans_id>` để copy account.
