# Kỹ Thuật Tự Động Lưu Mật Khẩu Vào GPM Chromium Browser (Password Manager Auto-Save)

Ngày ban hành: 13/09/2026.
Bối cảnh: Khi mở profile GPM qua Playwright CDP để tự động login Google/Gmail, Chromium mặc định không lưu tài khoản và mật khẩu vào Trình quản lý mật khẩu của trình duyệt (chrome://password-manager), khiến người dùng mở profile từ app GPMLogin phải đăng nhập lại hoặc không có danh sách mật khẩu đã lưu.

---

## 1. NGUYÊN NHÂN GỐC RỄ
1. **Playwright default flags chặn bong bóng lưu mật khẩu:**
   Playwright Chromium persistent context mặc định truyền flag `--disable-save-password-bubble`, làm ẩn hoàn toàn UI hỏi lưu mật khẩu của trình duyệt.
2. **Thiếu cấu hình Preferences trong profile GPM:**
   File `Default/Preferences` trong profile GPM mặc định không có hoặc tắt các cờ `credentials_enable_service` và `profile.password_manager_enabled`.
3. **Logic dismiss popup quá hung hãn:**
   Các handler trong bot thường tìm và click ngay các nút "Để sau / Not now / Skip / Hủy", vô tình tắt mất dialog/prompt xác nhận lưu thông tin tài khoản của Google/Chromium.
4. **Lỗi tính sai Singbox port cho proxy dải 20000+:**
   Khi port lấy từ database/sheet đã là port Singbox (20000+), logic cũ `20000 + (port - 10000)` cộng dồn sai thành port 30005 gây timeout proxy.

---

## 2. QUY TRÌNH & GIẢI PHÁP CHUẨN

### Bước 1: Kích hoạt Password Saving trong Profile Preferences
Trước khi khởi chạy Playwright context, đọc và ghi file `Default/Preferences` của profile:
```python
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
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Không thể cập nhật Preferences: {e}")
```

### Bước 2: Gỡ cờ chặn của Playwright
Khi gọi `launch_persistent_context`:
```python
context = p.chromium.launch_persistent_context(
    user_data_dir=prof_dir,
    executable_path=CHROME_EXE,
    proxy=proxy_config,
    locale="vi-VN",
    headless=False,
    ignore_default_args=["--disable-save-password-bubble"],  # BẮT BUỘC
    args=[
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--lang=vi-VN,vi"
    ]
)
```

### Bước 3: Ưu tiên click Lưu / Save trước khi Dismiss
Trong vòng lặp xử lý popup sau khi điền email & mật khẩu:
```python
# Ưu tiên bắt các nút Lưu / Save mật khẩu
save_btns = page.locator('button:has-text("Lưu"), button:has-text("Save"), button:has-text("Lưu mật khẩu"), button:has-text("Save password")')
if save_btns.count() > 0 and save_btns.first.is_visible():
    s_txt = save_btns.first.inner_text().strip().lower()
    if any(k in s_txt for k in ["lưu", "save"]) and not any(k in s_txt for k in ["để sau", "hủy", "not now", "không"]):
        logger.info(f"Phát hiện prompt lưu mật khẩu, click '{s_txt}'...")
        save_btns.first.click()
        time.sleep(3)
        continue
```

### Bước 4: Sửa nhánh nhận diện Singbox Port
```python
if acc.get("singbox_port"):
    singbox_port = acc["singbox_port"]
elif port and 20000 <= port < 21000:
    singbox_port = port  # Giữ nguyên port đã thuộc dải 20000+
elif port == 16002:
    singbox_port = 20000 + mid
elif port and 5000 < port < 6000:
    singbox_port = 20000 + (port - 5100)
elif port and 10000 <= port < 11000:
    singbox_port = 20000 + (port - 10000)
else:
    singbox_port = 20000 + mid
```

---

## 3. NGHIỆM THU (VERIFICATION)
1. **Kiểm tra cơ sở dữ liệu Login Data:**
   Truy vấn SQLite `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/<profile_path>/Default/Login Data`:
   ```sql
   SELECT count(*), origin_url, username_value FROM logins;
   ```
   Xác nhận có bản ghi `accounts.google.com` và email tương ứng.
2. **Kiểm tra trực quan bằng hình ảnh:**
   Mở `chrome://password-manager` trên profile đó và chụp ảnh screenshot nghiệm thu.
