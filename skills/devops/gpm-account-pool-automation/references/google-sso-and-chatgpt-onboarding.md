# Google SSO Account Chooser & ChatGPT Onboarding Playbook

## 1. Google Account Chooser Selector & Pointer Event Trap
- **DOM Trap**: Google SSO Chooser (`accounts.google.com/v3/signin/accountchooser`) không sử dụng thẻ `<button>` tiêu chuẩn cho từng account mà bọc trong `div[role="link"][data-identifier*="@gmail.com"]`.
- **Synthetic Click Issue**: Lệnh `locator.click()` thông thường có thể bị nuốt bởi custom event listener của Google.
- **Giải pháp tối ưu**: Định vị bounding box và click bằng chuột vật lý:
  ```python
  acc_btn = page.locator(f'div[role="link"][data-identifier*="{email}"], div[role="link"]:has-text("{email}")').first
  if acc_btn.count() == 0:
      acc_btn = page.locator('div[role="link"][data-identifier*="@gmail.com"]').first

  if acc_btn.count() > 0:
      box = acc_btn.bounding_box()
      if box:
          page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
  ```

## 2. ChatGPT Onboarding "Bạn bao nhiêu tuổi?" (`auth.openai.com/about-you`)
- **Pointer Event Interception**: Trường nhập tuổi (`input[name="age"]`) bị nhãn nổi (`div._typeableLabelTextPositioner`) đè lên trên layer z-index, khiến click thường của Playwright bị Timeout 30s với lỗi `subtree intercepts pointer events`.
- **Giải pháp**: Bắt buộc dùng `force=True` khi click và submit:
  ```python
  age_inp = page.locator('input[name="age"]').first
  if age_inp.count() > 0 and age_inp.is_visible():
      age_inp.click(force=True)
      time.sleep(0.3)
      page.keyboard.type(str(random.randint(22, 28)), delay=100)
      time.sleep(0.5)
      page.locator('button[type="submit"]').first.click(force=True)
  ```

## 3. Kiểm tra Google Session O(1) qua SQLite Cookies
- Trước khi khởi động trình duyệt tốn CPU/RAM, có thể kiểm tra trực tiếp database cookie tại `<profile_path>/Default/Network/Cookies`:
  ```python
  conn = sqlite3.connect(cookie_db)
  c = conn.cursor()
  c.execute('SELECT COUNT(*) FROM cookies WHERE host_key LIKE "%google%" AND name = "SID"')
  has_sid = c.fetchone()[0] > 0
  conn.close()
  ```
- Nếu có cookie `SID`, phiên Google vẫn còn sống. Tránh nhầm lẫn lỗi SSO tương tác DOM thành "tài khoản bị văng session".

## 4. Dọn dẹp tiến trình Chrome mồ côi
- Khi luồng bị timeout hoặc đứt gãy kết nối CDP, tiến trình `chrome.exe` có thể không được đóng sạch:
  ```cmd
  taskkill /F /IM chrome.exe /FI "USERNAME eq Kibe"
  ```
