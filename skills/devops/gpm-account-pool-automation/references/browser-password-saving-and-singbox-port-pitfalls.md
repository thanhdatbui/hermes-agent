# Kích Hoạt Lưu Mật Khẩu / Tài Khoản Vào GPM Chromium & Pitfalls Cổng Proxy Singbox

## 1. Cơ Chế Lưu Mật Khẩu (Password Manager) Trên GPM Browser (Chromium Core 142)

### Vấn đề mặc định:
- Playwright khi khởi chạy persistent context (`launch_persistent_context`) tự động truyền tham số mặc định `--disable-save-password-bubble`. Cờ này chặn hoàn toàn bong bóng hỏi lưu mật khẩu của Chrome.
- Nếu không bật `credentials_enable_service` và `profile.password_manager_enabled` trong file `Preferences` của profile, Chromium sẽ không ghi nhận thông tin đăng nhập vào cơ sở dữ liệu `Default/Login Data`.
- Code tự động hóa thường có các locator bắt nút "Để sau", "Not now", "Hủy", "Skip". Nếu Google Web UI hiện prompt hỏi "Lưu thông tin đăng nhập" hoặc "Lưu mật khẩu", việc bấm nhầm vào các nút này sẽ bỏ qua việc lưu tài khoản.

### Giải pháp kỹ thuật 3 lớp:
1. **Thiết lập file `Preferences` trước khi launch Chromium**:
   ```python
   def enable_password_saving_in_profile(prof_dir: str):
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
2. **Gỡ cờ chặn của Playwright**:
   ```python
   ctx = p.chromium.launch_persistent_context(
       user_data_dir=prof_dir,
       executable_path=CHROME_EXE,
       proxy=proxy_dict,
       locale="vi-VN",
       headless=False,
       ignore_default_args=["--disable-save-password-bubble"],
       args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled", "--lang=vi-VN,vi"]
   )
   ```
3. **Ưu tiên click "Lưu" / "Save" khi gặp prompt của Google Web UI**:
   - Trước khi click các nút skip/bỏ qua, kiểm tra và click:
     `page.locator('button:has-text("Lưu"), button:has-text("Save"), button:has-text("Lưu mật khẩu"), button:has-text("Save password")')`.
   - Đối soát nghiệm thu: Kiểm tra SQLite `Default/Login Data`, bảng `logins` có bản ghi chứa `origin_url` và `username_value`.

---

## 2. Pitfall Tính Toán Cổng Proxy Singbox (`20000+`)

### Hiện tượng:
- Khi master sheet hoặc config đã lưu sẵn cổng dạng `20005` (dải `20000..20999`), công thức quy đổi cũ:
  ```python
  singbox_port = 20000 + (port - 10000) # (20005 - 10000) = 10005 -> 20000 + 10005 = 30005!
  ```
  khiến cổng bị đổi thành `30005` (cổng không tồn tại), gây lỗi `ERR_PROXY_CONNECTION_FAILED` hoặc treo timeout 600s.

### Quy tắc chuẩn:
- Nếu cổng đã nằm trong dải `20000 <= port < 21000`, giữ nguyên `singbox_port = port`.
- Nếu cổng dạng `5101..5140`, tính `singbox_port = 20000 + (port - 5100)`.
- Nếu cổng dạng `10001..10040`, tính `singbox_port = 20000 + (port - 10000)`.
- Nếu `port == 16002`, `singbox_port = 20000 + mid`.

---

## 3. Pitfall Màn Hình 502 / Callback Redirect Khi Chụp Ảnh Nghiệm Thu

### Hiện tượng:
- Sau khi hoàn tất xác thực OAuth Antigravity trên Google, Google redirect trình duyệt về `http://127.0.0.1:20129/callback?code=...`.
- Vì trình duyệt GPM đang chạy qua proxy 4G (Singbox/MobiProxy), proxy không thể định tuyến về `127.0.0.1` của host máy tính, dẫn đến Chromium hiển thị trang `This page isn’t working - 127.0.0.1 is currently unable to handle this request - HTTP ERROR 502`.
- Nếu chụp screenshot ở cuối script, ảnh sẽ lưu trang lỗi 502 này thay vì giao diện đăng nhập thành công.
- **Thực tế:** Script đã bắt được mã `code` qua sự kiện mạng `page.on("request")` trước khi redirect, và tài khoản/mật khẩu đã được lưu thành công vào `Login Data` từ bước trước đó. Để chứng minh lưu mật khẩu trực quan, cần mở `chrome://password-manager` thay vì chụp trang callback.
