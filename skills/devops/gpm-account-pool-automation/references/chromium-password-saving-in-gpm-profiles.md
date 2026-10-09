# Tự động lưu mật khẩu vào Chromium Profile trong GPMLogin

Tài liệu kỹ thuật hướng dẫn kích hoạt và tự động hóa cơ chế lưu mật khẩu của Chromium trong các profile GPMLogin khi đăng nhập Google/Gmail qua Playwright CDP.

---

## 1. Nguyên nhân Chromium không lưu mật khẩu mặc định qua Playwright
- Khi Playwright khởi chạy persistent context (`launch_persistent_context`), mặc định nó tự động chèn argument:
  `--disable-save-password-bubble`
- Ngoài ra, các profile mới tạo trong GPMLogin chưa được khởi tạo cờ trong file `Default/Preferences`:
  - `credentials_enable_service: None`
  - `profile.password_manager_enabled: None`
- Trong luồng đăng nhập Google, các dialog/prompt hỏi về bảo mật thường bị click nhầm vào "Not now / Để sau / Bỏ qua" thay vì chọn "Lưu / Save".

---

## 2. Giải pháp kỹ thuật hoàn chỉnh (Đã kiểm chứng)

### A. Cập nhật `Default/Preferences` của Profile trước khi mở trình duyệt
```python
import os
import json

def enable_password_saving_in_profile(prof_dir: str):
    """Bật cờ quản lý và lưu mật khẩu trong Preferences của Chromium profile."""
    pref_path = os.path.join(prof_dir, "Default", "Preferences")
    if not os.path.exists(pref_path):
        return
    try:
        with open(pref_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["credentials_enable_service"] = True
        if "profile" not in data or not isinstance(data["profile"], dict):
            data["profile"] = {}
        data["profile"]["password_manager_enabled"] = True
        with open(pref_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
```

### B. Gỡ cờ chặn của Playwright khi launch persistent context
Bổ sung `ignore_default_args=["--disable-save-password-bubble"]`:
```python
ctx = p.chromium.launch_persistent_context(
    user_data_dir=prof_dir,
    executable_path=CHROME_EXE,
    proxy={"server": f"http://192.168.110.2:{singbox_port}"},
    locale="vi-VN",
    headless=False,
    ignore_default_args=["--disable-save-password-bubble"],
    args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled", "--lang=vi-VN,vi"]
)
```

### C. Tự động click "Lưu / Save" trên giao diện Web
Trong vòng lặp xử lý các màn hình đăng nhập:
```python
# Ưu tiên bắt prompt lưu mật khẩu trước khi click 'Để sau'
try:
    save_pw = page.locator('button:has-text("Lưu"), button:has-text("Save"), button:has-text("Lưu mật khẩu"), button:has-text("Save password")').first
    if save_pw.count() > 0 and save_pw.is_visible():
        s_txt = save_pw.inner_text().strip().lower()
        if any(k in s_txt for k in ["lưu", "save"]) and not any(k in s_txt for k in ["để sau", "hủy", "not now", "không"]):
            logger.info(f"Phát hiện prompt lưu mật khẩu/tài khoản, click '{s_txt}'...")
            save_pw.click()
            time.sleep(3)
            continue
except Exception:
    pass
```

---

## 3. Nghiệm thu cơ sở dữ liệu `Login Data`
Sau khi đăng nhập thành công, mật khẩu được lưu vào file SQLite:
`<profile_dir>/Default/Login Data`

Truy vấn kiểm tra (không in plaintext password):
```sql
SELECT count(*), origin_url, username_value FROM logins;
```
- Nếu `count(*) > 0` và `username_value` trùng với email -> Đã lưu thành công 100%.
- Kiểm tra trực quan qua UI bằng URL: `chrome://password-manager/passwords`.

---

## 4. Pitfall gửi ảnh bằng chứng qua Telegram Gateway
- **Cấm tuyệt đối dùng backslash `\` trên Windows**: `D:\Taadaa\...` dễ bị lỗi ký tự escape (`\t`, `\n`) làm hỏng path.
- **Cấm đường dẫn có khoảng trắng (space)**: Đường dẫn chứa khoảng trắng (như `GPM auto`) khiến regex `extract_media` của Gateway bị cắt cụt.
- **Quy chuẩn**: Luôn dùng forward slash `/` và nếu thư mục nguồn có khoảng trắng thì copy tạm ảnh vào `C:/Users/Kibe/AppData/Local/hermes/image_cache/<name>.png` trước khi phát lệnh `MEDIA:`.
