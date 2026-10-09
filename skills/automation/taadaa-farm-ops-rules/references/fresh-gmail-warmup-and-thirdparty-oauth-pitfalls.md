# Fresh Gmail Warmup & Third-Party OAuth Pitfalls on Samsung S7

## 1. Cơ chế Warmup Fresh Gmail sau khi Reg
- **Nguyên lý cốt lõi:** Ngăn Google AI đánh cờ hộp thư ma (Ghost Account) bằng cách kích hoạt **Inbound Activity (Welcome / Confirmation Mail)**.
- **Hiện thực chuẩn:** Gọi `warmup_newsletter_services.py` ngay sau khi reg thành công trên S7 để tự động subscribe 4–5 tech newsletter uy tín (Cooperpress: Node Weekly, JavaScript Weekly, Ruby Weekly, Postgres Weekly).
- **Quy tắc đủ:** Newsletter warmup là **HOÀN TOÀN ĐỦ** cho giai đoạn ngâm ban đầu. KHÔNG cố nhồi thêm đăng ký các dịch vụ bên ngoài (ChatGPT, mạng xã hội) ngay khi vừa tạo xong.

## 2. Rào cản Third-Party OAuth (ChatGPT / OpenAI) trên Samsung S7 (Android 8.0)
- **Hệ điều hành:** Dàn Samsung S7 chạy Android 8.0.0 (API 26). App ChatGPT chính thức yêu cầu tối thiểu Android 9.0+ nên **không thể cài đặt app**.
- **Lỗi Intent Loop trên Chrome S7:**
  - Khi mở Chrome vào trang đăng nhập ChatGPT và chọn **"Continue with Google"**, Google Play Services trên Android 8.0 kích hoạt bottom sheet chọn tài khoản.
  - Tuy nhiên, sau khi chọn tài khoản vừa reg, intent callback bị chuyển hướng sai vào `com.android.settings/.Settings$UserAndAccountDashboardActivity` (màn hình cài đặt tài khoản của hệ điều hành) thay vì trả auth token về WebView/Chrome.
  - Đây là hạn chế cấu trúc của Google Play Services / WebView trên Android 8.0 cũ, không thể vượt qua bằng click tự động.

## 3. Quy tắc an toàn vận hành (Farm Safety)
1. **Fresh Gmail Cooldown:** Tuyệt đối không nạp Gmail vừa reg (<24h-48h) lên GPM trên máy tính vì nguy cơ bị Google gắn cờ thiết bị lạ và kích hoạt SMS verification (`challenge/iap`).
2. **Workflow chuẩn:**
   - Bước 1: Reg Gmail trên S7 + Newsletter Warmup tự động.
   - Bước 2: Ngâm tài khoản $\ge$ 24h - 48h trên chính máy S7 trong lúc chạy các tác vụ nuôi bình thường.
   - Bước 3: Sau khi ngâm đủ độ trust, đưa tài khoản lên GPM bật 2FA và liên kết các dịch vụ AI / ChatGPT bằng Chrome profile trên PC.
