# OpenAI Onboarding / About-You Automation Pitfalls

## 1. Hiện tượng & Vấn đề
Khi tự động hóa đăng nhập Google OAuth vào ChatGPT-Web trên trình duyệt GPM / Playwright:
- Sau khi chọn tài khoản Google hoặc nhập xong email/mật khẩu, OpenAI có thể chuyển hướng về `https://auth.openai.com/about-you`.
- Nếu bot/script dừng lại ở đây và coi là "chưa hoàn thành" rồi nhả ra bắt user điền tay -> User sẽ cực kỳ khó chịu vì automation bị đứt gãy giữa chừng.
- **YÊU CẦU BẮT BUỘC**: PHẢI tự động hoàn tất 100% form onboarding này, cấm dừng lại viện cớ an toàn!

## 2. Các biến thể form About-You của OpenAI
OpenAI thường xuyên đổi cấu trúc DOM của màn hình này:
- **Dạng cũ**: Gồm 2 input: `input[name="name"]` và `input[name="age"]`.
- **Dạng mới (Auth v2)**: Đòi hỏi ngày sinh `birthday`:
  - `input[name="birthday"]`
  - `input[type="text"][placeholder*="YYYY" i]` (format `YYYY-MM-DD` hoặc `DD/MM/YYYY`)
  - `input[placeholder*="birth" i]`

## 3. Snippet tự động hóa chuẩn (Page Evaluate + Dispatch Event)
Dùng evaluate JavaScript trực tiếp trên trang để vượt qua mọi biến thể selector và kích hoạt React state:

```javascript
() => {
    // 1. Tự động điền Họ và tên nếu chưa có
    const nameInp = document.querySelector('input[name="name"], input[placeholder*="name" i]');
    if (nameInp && !nameInp.value) {
        nameInp.value = short_name;
        nameInp.dispatchEvent(new Event('input', { bubbles: true }));
        nameInp.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // 2. Tự động điền Ngày sinh / Tuổi (> 18 tuổi)
    const bdayInp = document.querySelector('input[name="birthday"], input[type="text"][placeholder*="YYYY" i], input[placeholder*="birth" i], input[name="age"]');
    if (bdayInp && !bdayInp.value) {
        const isYMD = bdayInp.getAttribute('placeholder')?.includes('YYYY') || bdayInp.getAttribute('name') === 'birthday';
        bdayInp.value = isYMD ? '2000-01-15' : '15/01/2000';
        bdayInp.dispatchEvent(new Event('input', { bubbles: true }));
        bdayInp.dispatchEvent(new Event('change', { bubbles: true }));
    }
}
```

Sau khi inject giá trị, chờ 1s rồi click submit:
```python
btn = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first
if btn.count() > 0 and btn.is_visible():
    btn.click()
    page.wait_for_timeout(6000)
```

Chờ tiếp tới khi URL đổi thành `https://chatgpt.com/` và không còn `auth` trong URL -> Trích xuất cookie session tươi ngay.
