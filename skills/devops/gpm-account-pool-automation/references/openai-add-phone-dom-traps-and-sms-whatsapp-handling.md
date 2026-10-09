# OpenAI Phone Verification Automation: DOM Traps & SMS vs WhatsApp Handling

## 1. Bản chất của OpenAI `add-phone` trong luồng OAuth Codex CLI

Khi tài khoản ChatGPT/Google được cấp quyền OAuth cho Codex CLI (`auth.openai.com`), OpenAI bắt buộc bước `add-phone` (xác thực số điện thoại).

### Bẫy DOM số 1: React Controlled Component & Hidden Native Select
- Trên giao diện `auth.openai.com/add-phone`, nút chọn quốc gia bên ngoài là một button giả lập (`button[aria-haspopup="listbox"]` thuộc React Aria).
- **Cạm bẫy:** Bên dưới form có một thẻ `<select>` ngầm (native `<select>`) và một `<input type="hidden" name="phoneNumber">`.
- Nếu chỉ click nút giả lập hoặc dùng Playwright gõ chữ vào popup mà **không cập nhật thẻ `<select>` ngầm**, giá trị submit thực tế gửi lên backend OpenAI vẫn bị neo cứng vào quốc gia mặc định (ví dụ `US (+1)`).
- Hậu quả: Số điện thoại nước ngoài (ví dụ Philippines `+63`, Campuchia `+855`) bị ghép thành mã vùng Mỹ `+198...` dẫn đến lỗi `Số điện thoại không hợp lệ`.
- **Cách xử lý đúng trong Playwright:**
```javascript
// Cập nhật đồng bộ trực tiếp thẻ select ngầm và bắn event 'change'
page.evaluate((targetIso) => {
    const sel = document.querySelector("select");
    if (sel) {
        sel.value = targetIso; // 'PH', 'KH', 'GR', v.v.
        sel.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const smsRadio = document.querySelector('input[type="radio"][value="sms"]');
    if (smsRadio) smsRadio.click();
}, iso);
```

---

## 2. Bẫy DOM số 2: Phản hồi "Chuyển sang WhatsApp" (Silent VoIP Rejection)

### Hiện tượng
Khi submit số điện thoại ảo (Virtual/VoIP rẻ tiền từ 5sim, ViOTP...), OpenAI gọi API:
`POST https://auth.openai.com/api/accounts/add-phone/send` -> Trả về `HTTP 400 Bad Request`.
Trên giao diện xuất hiện dòng chữ:
> *"Chúng tôi không thể gửi tin nhắn SMS đến số điện thoại này nên đã chuyển sang WhatsApp. Tiếp tục để gửi mã xác minh qua WhatsApp."*

### Sai lầm chết người của Agent
- Agent không chụp ảnh màn hình, không kiểm tra thông báo này.
- OpenAI **CHƯA HỀ BẮN TIN NHẮN SMS**, mà nó chỉ hiện cảnh báo yêu cầu bấm tiếp để gửi vào ứng dụng WhatsApp.
- Agent lầm tưởng đã gửi SMS nên ngồi đợi polling SMS suốt 1-2 phút.
- Hậu quả: Thử liên tục các số ảo bị ép qua WhatsApp khiến tài khoản bị OpenAI gắn cờ rate-limit:
  *"Bạn đã yêu cầu xác minh số điện thoại quá nhiều lần. Vui lòng thử lại sau."*

### Xử lý chuẩn (Fail-Fast trong 2 giây)
Ngay sau khi click Submit:
```python
page.wait_for_timeout(2500)
body_text = page.inner_text("body").lower()

if "whatsapp" in body_text or "không thể gửi tin nhắn sms" in body_text:
    print("[!] Số bị OpenAI ép chuyển sang WhatsApp -> HỦY SỐ NGAY LẬP TỨC (hoàn tiền)")
    cancel_5sim_order(order_id)
    # Reset form và đổi số khác ngay, TUYỆT ĐỐI KHÔNG CHỜ SMS!
elif "nhập mã xác minh" in body_text or "kiểm tra điện thoại" in body_text:
    print("[+] OpenAI đã chấp nhận gửi SMS! Mới bắt đầu đợi mã OTP tối đa 120s...")
```

---

## 3. Quy chuẩn chụp ảnh nghiệm thu (Visual Heartbeat Checklist)

Tuân thủ nghiêm ngặt quy tắc `MAX BLIND STEPS = 1`:
1. **Checkpoint 1 (Pre-Submit):** Sau khi chọn quốc gia và điền số vào `input[type="tel"]`, chụp full-screen xác nhận số và mã vùng đã khớp trước khi bấm nút Submit.
2. **Checkpoint 2 (Post-Submit):** Bấm submit xong, chụp ngay toàn bộ màn hình kết quả phản hồi trong vòng <= 3 giây.
3. **Chụp full-screen bằng canvas khi Playwright screenshot bị kẹt font:**
   Trang `auth.openai.com` đôi khi load webfont ngoài khiến `page.screenshot()` của Playwright bị timeout. Giải pháp render canvas độc lập:
```javascript
const canvas = await window.html2canvas(document.body);
return canvas.toDataURL("image/png");
```
4. **Giới hạn an toàn:** Nếu thất bại 3 lần liên tiếp trên 1 tài khoản, dừng ngay lập tức để tránh làm cháy tài khoản (Rate limit).
