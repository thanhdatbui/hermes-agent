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
   - **KỶ LUẬT PHỚT LỜ CẢNH BÁO "CHỈ LƯU 3 NGÀY" (User Correction 2026-10-12)**:
     - Dòng thông báo *"Lịch sử đơn hàng trên hệ thống chỉ được lưu trong 3 ngày... sau thời gian này dữ liệu có thể bị xóa"* trên web CHỈ LÀ disclaimer khuyến cáo của bên bán CMSNT, KHÔNG PHẢI cơ chế xóa cứng tự động.
     - Thực tế kiểm chứng: Hệ thống BoxTaiKhoan của User vẫn lưu trữ đầy đủ 166 đơn hàng từ tháng 07/2026 đến tháng 09/2026.
     - **CẤM TUYỆT ĐỐI** Agent vin vào câu cảnh báo 3 ngày để thoái thác, từ chối tìm kiếm hoặc kết luận vội vàng là đơn hàng đã mất. Bắt buộc phải bấm duyệt qua các trang phân trang (`page=1`, `page=2`... `page=17`) để đọc hiện trường.
   - **Đặc điểm username của recovery email**:
     - Email khôi phục `@fviainboxes.com` KHÔNG trùng 100% với username Hotmail mà luôn có đuôi ngẫu nhiên 3-4 ký tự (ví dụ: `tamaiischester` -> `tamaiischester84x@fviainboxes.com`, `guadarramanilges923` -> `guadarramanilges923awr@fviainboxes.com`, `chasdanyell368` -> `chasdanyell3682ia@fviainboxes.com`).
     - Do đó, CẤM tự ý bịa hoặc đoán recovery email; bắt buộc phải lấy từ chuỗi 5 trường trong đơn hàng thực tế.
   - **Thao tác điều hướng & bóc tách dữ liệu trên BoxTaiKhoan web**:
     - Link chi tiết đơn hàng dạng `https://boxtaikhoan.com/product-order/<trans_id>` chứa bảng danh sách tài khoản (`product_sold`), trường credentials dạng textarea chứa đủ chuỗi 5 trường.
     - Chuyển trang: Click trực tiếp vào các nút số trang phân trang (`#156 Hyperlink '2'`, `#157 Hyperlink '3'`...) ở chân bảng. Chú ý nút phân trang có thể nằm ở sát đáy viewport, cần click chuột hoặc kéo vào vùng hiển thị trước khi kích hoạt.

3. **Cơ chế dự phòng khi tài khoản thực sự không có mail khôi phục**:
   - Nếu đơn hàng cũ không có mail khôi phục và Microsoft không dựng challenge đòi gõ mail khôi phục:
     - Supervisor bắt buộc phải **bật 2FA TOTP trước** để tài khoản có phương thức xác minh thay thế.
     - Sau khi đã add 2FA, Microsoft cho phép đổi mật khẩu mà không bị chặn lỗi *"There's a temporary problem with the service"*.
