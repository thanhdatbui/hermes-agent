# BoxTaiKhoan Order & Recovery Email Reconciliation

## Bối cảnh & Nguyên tắc Cốt lõi
Khi kiểm tra tài khoản Hotmail bị Microsoft dựng thử thách bảo mật (challenge):
- Nếu Microsoft thông báo: *"Chúng tôi sẽ gửi mã đến xx*****@fviainboxes.com"* (hoặc `@smvmail.com`).
- **NGUYÊN TẮC BẮT BUỘC**: Chắc chắn đơn hàng gốc từ bên bán (BoxTaiKhoan / CloneFBIG) **CÓ cấp email khôi phục**. Tuyệt đối không được vội vàng kết luận là tài khoản trắng hay đơn hàng không có mail khôi phục.

## Format Đơn Hàng BoxTaiKhoan (5 trường)
Các gói sản phẩm Hotmail GraphAPI / Trusted có bảo mật phụ (như sản phẩm *"Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes - Chưa Qua Dịch Vụ"*):
Bên bán trả về đầy đủ **5 trường**:
```text
email | password | refresh_token | client_id | recovery_email
```
Ví dụ thực tế:
```text
annaisidorefidelma8810@hotmail.com|QmBqdJmf9O|M.C517_BAY.0...|9e5f94bc-e8a4-4e73-b8be-63364c29d753|annaisidorefidelma8810@fviainboxes.com
```

## Bẫy Lỗi Phổ Biến (Pitfalls)
1. **Bẫy cắt cụt 4 trường khi parse hoặc ghi log**:
   - Trong các script mua tự động cũ hoặc khi parse dữ liệu, một số hàm chỉ bốc `email, pass, refresh_token, client_id` rồi ghi ra file text, vô tình làm rơi mất trường thứ 5 (`recovery_email`).
   - Hậu quả: Khi nạp vào `gmail_clean_v2.xlsx` Cột 5 bị để `None`, khiến script đổi pass không tra cứu được mail khôi phục và fail-closed `BLOCKED`.
   - **Cách xử lý**: Mọi script parse đơn hàng từ BoxTaiKhoan bắt buộc phải kiểm tra:
     ```python
     recovery_email = parts[4].strip() if len(parts) > 4 else ""
     ```

2. **Cách đối soát trực tiếp trên Trình duyệt User qua Chrome CDP / Computer Use**:
   - Khi cần kiểm tra lại đơn hàng thực tế của User trên `boxtaikhoan.com`:
     - Profile Chrome của User (`C:\Users\Kibe\AppData\Local\Google\Chrome\User Data\Profile`) đã lưu phiên đăng nhập `thanhdatbui1995`.
     - Điều hướng đến `https://boxtaikhoan.com/product-orders/` hoặc chi tiết đơn hàng `https://boxtaikhoan.com/product-order/<order_id>`.
     - Lưu ý: BoxTaiKhoan có chính sách chỉ lưu lịch sử đơn hàng trên web trong **3 ngày** kể từ thời điểm mua. Các đơn hàng quá 3 ngày sẽ bị xóa khỏi lịch sử web, do đó dữ liệu đã tải về máy tính phải được bảo toàn nguyên vẹn 5 trường.

3. **Cơ chế dự phòng khi tài khoản thực sự không có mail khôi phục**:
   - Nếu đơn hàng cũ không có mail khôi phục và Microsoft không dựng challenge đòi gõ mail khôi phục:
     - Supervisor bắt buộc phải **bật 2FA TOTP trước** để tài khoản có phương thức xác minh thay thế.
     - Sau khi đã add 2FA, Microsoft cho phép đổi mật khẩu mà không bị chặn lỗi *"There's a temporary problem with the service"*.
