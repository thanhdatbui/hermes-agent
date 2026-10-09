# ChatGPT Registration Canary & Email Submit Timeout Diagnostics

## Canary Execution Protocol
- Khi chạy canary test ChatGPT registration trên các máy S7 trong farm (ví dụ Máy 09 - `988627414444594c51`):
  - Luôn sử dụng runner có `DeviceContext` (pinned lock) để tránh va chạm với các batch runner khác.
  - Các script canary mẫu đặt tại `D:/Taadaa/run_canary_m<STT>.py`.
  - Luôn có cơ chế pull ảnh screencap nghiệm thu (`/sdcard/_canary_m<STT>.png` -> `D:/Taadaa/canary_chatgpt_m<STT>.png`) và teardown đưa thiết bị về HOME trước khi release lock.

## Triệu chứng `FAILED_AT_EMAIL_SUBMIT` (EMAIL_SUBMIT_TIMEOUT)
- **Mã lỗi:** `status: FAILED_AT_EMAIL_SUBMIT`, `reason_code: EMAIL_SUBMIT_TIMEOUT`.
- **Hiện tượng:** Runner nhập email xong và nhấn Submit/Continue nhưng sau timeout (~80s - 150s) UI vẫn không chuyển tiếp sang màn hình OTP hoặc đặt mật khẩu.
- **Nguyên nhân cốt lõi:**
  1. **Cloudflare / Arkose Captcha Challenge:** OpenAI hiển thị challenge Captcha (Cloudflare Turnstile hoặc Arkose puzzle) chặn tiếp tục.
  2. **IP / Proxy bị block / rate limit:** IP mạng của máy bị OpenAI gắn cờ (flag) dẫn đến việc click Submit bị treo hoặc loading vô tận.
  3. **Bàn phím ảo che mất nút Submit / UI không dispatch event:** Nếu chưa ẩn bàn phím ảo (`keyevent 111` hoặc tap ra ngoài), bàn phím có thể che khuất view hoặc việc tap submit không kích hoạt event submit trên webview.
  4. **Email đã tồn tại hoặc format bất thường:** Webview hiện lỗi inline đỏ (e.g. "Email not supported" hoặc "Too many requests") mà script không nhận diện qua text so khớp thông thường.

## Quy trình xử lý & kiểm tra UI Evidence
1. **Kiểm tra ảnh screencap nghiệm thu:** Mở ảnh `D:/Taadaa/canary_chatgpt_m<STT>.png` để xác định UI đang hiển thị thông báo lỗi hay challenge gì.
2. **Xử lý ẩn bàn phím:** Đảm bảo trước khi click Submit hoặc sau khi nhập email, gửi lệnh ẩn IME (`adb shell input keyevent 111` - Back/Escape).
3. **Đổi Proxy / Rotate IP:** Nếu lỗi do IP bị rate-limit, ngắt kết nối/đổi IP VPN trên máy trước khi chạy lại canary.
