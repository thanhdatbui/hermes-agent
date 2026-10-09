# ChatGPT / OpenAI Onboarding & OAuth Automation trên GPM Browser

## 1. Ngữ cảnh & Triệu chứng lỗi thường gặp
Khi tự động hóa đăng nhập ChatGPT thông qua Google OAuth (`Continue with Google`) trên GPM-Browser:
1. **Kẹt ở màn hình Onboarding Tuổi (`auth.openai.com/about-you`)**:
   - Giao diện OpenAI hiện tại có **2 biến thể form** tùy theo ngôn ngữ/locale của trình duyệt:
     - **Tiếng Anh (`en`)**: Nhập trực tiếp số tuổi nguyên (Field `input[name="age"]`, `type="number"`).
     - **Tiếng Việt (`vi`)**: Hiển thị component `react-aria-DateField` gồm 3 ô riêng biệt: `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`.
   - **BẪY CHẾT NGƯỜI (Năm sinh 2026)**: Khi ở giao diện tiếng Việt, OpenAI tự động điền sẵn ngày hiện tại (ví dụ: `14/09/2026`). Nếu script không xóa sạch và thay đổi năm sinh, tuổi sẽ bằng 0 (chưa sinh ra / dưới 13 tuổi). OpenAI lập tức báo lỗi đỏ: *"Chúng tôi không thể tạo tài khoản với thông tin đó. Vui lòng thử lại"* và văng ra lỗi `token_exchange_failed`!
   - Bắt buộc phải click vào từng ô `day`, `month`, `year`, bấm `Control+A` và gõ năm sinh hợp lệ (`1996` – `2002`, tức 24–30 tuổi).
   - Element `input[name="age"]` có lớp phủ `<div class="_typeableLabelTextPositioner...">` nằm trong subtree `<label>` đè lên, khiến Playwright `locator.click()` bị chặn. Phải dùng `click(force=True)` hoặc `Control+A` khi focus.

2. **Kẹt chuyển hướng `Loading https://...` trong Page Title**:
   - Khi Google OAuth redirect về OpenAI hoặc ngược lại, Chromium trên proxy thỉnh thoảng bị dừng event loop: `page.url` vẫn ở URL cũ nhưng `page.title()` đã thành `Loading https://accounts.google.com/...` hoặc `Loading https://auth.openai.com/...`.
   - **Giải pháp**: Kiểm tra `if "Loading https://" in page.title(): page.goto(page.title().replace("Loading ", "").strip())`.

3. **Lỗi `Page.screenshot` treo do font chữ**:
   - Trên các trang web hiện đại như ChatGPT/OpenAI, gọi trực tiếp `page.screenshot(path=...)` có thể bị timeout 30000ms tại bước `waiting for fonts to load...`.
   - **Giải pháp**: Dùng CDP session trực tiếp `cdp_sess = context.new_cdp_session(page)` và gọi `cdp_sess.send('Page.captureScreenshot', {'format': 'png'})`, sau đó `base64.b64decode` lưu file. Tốc độ tức thì và không phụ thuộc vào font load.

4. **Tách biệt Quota giữa Codex và ChatGPT-Web trên OmniRoute (Cổng 20129)**:
   - **Codex OAuth**: Dùng pool developer token. Nếu tài khoản bị vắt kiệt quota tháng (`503 Unavailable - reset after 700h`), **phiên ChatGPT-Web (`session-token`) của CHÍNH tài khoản đó vẫn còn 100% quota (`200 OK`)**.
   - ChatGPT-Web trên OmniRoute (nhãn `ChatGPT Web (Plus/Pro)`) nhận cookie `__Secure-next-auth.session-token` của mọi tài khoản Free/Plus/Pro, hỗ trợ gọi được cả `gpt-5.6-terra-high`, `gpt-5.6-sol-high`, `gpt-5.6-sol-xhigh`.

5. **Tránh spam Taskbar & Concurrency an toàn**:
   - Chạy tối đa **3 workers** song song. Chạy 5+ workers cùng IP proxy di động sẽ kích hoạt WAF OpenAI trả về `token_exchange_failed` hoặc `error=undefined`.
   - Sau khi stop profile qua API (`GET /api/v3/profiles/stop/{id}`), kiểm tra `psutil` diệt các process `chrome.exe` có đường dẫn chứa `gpm_browser`, tuyệt đối không kill nhầm `xiaowei` của Phone Farm.

---

## 2. Quy trình xử lý Onboarding "About You" chuẩn xác (hỗ trợ cả Tiếng Anh & Tiếng Việt)

```python
def handle_about_you_onboarding(page, p_name, email):
    try:
        # 1. Điền Họ và tên nếu trống
        name_inp = page.locator('input[name="name"]').first
        if name_inp.count() > 0 and name_inp.is_visible():
            if not name_inp.input_value():
                def_name = p_name.split('@')[0].replace('-', ' ').strip() or email.split('@')[0]
                name_inp.fill(def_name)

        # 2. Dạng 1: Ô Age (Tiếng Anh/số nguyên)
        age_inp = page.locator('input[name="age"]').first
        if age_inp.count() > 0 and age_inp.is_visible():
            age_inp.click(force=True)
            page.keyboard.press("Control+A")
            page.keyboard.type(str(random.randint(22, 28)), delay=80)
            time.sleep(0.5)

        # 3. Dạng 2: Ngày sinh React-Aria DateField (Tiếng Việt)
        day_el = page.locator('div[data-type="day"]').first
        if day_el.count() > 0 and day_el.is_visible():
            day_el.click()
            page.keyboard.press("Control+A")
            page.keyboard.type(f"{random.randint(10, 28):02d}", delay=80)
            time.sleep(0.2)

            month_el = page.locator('div[data-type="month"]').first
            if month_el.count() > 0:
                month_el.click()
                page.keyboard.press("Control+A")
                page.keyboard.type(f"{random.randint(1, 12):02d}", delay=80)
                time.sleep(0.2)

            year_el = page.locator('div[data-type="year"]').first
            if year_el.count() > 0:
                year_el.click()
                # QUAN TRỌNG: Phải xóa số năm 2026 mặc định, gõ năm sinh 1996-2002
                page.keyboard.press("Control+A")
                page.keyboard.type(str(random.randint(1996, 2002)), delay=80)
                time.sleep(0.5)

        # 4. Bấm nút Submit (Continue / Tiếp tục)
        submit_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Tiếp tục")').first
        if submit_btn.count() > 0:
            submit_btn.click(force=True)
            return True
    except Exception as e:
        logger.warning(f"Lỗi form onboarding: {e}")
    return False
```

---

## 3. Chụp ảnh nghiệm thu không bị treo bằng CDP Session

```python
import base64

def capture_screenshot_cdp(context, page, output_path):
    cdp_sess = context.new_cdp_session(page)
    ss = cdp_sess.send('Page.captureScreenshot', {'format': 'png'})
    with open(output_path, 'wb') as f:
        f.write(base64.b64decode(ss['data']))
    return output_path
```
