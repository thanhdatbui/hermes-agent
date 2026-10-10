# boxtaikhoan.com — Tra cứu lịch sử đơn hàng & Đối soát tài khoản đã mua (2026-10)

## 1. Endpoint & Phiên đăng nhập
- **URL danh sách đơn hàng:** `https://boxtaikhoan.com/product-orders`
- **URL chi tiết đơn hàng:** `https://boxtaikhoan.com/product-order/<order_code>` (Ví dụ: `https://boxtaikhoan.com/product-order/821P6a8977522f650`)
- **API Key lưu ý:** API endpoint `api/profile.php` có thể bị lỗi `"API key không hợp lệ"` nếu key hết hạn hoặc bị đổi. Tuy nhiên phiên đăng nhập web trên trình duyệt Chrome Profile thường lưu cookie session lâu dài (`PHPSESSID`, session token).

## 2. Pitfall Cảnh Báo "Chỉ lưu 3 ngày" (Static Disclaimer Trap)
Khi truy cập `product-orders`, banner trên đầu trang hiển thị:
> *"Lịch sử đơn hàng trên hệ thống chỉ được lưu trong 3 ngày kể từ thời điểm mua. Sau thời gian này, đơn hàng dữ liệu có thể bị xóa và không thể khôi phục. Vui lòng sao lưu tài khoản đã mua về máy tính/email cá nhân ngay sau khi nhận để tránh mất dữ liệu."*

**CẢNH BÁO QUAN TRỌNG:**
- Đây là **câu thông báo tĩnh (static policy disclaimer)** nhằm khuyến khích khách hàng tải dữ liệu về máy, **KHÔNG PHẢI** bằng chứng dữ liệu đã bị xóa thực tế!
- Thực tế trên sàn: Hệ thống vẫn lưu trữ toàn bộ lịch sử đơn hàng từ nhiều tháng trước (hàng trăm đơn hàng trải dài trên 17+ trang phân trang).
- **CẤM TUYỆT ĐỐI** đọc dòng cảnh báo này rồi vội vã báo User rằng "đơn hàng đã bị xóa không thể lấy lại".

## 3. Quy trình trích xuất dữ liệu đơn hàng cũ
1. **Lật trang / Phân trang:** 
   - Kiểm tra tổng số kết quả ở cuối bảng (ví dụ: `Hiển thị 10 trên 166 kết quả` -> có 17 trang).
   - Duyệt ngược về các trang cuối (`page=14`, `page=15`, `page=16`...) để tìm các đơn mua trong quá khứ theo ngày tháng (`HH:mm - DD/MM/YYYY`).
2. **Mở chi tiết đơn hàng:**
   - Tại dòng đơn hàng, click vào icon xem chi tiết mắt (``) hoặc chuyển hướng đến `https://boxtaikhoan.com/product-order/<order_code>`.
3. **Đọc dữ liệu tài khoản bàn giao:**
   - Bảng **"CHI TIẾT ĐƠN HÀNG"** hiển thị danh sách tài khoản đã mua.
   - Với các gói mua theo batch (ví dụ đơn 26 tài khoản), bảng có phân trang riêng (`Showing 10 of 26 Results`). Bắt buộc duyệt qua các trang con (1, 2, 3) để tìm đúng tài khoản mục tiêu.
   - Cột **TÀI KHOẢN** chứa chuỗi credential gốc ban đầu:
     `email|pass|refresh_token|client_id`
   - Dùng chuỗi này để đối soát độc lập khi nghi ngờ mật khẩu trong database / Excel bị ghi đè, ghi sai hoặc lệch cột.
