# Gmail Check Live Guidelines & Pitfalls (checkmail.live)

## Quy chuẩn & Phương pháp kiểm tra Live Gmail
- Công cụ chuẩn: `checkmail.live` qua Playwright / Chrome CDP persistent context.
- Proxy bắt buộc: Mobile proxy farm `mobi1` (`http://test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`) kết hợp cờ `--disable-blink-features=AutomationControlled` để tự động vượt Cloudflare Turnstile sau 1-3s.

## Bẫy ngộ nhận On-Device Google Health (Incident 2026-09-12)
- Khi reg TikTok fail OTP ở bước 7c, on-device health check trên Android (`check_google_account_health_from_gmail`) chỉ phát hiện khi Google văng popup CAPTCHA/Relogin trên UI.
- Nếu tài khoản Google bị vô hiệu hóa/khóa ngầm ở backend, app Gmail không sync được thư nhưng cũng không hiện thông báo lỗi $\rightarrow$ script ngộ nhận `target_account_not_verified` (cho rằng Google còn LIVE và đổ lỗi cho TikTok không phát OTP).
- Thực tế kiểm tra qua `checkmail.live`: **16/17 mail fail OTP đều đã DIE (`[die]`)**.
- **Quy tắc:** BẮT BUỘC dùng `checkmail.live` làm nguồn đối soát sự sống của Gmail, TUYỆT ĐỐI CẤM dựa vào kết quả on-device health check để kết luận mail sống.
