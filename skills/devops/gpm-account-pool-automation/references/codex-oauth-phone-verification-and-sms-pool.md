# Codex OAuth Phone Verification Automation & SMS Service Architecture

## 1. Bản chất phân biệt giữa ChatGPT Web và Codex CLI OAuth
- **ChatGPT Web (`chatgpt.com/backend-api/conversation`)**:
  - Đăng nhập qua session Google OAuth chuẩn hoặc cookies.
  - Không bắt buộc verify số điện thoại (Phone Verification).
  - Điểm yếu: Body payload giới hạn chặt (~500KB - 1MB JSON). Khi các agent mang theo system prompt dài + danh sách tool schemas + conversation history sẽ bị WAF dội lỗi **HTTP 413 (Payload Too Large)**.
- **Codex CLI (`auth.openai.com` qua scope `offline_access`)**:
  - Sử dụng REST API chuẩn của OpenAI (`api.openai.com`), context window lớn (128K - 200K tokens), payload nhiều MB không bao giờ dính 413.
  - Bắt buộc tài khoản phải hoàn tất **Phone Verification (`https://auth.openai.com/add-phone`)** để cấp Developer OAuth Token PKCE.

## 2. Quy trình tự động hóa xác thực số điện thoại OpenAI (`add-phone`)
Khi tự động hóa qua Playwright CDP trên profile GPMLogin:
1. **Khởi tạo OAuth Callback Server**: Gọi `GET http://127.0.0.1:20129/api/oauth/codex/start-callback-server` để lấy `authUrl`.
2. **Bắt mã Redirect Callback**: Lắng nghe request URL chứa `1455` và `code=` để forward về OmniRoute.
3. **Thao tác DOM tại `auth.openai.com/add-phone`**:
   - Mở dropdown quốc gia: Click `button[aria-haspopup="listbox"]`.
   - Chọn quốc gia theo mã ISO 2 ký tự: Click `[role="option"][id*="-option-{ISO}"]`.
   - Chọn channel SMS: Đảm bảo radio `input[type="radio"][value="sms"]` được checked.
   - Điền số điện thoại: Tách bỏ prefix quốc gia (ví dụ: `+1`, `+44`, `+54`...), điền số local vào `input[type="tel"]`.
   - Bấm `button[type="submit"]`.
   - Bắt lỗi từ chối số: Đọc `[role="alert"], [data-error]` ngay sau submit. Nếu OpenAI từ chối, lập tức gọi lệnh cancel hoàn tiền 100%.
   - Nhập OTP: Polling mã từ SMS API, điền vào `input[autocomplete="one-time-code"]` và submit.

## 3. Bản chất các dải số trên 5sim đối với OpenAI
- **Cơ chế giữ và hoàn tiền của 5sim**:
  - Khi mua số (`/v1/user/buy/activation/{country}/{operator}/openai`), 5sim ở trạng thái hold balance.
  - Nếu không có SMS, gọi `GET /v1/user/cancel/{order_id}` để hoàn lại 100% tiền ngay lập tức.
  - Chỉ bị trừ tiền khi có SMS gửi về hoặc hoàn tất (`/finish/{order_id}`).
- **Dải số siêu rẻ ($\le \$0.10$)**:
  - Các đầu số VoIP giá rẻ ($0.05 - $0.07$) như Anh (+447...), Argentina (+54...), Brazil (+55...) thường bị hệ thống bảo mật OpenAI âm thầm nuốt tin nhắn (Silent Drop). Gateway báo đã gửi nhưng SMS không chuyển tiếp tới SIM ảo. Tỷ lệ nhận code thực tế $< 5\%$.
- **Dải số tỷ lệ cao ($\ge 60\%$)**:
  - **Mỹ (USA virtual63)**: Giá ~$0.148 (khoảng 3.700đ), tỷ lệ nhận code ổn định 60-65%.
  - **SIM thật (Real Physical SIM)**: Tỷ lệ nhận code $\sim 99\%$.

## 4. Kiến trúc shop đại lý bán lẻ (như SumiStore / Bee Shop)
- **API Đấu Kho Hàng (`/api/tele-products`)**: Thường chỉ cung cấp các sản phẩm tài khoản số cố định (Gmail, acc ChatGPT đã ver phone sẵn, API key, phần mềm).
- **Tính năng Thuê SIM trên Bot Telegram**:
  - Thường là tính năng nội bộ chạy trong luồng Telegram bot (gọi sang SMSPool, 5sim, ViOTP).
  - Không mở REST API công khai ra web.
  - Tự động hóa tính năng này bắt buộc phải sử dụng **Telegram Userbot (Telethon / Pyrogram)** để giả lập thao tác bấm nút Inline Button trên chat bot, bóc tách số điện thoại và mã OTP trả về.
- **Tại sao shop bán số ảo Mỹ 1.000đ rẻ hơn giá web 5sim?**:
  - Shop nạp tiền gốc bằng Rúp Nga (RUB) với tỷ giá chiết khấu đại lý (~3.5 RUB $\approx$ 950đ - 1.000đ), trong khi tài khoản cá nhân nạp USD bị đội giá quy đổi.
  - Shop dùng làm sản phẩm phễu (loss leader) để hút người dùng nạp tiền vào bot.
