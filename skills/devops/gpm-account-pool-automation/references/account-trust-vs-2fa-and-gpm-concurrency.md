# Google Account Trust vs 2FA & Multi-Worker GPM Concurrency Pitfalls

## 1. Bản chất: Account Trust Score vs 2FA
### Sai lầm kinh điển
- Nhầm lẫn giữa việc "Bắt buộc tài khoản phải có 2FA mới đăng nhập được trên browser PC" và "Độ tin cậy của tài khoản (Account Trust Score)".
- Sự thật thực tế từ hiện trường:
  - Tài khoản **hoàn toàn không có 2FA** nhưng có độ trust cao (ngâm đủ lâu $\ge 14$ ngày, proxy sạch, thiết bị gốc S7 có lịch sử sạch) vẫn đăng nhập vào thẳng 100% chỉ với `Email + Mật khẩu` mà Google không hề hỏi thêm OTP hay kích hoạt checkpoint (ví dụ điển hình: `cecilssimpsono8a2m@gmail.com`).
  - Ngược lại, nếu chạy concurrency cao hoặc IP proxy bị đánh dấu suspicious, Google Risk Engine sẽ kích hoạt **Hard Phone Checkpoint (`challenge/iap`)** đòi số điện thoại mới ngay lập tức, bất kể tài khoản có 2FA hay chưa.

## 2. Concurrency Pitfall: MAX_WORKERS = 5 gây nghẽn và rớt OAuth
### Hiện tượng
- Bung 5 workers song song cho Playwright + GPMLogin:
  - Tài khoản đã đăng nhập thành công vào đến màn hình cấp quyền OAuth (`.../signin/oauth/firstparty/nativeapp`), nhưng do proxy/mạng nghẽn và tranh chấp tài nguyên, Playwright loop không kịp click nút "Cho phép / Tiếp tục" trước khi hết timeout 180s.
  - Kết quả: Watchdog đánh dấu **FAIL / TIMEOUT** oan cho tài khoản (mặc dù session Google đã lưu vào đĩa thành công).
  - Khi chạy lại đơn lẻ (1-2 workers), tài khoản mở lên gặp ngay bảng Chọn tài khoản (Account Chooser) và hoàn tất nạp OAuth trong vài giây.

### Quy tắc điều phối
- **Hạ trần Concurrency**: `MAX_WORKERS` cho luồng GPMLogin + Google OAuth chỉ duy trì ở mức **tối đa 2 workers** (chạy cuốn chiếu, stagger 5-10s).
- **Tránh false failure**: Luôn kiểm tra session cookie / lịch sử duyệt web thực tế trước khi kết luận tài khoản bị checkpoint.

## 3. Chiến lược nạp Trust trước khi đưa lên PC
1. **Reg/Link ChatGPT trực tiếp trên thiết bị S7 trước (Direct Email OTP)**:
   - OpenAI gửi OTP về app Gmail trên thiết bị gốc Samsung S7.
   - Việc mở Gmail, đồng bộ hòm thư và đọc mã OTP trên điện thoại tạo hành vi người dùng thật (User Engagement) tự nhiên 100%, không bị Google chặn.
   - Tài khoản sau khi hoàn tất sẽ được gắn cờ `CHATGPT_READY` trên Excel, bồi đắp trust trước khi đưa lên trình duyệt PC.
   - **Kỷ luật Scope Lock (RÚT KINH NGHIỆM ĐIỀU PHỐI)**: Khi chạy watchdog liên kết ChatGPT để bồi trust, **CHỈ quét tập hợp tài khoản đang nằm trong diện CHỜ LOGIN GPM** (tức là: đã có profile GPM nhưng chưa nạp OmniRoute/chưa có session). Tuyệt đối KHÔNG quét toàn bộ tài khoản farm diện rộng, tránh làm lệch trọng tâm và vi phạm phạm vi nhiệm vụ của task Đăng nhập GPM.
2. **Fail-Closed Gate cho ngày tuổi (Aged Gate)**:
   - Khi kiểm tra điều kiện ngâm $\ge 7$ ngày, bắt buộc dùng cơ chế **Fail-Closed**: nếu không có ngày tạo hoặc định dạng ngày lỗi, phải bỏ qua candidate ngay lập tức, tuyệt đối không fail-open cho đi tiếp để tránh rủi ro vướng checkpoint.
