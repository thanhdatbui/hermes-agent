# Kỷ Luật Warmup Hòm Thư & Vòng Đời Gmail Mới Reg (Fresh Gmail Lifecycle)

## 1. Bản Chất Kỹ Thuật Của Cơ Chế Warmup
Sau khi đăng ký thành công tài khoản Google Gmail mới trên điện thoại Samsung S7 (`register gmail` / `gmail_reg_v10.py`), tài khoản ở trạng thái **Fresh (Mới sinh)**:
- **Nguy cơ lớn nhất**: Bị Google quét vào danh sách tài khoản rác / tài khoản ảo (**Ghost Accounts**) do không có bất kỳ luồng thư hay tương tác gửi/nhận nào.
- **Giải pháp Warmup chuẩn**: Tự động kích hoạt hook `register_warmup_newsletters(email)` (`D:/Taadaa/tools/warmup_newsletter_services.py`) ngay khi vừa ghi nhận tài khoản thành công (`persist_success_result`).
  - Hệ thống gửi HTTP POST đăng ký nhận Newsletter công khai từ các tổ chức uy tín (*Cooperpress: Node Weekly, JavaScript Weekly, Ruby Weekly, Postgres Weekly, Frontend Focus; Hacker Newsletter*).
  - Các nguồn này lập tức gửi mail xác nhận (**Double Opt-in Confirmation / Welcome Email**) về thẳng hộp thư Gmail.
  - Luồng thư đến (**Inbound Activity**) tạo uy tín tự nhiên (Trust) với Google AI mà không cần phải thực hiện các thao tác giả lập phức tạp.

## 2. Vì Sao KHÔNG Cần Thiết Tạo Acc Ngoài (ChatGPT/Mạng Xã Hội) Trên S7 Để Warmup
1. **Lỗi Tương Thích WebView Android 8.0**:
   - Dàn Samsung S7 chạy Android 8.0.0 (Oreo). Khi bấm *"Continue with Google"* (OAuth) trên trình duyệt Chrome/WebView, Intent callback từ Google Accounts (`accountchooser`) bị điều hướng sai vào Activity cài đặt hệ thống (`Settings$UserAndAccountDashboardActivity`) thay vì trả auth token về lại trình duyệt.
   - App ChatGPT chính thức của OpenAI yêu cầu tối thiểu Android 9.0+ nên không thể cài đặt trên S7.
2. **Nguy Cơ Kích Hoạt Checkpoint Sớm**:
   - Tài khoản vừa sinh chưa đầy vài phút nếu đem đi đăng ký tài khoản dịch vụ ngoài liên tục sẽ dễ bị kích hoạt cờ hành vi bot bất thường.
3. **Kết luận**:
   - **Chỉ cần kích hoạt Newsletter Warmup là HOÀN TOÀN ĐỦ** để nuôi sống Gmail trong giai đoạn non trẻ. Tuyệt đối không over-engineer thêm các luồng đăng ký app bên ngoài trên thiết bị S7.

## 3. Vòng Đời Chuẩn (Fresh Gmail Lifecycle & Cooling Rule)
- **Giai đoạn 1 (0h - 48h): Ngâm Tĩnh Trên S7**
  - Tài khoản nằm trong ứng dụng Gmail của chính máy S7 đã reg.
  - Nhận mail Newsletter đều đặn.
  - **CẤM TUYỆT ĐỐI**: Không nạp lên GPM, không đăng nhập máy tính lạ, không bật 2FA sớm.
- **Giai đoạn 2 (Sau 24h - 48h): Trưởng Thành & Đưa Lên GPM**
  - Sau >= 24-48 giờ, tài khoản đã có lịch sử tồn tại ổn định trên thiết bị Android S7.
  - Chuyển sang nạp lên GPM Profile (kèm Proxy cố định) -> Đăng nhập Google mượt mà, bật 2FA Google Authenticator, hoặc liên kết với mọi dịch vụ ngoài (ChatGPT, OpenAI, Claude, MXH) mà không sợ bị dính checkpoint thiết bị lạ.
