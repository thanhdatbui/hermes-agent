# Google Account Trust vs 2FA Myth & Concurrency Throttling

## 1. Bản chất sự cố Checkpoint khi Login GPM qua Proxy
- **Sai lầm nhận định (Myth):** "Bắt buộc tài khoản phải có 2FA mới đăng nhập được lên GPM".
  - *Thực tế chứng minh:* Acc `cecilssimpsono8a2m@gmail.com` **hoàn toàn không có 2FA**, không có secret key trên Excel, nhưng Google vẫn cho đăng nhập thẳng 100% chỉ với Email + Password mà không hỏi thêm bất kỳ bước xác minh nào.
- **Bản chất thực sự (Account Trust Score):**
  - Google Risk Engine quyết định việc cho qua hay kích hoạt checkpoint (`challenge/iap` đòi nhập số điện thoại mới) dựa trên **Độ Trust của tài khoản** và **môi trường truy cập**.
  - Nếu tài khoản đã được "làm ấm" (có lịch sử nhận email, đồng bộ hòm thư trên máy gốc S7, ngâm đủ lâu), Google đánh giá độ tin cậy cao và cho qua thẳng.
  - Nếu tài khoản chỉ ngâm tĩnh, vừa mở trên profile trình duyệt PC mới toanh qua cổng proxy thì Google lập tức kích hoạt Phone Checkpoint.

## 2. Hậu quả của Concurrency cao (`MAX_WORKERS = 5`)
- Khi mở đồng thời 5 browser Playwright qua mạng nội bộ:
  1. Gây tăng đột biến điểm nghi vấn (fraud score) từ phía Google do nhiều kết nối đồng thời từ cùng dải proxy/mạng.
  2. Gây nghẽn băng thông và tranh chấp tiến trình tại bước redirect về callback `:20129`.
  3. Khiến tài khoản dù đã qua bước nhập pass (như Cecil) cũng bị **chết oan do TIMEOUT 180s** ở bước click Consent / cấp mã Authorization Code.
- **Quy tắc điều phối bắt buộc:**
  - Hạ trần `MAX_WORKERS` từ 5 xuống **tối đa 2 workers** (hoặc 1 worker tuần tự).
  - Stagger thời gian khởi động tối thiểu 5-10s giữa các browser.

## 3. Chiến lược bồi Trust tự nhiên trước khi Login GPM
- Thay vì cố gắng đăng nhập lặp đi lặp lại trên PC gây cháy lượt proxy (`proxy_limit 2/port/ngày`) và tăng nguy cơ die nick:
  - Ban ngày: Tận dụng thời gian điện thoại Samsung S7 rảnh giữa các ca nuôi TikTok, cho chạy luồng liên kết ChatGPT qua **Direct Email OTP** trực tiếp trên điện thoại.
  - Thiết bị S7 mở hòm thư Gmail nhận mã OTP 6 số từ OpenAI $\rightarrow$ tạo luồng tương tác người dùng thật trên thiết bị tin cậy.
  - Sau khi tài khoản đã ấm và được gắn cờ `CHATGPT_READY`, ca tối watchdog GPM mới ưu tiên kéo lên browser PC, tỷ lệ vào thẳng không dính checkpoint tăng lên vượt bậc.

## 4. Kiểm kê Pool Antigravity trên OmniRoute (`:20129`)
- Tuyệt đối không dựa vào các file log trạng thái cục bộ cũ (như `oauth_pipeline_status.json` bị dừng ghi).
- Luôn kiểm tra trực tiếp qua API OmniRoute (`GET /api/providers` -> `connections` provider `antigravity`) hoặc đối soát qua Dashboard `:20129` để có con số thực tế chính xác nhất (ví dụ: 108 Antigravity accounts trong tổng 113 accounts).
