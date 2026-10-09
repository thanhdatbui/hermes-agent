# Headless Direct Profile Provisioning & Challenge Selection TOTP Handling

## 1. Direct Headless Profile Provisioning (Khi GPM Desktop App port 19995 không mở)
Khi ứng dụng GPMLogin đóng hoặc port `19995` chưa bật, tuyệt đối không bị chặn luồng. Ta có thể khởi tạo profile GPM trực tiếp O(1) qua SQLite và thư mục persistent context:

1. **Tạo thư mục Profile chuẩn quy ước:**
   `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\M<mid> - <port> - <email>`
2. **Ghi nhận vào CSDL GPMLogin `profile_data.db`:**
   ```python
   import sqlite3, uuid, datetime

   conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
   c = conn.cursor()
   name = f'M{mid} - {port} - {email}'
   uid = str(uuid.uuid4())
   now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   jdata = f'{{"Name":"{name}","Proxy":"{raw_proxy}"}}'
   c.execute(
       'INSERT INTO Profiles (Id, Name, ProfilePath, JsonData, GroupId, CreatedAt) VALUES (?, ?, ?, ?, 1, ?)',
       (uid, name, name, jdata, now_str)
   )
   conn.commit()
   conn.close()
   ```
3. **Khởi chạy Playwright trực tiếp bằng GPM Chromium Core 142:**
   ```python
   CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
   ctx = p.chromium.launch_persistent_context(
       user_data_dir=profile_dir,
       executable_path=CHROME_EXE,
       proxy={"server": f"http://192.168.110.2:{singbox_port}"},
       locale="vi-VN",
       headless=False,
       args=[
           "--no-first-run",
           "--no-default-browser-check",
           "--disable-blink-features=AutomationControlled",
           "--lang=vi-VN,vi"
       ]
   )
   ```
   Cookies và session sẽ được Chromium ghi đè bền vững vào thư mục profile, GPMLogin khi mở lên sẽ nhận diện 100%.

## 2. Ưu tiên Google Authenticator (TOTP) trên màn hình Challenge Selection
Khi thiết bị S7 gặp trục trặc tạm thời ("Không thể kết nối với thiết bị ngay bây giờ"), Google sẽ hiển thị màn hình chọn phương thức xác minh (`challenge/selection`):
- Lựa chọn 1 (Google Prompt) bị disable/treo.
- Lựa chọn 2 (Google Authenticator) hiển thị ngay bên dưới.

**Giải pháp trong Playwright:**
Nếu tài khoản có `totp_secret`, ưu tiên click vào tùy chọn Authenticator trước khi fallback về Prompt/Security code:
```python
if "selection" in cur_url:
    if totp_secret:
        totp_opt = page.locator('div[data-challengetype="12"], div[data-challengetype="5"], li:has-text("Authenticator"), li:has-text("xác thực"), div[role="link"]:has-text("Authenticator"), div[role="link"]:has-text("xác thực")').first
        if totp_opt.count() > 0 and totp_opt.is_visible():
            logger.info(f"[M{mid:02d}] Chọn phương thức Google Authenticator (TOTP)...")
            totp_opt.click()
            time.sleep(3)
            continue
```

## 3. Quy tắc Fail-Fast cho SMS Checkpoint Loop
Nếu tài khoản bị Google điều hướng vào màn hình xác minh số điện thoại (`challenge/iap`):
- Bấm *"Thử cách khác"* (`Try another way`) tối đa 2 lần.
- Nếu Google vẫn giữ nguyên màn hình bắt nhập số điện thoại (Hard SMS Checkpoint) mà không đưa ra tùy chọn Prompt / TOTP:
  - **DỪNG NGAY (ABORT)** trong vòng <= 180s.
  - CẤM chạy vòng lặp click vô tận làm đốt hết budget iteration của subagent.
  - Đóng browser, ghi nhận vào `oauth_pipeline_status.json` (`wrong_password_or_checkpoint` hoặc `sms_checkpoint`) và chuyển sang tài khoản khác.

## 4. Phục hồi ADB Server bị rớt thiết bị
Khi phát hiện số lượng thiết bị trên `adb devices` giảm đột ngột (ví dụ từ 78 xuống 7 máy), KHÔNG kết luận máy vật lý hỏng/ngắt điện ngay:
- Chạy:
  ```bash
  adb kill-server
  adb devices
  ```
- ADB server sẽ quét lại toàn bộ USB Bus và nhận diện lại đầy đủ các thiết bị S7 đang kết nối.
