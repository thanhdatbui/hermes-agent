# OmniRoute ChatGPT-Web Turnstile/Sentinel Challenge & 30-min Circuit Breaker

## Hiện tượng
- Lệnh gọi Advisor Sol (`python D:/Taadaa/tools/consult_advisor.py "<prompt>"`) bị trả về:
  `ADVISOR_UNAVAILABLE: TIMEOUT :: >45s`
- Hiện tượng lặp lại dù tiến trình OmniRoute trên cổng 20129 vẫn đang lắng nghe bình thường (`LISTENING`).

## Chẩn đoán & Bằng chứng thực tế
Đọc log runtime tại `C:/Users/Kibe/AppData/Roaming/omniroute/logs/omniroute-stdout.log`:
```text
[ERROR] [403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.
{"level":50,"service":"omniroute","tag":"TOKEN_REFRESH","msg":"🔴 Circuit breaker tripped for chatgpt-web: 5 consecutive failures. Blocked for 30min. Provider needs re-authentication."}
{"level":40,"service":"omniroute","tag":"TOKEN_REFRESH","msg":"⚡ Circuit breaker active for chatgpt-web, skipping refresh"}
```

## Cơ chế lỗi
1. **Cloudflare / OpenAI Sentinel Challenge:**
   - OpenAI siết bảo mật định kỳ đối với các web session, yêu cầu vượt qua Turnstile / Sentinel captcha.
2. **Cầu dao tự ngắt 30 phút của OmniRoute:**
   - Khi có 5 lần liên tiếp gặp lỗi 403 khi refresh token, OmniRoute kích hoạt cơ chế bảo vệ provider `chatgpt-web`: **Khóa toàn bộ pool trong 30 phút** để tránh bị Cloudflare đánh dấu spam/ban hàng loạt.
3. **Hiệu ứng Timeout ở Client:**
   - Trong thời gian 30 phút bị khóa, các request gửi đến route `gpt-web-sol` bị OmniRoute giữ chờ thử lại hoặc không nhận được streaming chunk nào, dẫn đến vượt quá ngưỡng an toàn `TIMEOUT_SECONDS = 45` của `consult_advisor.py`.

## Quy trình xử lý
- **Không suy diễn server chết hay port bị chiếm:** Kiểm tra ngay `omniroute-stdout.log` để xem circuit breaker có đang active không.
- **Thời gian chờ tự hồi phục:** Sau 30 phút kể từ lúc kích hoạt (thời gian ghi nhận trong log), circuit breaker sẽ mở lại để thử refresh token.
- **Nếu sau 30 phút vẫn kẹt:** Mở trình duyệt đăng nhập lại tài khoản trên chatgpt.com để giải captcha và cập nhật cookie mới.
