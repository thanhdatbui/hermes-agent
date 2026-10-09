# Captcha Solving Architecture, reCAPTCHA Enterprise & Automation Services

## 1. Bản chất dịch vụ giải Captcha (Human vs AI vs Token Bypass)

| Tiêu chí | Dịch vụ truyền thống (2Captcha cũ, MegaTypers) | Dịch vụ AI hiện đại (CapSolver, YesCaptcha, EzCaptcha) |
| :--- | :--- | :--- |
| **Cơ chế** | Thuê nhân công gõ tay (Ấn Độ, Pakistan, Nga, VN) | Cụm AI thị giác (Computer Vision) + GPU Server |
| **Tốc độ** | 15 – 30 giây / lần | 1 – 3 giây / lần |
| **Chi phí** | Đắt ($2.99 / 1.000 requests) | Rất rẻ ($0.60 – $1.20 / 1.000 requests; ~15đ – 30đ / lần) |
| **Cơ chế trừ tiền** | Trừ theo lượt | Trừ theo số dư nạp trước (Prepaid), giải thành công mới trừ, không hết hạn credit |

---

## 2. Vì sao LLM tổng quát (Gemini / Claude / GPT) không tự giải được reCAPTCHA?

Khi tự động hóa qua browser, nhiều người nhầm tưởng "AI của agent nhìn ảnh rồi tự click là giải được". Điều này thất bại trên các hệ thống Anti-Bot hiện đại (Google reCAPTCHA Enterprise, Cloudflare Turnstile, hCaptcha Enterprise) vì 3 rào cản kỹ thuật:

### Rào cản 1: Model chuyên sâu (Specialized Vision) vs Model tổng quát (General LLM)
* **General LLM:** Huấn luyện đa năng, context lớn, xử lý chậm (vài giây), nhận diện chữ/hình méo mó, xoay góc hoặc noise filter dễ bị sai lệch.
* **Solver AI (CapSolver/YesCaptcha):** Sử dụng các model gọn nhẹ (YOLO, ResNet, Vision Transformer) được fine-tune trên hàng chục triệu mẫu captcha thực tế. Thời gian inference chỉ mất 0.05s, tỷ lệ chính xác gần như tuyệt đối trên các mẫu biến dạng cao.

### Rào cản 2: Đánh giá điểm rủi ro hành vi (Behavioral Risk Score)
* Google reCAPTCHA Enterprise không chỉ là câu đố hình ảnh, mà đo lường liên tục các thông số hành vi:
  * **Động học chuột:** Đường cong Bezier, gia tốc di chuột, độ rung tay tự nhiên của người thật. Tool tự động click thẳng vào tọa độ sẽ bị Google gán `score = 0.1` (Bot).
  * **Vân tay trình duyệt (Fingerprint):** Canvas hash, WebGL, AudioContext, TCP/IP & HTTP/2 TLS fingerprint (JA3/JA4).
  * Khi bị nghi ngờ, Google sẽ bắt giải captcha liên tục 5-10 vòng mà không bao giờ nhả kết quả ("Vui lòng thử lại sau").

### Rào cản 3: Cơ chế Token Bypass (Cốt lõi của dịch vụ Captcha)
* Dịch vụ giải captcha không click trực tiếp trên canvas của client.
* Server của dịch vụ mô phỏng một môi trường trình duyệt hoàn chỉnh với fingerprint sạch, vượt qua bộ lọc của Google và lấy về **chuỗi chữ ký token mã hóa**:
  `g-recaptcha-response: 03AFcWeA6...`
* Script automation chỉ cần inject chuỗi token này vào thẻ ẩn `textarea[name="g-recaptcha-response"]` hoặc submit payload trực tiếp để server đích chấp nhận mà không cần hiển thị khung ảnh giải đố.

---

## 3. Hai phương án tích hợp Captcha Solver vào GPM Browser Pool

### Phương án A: Cài Extension tự động vào Profile (Khuyên dùng cho UI/OAuth)
* **Ưu điểm:** Extension chạy trực tiếp trong ngữ cảnh trang, tự can thiệp vào DOM, tự giải và click trên canvas thật mà không làm gãy session hay fingerprint của profile.
* **Cách triển khai:**
  1. Tải bản zip/crx của CapSolver Extension hoặc 2Captcha Extension.
  2. Nạp vào mục Extensions trong GPM Local API hoặc đặt trong thư mục extension dùng chung.
  3. Cấu hình sẵn API Key trong file `config.json` của extension.
  4. Mọi thử thách reCAPTCHA / hCaptcha / Cloudflare tự động được giải ngầm.

### Phương án B: Tích hợp qua REST API / Playwright (Khuyên dùng cho API / Headless)
* **Quy trình:**
  1. Script đọc `sitekey` từ thẻ HTML (`[data-sitekey]` hoặc script render reCAPTCHA) và `page_url`.
  2. Gửi request `POST https://api.capsolver.com/createTask`:
     ```json
     {
       "clientKey": "CAP-...",
       "task": {
         "type": "ReCaptchaV2EnterpriseTaskProxyless",
         "websiteURL": "https://www.facebook.com/...",
         "websiteKey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
       }
     }
     ```
  3. Poll `POST https://api.capsolver.com/getTaskResult` đến khi trạng thái `ready`.
  4. Inject `token` nhận được vào DOM:
     ```python
     page.evaluate(f'''() => {{
         document.getElementById("g-recaptcha-response").innerHTML = "{token}";
         if (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) {{
             // Kích hoạt callback nếu có
         }}
     }}''')
     ```
