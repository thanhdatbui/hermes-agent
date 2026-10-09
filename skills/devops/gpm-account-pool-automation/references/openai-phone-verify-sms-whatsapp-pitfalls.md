# OpenAI Phone Verification via SMS Automation & Pitfalls

## 1. Bản chất luồng Verify Phone cho Codex OAuth
- Khi tài khoản Google/ChatGPT chưa liên kết SĐT chạy qua OAuth Codex (`auth.openai.com/oauth/authorize`), OpenAI bắt buộc chuyển hướng sang `auth.openai.com/add-phone`.
- Luồng này kiểm tra chặt chẽ tính hợp lệ và loại số điện thoại (VoIP/Virtual vs Physical Carrier).

## 2. Các cạm bẫy chí mạng (Pitfalls) đã gặp

### Pitfall 1: OpenAI âm thầm chuyển sang WhatsApp (Silent WhatsApp Switch)
- **Triệu chứng:** Khi điền số điện thoại ảo (Virtual) từ 5sim/các web thuê SIM rẻ và bấm nút **"Tiếp tục"**, OpenAI trả về HTTP 400 ngầm từ `POST /api/accounts/add-phone/send` và tự động chuyển radio button sang **WhatsApp** kèm cảnh báo:
  > *"Chúng tôi không thể gửi tin nhắn SMS đến số điện thoại này nên đã chuyển sang WhatsApp. Tiếp tục để gửi mã xác minh qua WhatsApp."*
- **Nguyên nhân:** OpenAI phát hiện đầu số là VoIP/Virtual nên từ chối gửi SMS viễn thông.
- **Hậu quả nếu xử lý sai:** Script tưởng đã gửi SMS thành công và treo polling OTP 60s - 120s vô ích. 5sim không có WhatsApp nên không bao giờ nhận được mã.
- **Giải pháp bắt buộc (Fail-Fast):**
  Ngay sau khi bấm submit số điện thoại, kiểm tra DOM ngay trong 1-2 giây:
  ```python
  # Nếu phát hiện switch sang whatsapp hoặc có thông báo lỗi
  page_text = page.evaluate("() => document.body.innerText")
  if "chuyển sang WhatsApp" in page_text or "WhatsApp" in page_text and page.locator('input[value="whatsapp"]').is_checked():
      print("[!] OpenAI từ chối gửi SMS (bắt chuyển WhatsApp). HỦY SỐ NGAY LẬP TỨC!")
      cancel_order(order_id)
      # Reset form để thử số khác
  ```

### Pitfall 2: Rate Limit "Yêu cầu xác minh quá nhiều lần"
- **Triệu chứng:** Sau khi thử liên tục 10 - 20 số ảo thất bại, tài khoản sẽ bị OpenAI khóa cổng add-phone với thông báo:
  > *"Bạn đã yêu cầu xác minh số điện thoại quá nhiều lần. Vui lòng thử lại sau."*
- **Bài học:** Không được spam thử mù quáng các đầu số ảo cùng một dải trên 1 profile. Nếu sau 3 - 5 số bị từ chối gửi SMS, phải dừng ngay hoặc đổi sang Physical SIM sạch.

### Pitfall 3: Playwright Screenshot bị treo (Font Load Hang) trên trang Auth OpenAI
- **Triệu chứng:** Gọi `page.screenshot(path=...)` trên `auth.openai.com` bị treo cứng vượt quá timeout 30s (`TimeoutError: Page.screenshot: Timeout 30000ms exceeded ... waiting for fonts to load...`).
- **Khắc phục:**
  - Không gọi `page.screenshot()` thông thường trên các trang Cloudflare/Auth nặng font.
  - Sử dụng giải pháp render canvas HTML trực tiếp hoặc inject `html2canvas`:
    ```javascript
    const canvas = await window.html2canvas(document.body);
    return canvas.toDataURL("image/png");
    ```
  - Hoặc gửi lệnh CDP trực tiếp: `cdp_client.send("Page.captureScreenshot")` với `animations: "disabled"`.

## 3. Kiến thức về 5sim & Thị trường SIM
- **Cổng thanh toán 5sim hiện tại:** Không còn cổng Rúp nội địa Nga (Qiwi, YooMoney...). Mọi cổng nạp công khai đều quy đổi qua USD (Crypto USDT 1:1, thẻ quốc tế, Alipay).
- **Phân khúc Virtual Numbers (< $0.16):** Tỷ lệ nhận SMS trực tiếp từ OpenAI rất thấp (< 2%) do các gateway VoIP phổ biến (+447, +54, +55) đều bị OpenAI ép sang WhatsApp.
- **Physical SIM (SIM thật):** Đối với OpenAI/ChatGPT Developer OAuth, các số Physical (Real SIM như gói 7k bên đại lý hoặc SMSPool/ViOTP) mới đảm bảo nhận mã SMS trong 5 - 10 giây.
