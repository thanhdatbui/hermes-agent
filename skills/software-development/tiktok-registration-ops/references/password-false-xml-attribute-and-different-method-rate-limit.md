# Pitfall password="false" trên Raw XML và Nhận diện Lỗi Rate-Limit Different Method trong TikTok Registration

Áp dụng cho `social_reg_v1.py` và các script automation đăng ký / đăng nhập TikTok qua ADB UI dump.

## 1. Pitfall: Substring 'password' trên raw XML dính thuộc tính password="false"

### Triệu chứng
Trong luồng `fill_email_and_next` hoặc các bước phân loại màn hình đăng ký / đăng nhập:
- Script fallback quét tìm từ khóa để xác định xem tài khoản đã đăng ký chưa (`reg_fallback = ["da co tai khoan", "email nay da co", "mat khau", "password"]`).
- Khi quét trực tiếp trên raw XML dump được strip accent: `flat_backup = strip_accents(xml_backup).lower()`.
- Mọi node `EditText` hoặc `TextView` thông thường trên Android UI Automator đều có thuộc tính `password="false"`.
- Do đó chuỗi `"password"` luôn xuất hiện trong raw XML dù màn hình hiện tại KHÔNG PHẢI màn hình nhập mật khẩu, dẫn đến false positive: script ngộ nhận là màn hình đã đăng ký (`registered, giu lai`) thay vì xử lý đăng ký tài khoản mới.

### Khắc phục chuẩn
1. **Tuyệt đối không quét raw XML cho từ khóa "password":**
   - Loại bỏ `"password"` khỏi danh sách từ khóa chuỗi trần (`reg_fallback`). Chỉ giữ lại các cụm từ ngữ cảnh người dùng như `"da co tai khoan"`, `"email nay da co"`, `"mat khau"`.
2. **Dùng bộ trích xuất text/desc chuyên biệt:**
   - Thay vì `strip_accents(raw_xml).lower()`, sử dụng `_tiktok_flat_xml(xml)` chỉ bóc tách các trường `text` và `content-desc` hiển thị cho người dùng.
3. **Kiểm tra thuộc tính password qua parser node:**
   - Dùng `nodes = list_edittext_nodes(xml)` để bóc tách danh sách `EditText`.
   - Kiểm tra `has_pw_field = any(n.get("password") for n in nodes)` (hoặc kiểm tra giá trị boolean loại trừ `"false"`).

---

## 2. Nhận diện lỗi Rate-Limit / Banner "Different Method"

### Triệu chứng
- TikTok xuất hiện banner thông báo lỗi: *"Please try again or log in with a different method."* (bản tiếng Việt: *"Vui lòng thử lại hoặc đăng nhập bằng một phương thức khác"*).
- Nếu không bắt trạng thái này:
  - `detect_after_continue` bỏ sót và tiếp tục chờ đợi hoặc nhầm lẫn màn hình.
  - `_post_auth_ui_state` không phân loại được, khiến `wait_login_success` chờ hết 30 giây timeout vô ích.
  - Vòng lặp `handle_post_auth_screens` tiếp tục thử lại mù quáng.

### Khắc phục chuẩn
1. **Trong `detect_after_continue`:**
   ```python
   if "different method" in flat or "phuong thuc khac" in flat:
       log("   ✗ detected: TikTok rate-limit / 'different method' error banner")
       return "error_different_method"
   ```
2. **Trong `_post_auth_ui_state`:**
   ```python
   if "different method" in flat or "phuong thuc khac" in flat:
       return "rate_limited"
   ```
3. **Fast-fail trong các vòng chờ:**
   - Bổ sung `"rate_limited"` vào tập trạng thái dừng sớm trong `wait_login_success` và `handle_post_auth_screens`:
   ```python
   if state in {"captcha", "google_relogin", "identity_verification", "terms_consent", "account_not_found", "rate_limited"}:
       _report_manual_auth_state(device_id, stt, state, "login_success")
       return False
   ```
