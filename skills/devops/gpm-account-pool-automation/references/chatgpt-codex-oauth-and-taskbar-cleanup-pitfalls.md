# ChatGPT / Codex OAuth Automation Pitfalls & Workarounds

## 1. Bản chất 2 Provider trên OmniRoute (Port 20129)
- **`chatgpt-web` (UI hiển thị: ChatGPT Web Plus/Pro)**:
  - Dùng Cookie `__Secure-next-auth.session-token` trích xuất từ GPM Browser sau khi login `chatgpt.com`.
  - Hỗ trợ tất cả tài khoản (Free, Plus, Pro).
  - Model hỗ trợ: `gpt-5.6-luna-free`, `gpt-5.6-luna-free-thinking`, và **map được cả dòng `gpt-5.6-sol` / `gpt-5.6-terra-high`**.
  - **Quota độc lập với Codex**: Khi Codex dính 503 (`reset after 700h`), Web session của chính tài khoản đó vẫn gọi `200 OK`.
  - Token sống bền nhiều ngày, không bị 401 sau vài tiếng nếu session trình duyệt còn duy trì.
- **`codex` (UI hiển thị: ChatGPT Web Codex)**:
  - Dùng OAuth Token (`access_token` + `refresh_token`) lấy qua callback `127.0.0.1:1455`.
  - Quota Free cạn rất nhanh khi dồn request review code -> Dễ dính `503 Unavailable (reset after 700h)`.
  - Nếu chỉ bốc tạm `accessToken` JWT từ `/api/auth/session` nạp vào mà không có `refreshToken`, token sẽ expired sau 1-2h.

## 2. Các Pitfalls cốt lõi khi tự động hóa Playwright CDP với Google SSO

### Pitfall 1: Click trượt trên Google Account Chooser
- **Hiện tượng**: Màn hình dừng ở `accounts.google.com/v3/signin/accountchooser`, Playwright click selector thông thường (`role=link`) nhưng Google không nhận event hoặc trượt.
- **Giải pháp chuẩn**:
  ```python
  # Định vị chính xác qua data-identifier chứa email
  loc = page.locator(f'div[data-identifier*="{email}"], div[role="link"]:has-text("{email}")').first
  box = loc.bounding_box()
  if box:
      page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
  ```

### Pitfall 2: Google Consent Screen ("Đăng nhập vào OpenAI")
- Sau khi chọn tài khoản, Google chuyển sang trang cấp quyền `signin/oauth/id` với nút "Tiếp tục".
- Selector nút tiếp tục có thể nằm trong Web Component hoặc button DOM con:
  ```python
  try:
      page.evaluate('''() => {
          const btns = Array.from(document.querySelectorAll('button'));
          const b = btns.find(x => (x.innerText||'').includes('Tiếp tục') || (x.innerText||'').includes('Continue'));
          if (b) b.click();
      }''')
  except Exception:
      pass
  ```

### Pitfall 3: Form Onboarding ChatGPT "How old are you?" (`/about-you`)
- **Triệu chứng**: Playwright `click()` vào `input[name="age"]` bị `TimeoutError: Locator.click: Timeout 30000ms exceeded` do `_typeableLabelTextPositioner` đè lên layer input.
- **Giải pháp chuẩn**:
  - Dùng `force=True` khi click hoặc focus:
  ```python
  age_inp = page.locator('input[name="age"]').first
  age_inp.click(force=True)
  page.keyboard.type(str(random.randint(22, 28)), delay=100)
  page.locator('button[type="submit"]').first.click()
  ```

### Pitfall 4: Treo hàng trăm tiến trình Chrome mồ côi làm nghẽn Taskbar (Taskbar badge 200+)
- **Nguyên nhân**: Script crash hoặc loop mở profile GPM mà không dọn `chrome.exe` qua psutil khi exception xảy ra.
- **Quy tắc dọn sạch an toàn (Tuyệt đối không kill nhầm Phone Farm)**:
  ```python
  import psutil
  for p in psutil.process_iter(['pid', 'name', 'exe']):
      try:
          exe = p.info.get('exe') or ''
          name = p.info.get('name') or ''
          # CHỈ kill chrome.exe thuộc thư mục gpm_browser, CẤM kill bừa bãi
          if 'chrome.exe' in name.lower() and 'gpm_browser' in exe.lower():
              p.kill()
      except Exception:
          pass
  ```
- **Kỷ luật điều phối**: Chạy tuần tự (`MAX_WORKERS = 1` hoặc tối đa 2 có bulkhead), xong acc nào gọi `stop` API và kiểm tra dọn sạch ngay trước khi mở profile tiếp theo.
