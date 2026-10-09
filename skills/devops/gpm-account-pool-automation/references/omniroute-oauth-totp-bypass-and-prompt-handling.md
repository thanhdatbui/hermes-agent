# Google OAuth 2FA TOTP Bypass & Prompt Decoupling in OmniRoute (`add_oauth_omniroute.py`)

## 1. Bối cảnh & Hiện tượng Kẹt Canary M10 (2026-09-05)
- Khi gọi OAuth cấp quyền Google Antigravity cho OmniRoute (`/api/oauth/antigravity/authorize`), Google kích hoạt bảo mật `challenge/dp` (Google Prompt đẩy về điện thoại Samsung S7).
- Hệ thống đã bật 2FA Google Authenticator cho dàn tài khoản và lưu Secret Key trong Excel (`master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`).
- **Nguyên nhân kẹt ban đầu:** Trong vòng lặp lắng nghe `automate_oauth_flow`, script cũ có đoạn code:
  ```python
  if "challenge" in current_url.lower():
      logger.warning("Profile dính Google Challenge / Checkpoint!")
      break
  ```
  Khi Google chuyển hướng sang `challenge/dp`, URL chứa `challenge` nhưng không khớp điều kiện `recovery email`, khiến script ngắt ngay lập tức và ném lỗi timeout `timeout_stuck`.

---

## 2. Giải pháp Chuẩn Hóa 3 Bước

### Bước 1: Mở rộng `CredentialLookup` đọc TOTP Secret
Đọc `totp_secret` từ cả 2 nguồn:
- `master_gmail_manager.xlsx`: Cột 5 (index 4 trong 0-indexed row `r[4]`).
- `gmail_clean_v2.xlsx`: Cột 4 (index 3 trong 0-indexed row `r[3]`).
- Lưu vào cache: `cls._cache[email] = {"password": pwd, "recovery": rec, "totp_secret": totp_secret}`.

### Bước 2: Thứ tự ưu tiên Selector trong Vòng lặp Playwright (CỰC KỲ QUAN TRỌNG)
Tránh xung đột click nhầm:

1. **Callback Catch:** Bắt URL chứa `/callback` và `code=` $\rightarrow$ lấy code và break.
2. **Account Chooser / Consent Screen:**
   - Account Chooser: Click `div[data-identifier="{email}"]` (không dùng selector text rộng `div:has-text` để tránh click nhầm header chip trên trang Consent).
   - Consent Screen: Tick `#select-all-scopes` $\rightarrow$ click các nút "Tiếp tục" / "Sign in" / "Continue" / "Allow".
3. **Màn hình nhập mã TOTP (`challenge/totp` hoặc `input#totpPin`):**
   - **BẮT BUỘC KIỂM TRA TRƯỚC NÚT "THỬ CÁCH KHÁC":** Trên trang `challenge/totp`, ở chân trang vẫn có link "Thử cách khác" (`Try another way`). Nếu check nút này trước, Playwright sẽ bấm vào đó và quay ngược lại trang `selection`!
   - **Chống lệch chu kỳ 30s (Clock Skew / Edge Window):**
     ```python
     if (time.time() % 30) >= 28:
         time.sleep(3)  # Đợi sang chu kỳ 30s mới để mã không hết hạn lúc submit
     totp_code = pyotp.TOTP(totp_secret.replace(" ", "").upper()).now()
     totp_inp.first.fill(totp_code)
     page.keyboard.press("Enter")
     ```
4. **Màn hình chọn phương thức xác minh (`challenge/selection`):**
   - Google gán data attribute chuẩn cho Authenticator là `div[data-challengetype="6"]`.
   - Kết hợp fallback: `li:has-text("Authenticator"), li:has-text("xác thực"), div[role="link"]:has-text("xác thực"), div[role="button"]:has-text("xác thực"), div:has-text("Google Authenticator")`.
   - **Lưu ý quan trọng (Pre-condition):** Nếu tài khoản chưa được kích hoạt 2FA Google Authenticator, trang `selection` CHỈ hiển thị 2 mục: (1) Nhấn Có trên điện thoại; (2) Dùng điện thoại nhận mã bảo mật 10 số offline. Hoàn toàn KHÔNG có dòng chọn Authenticator. Vì vậy, tài khoản bắt buộc phải có 2FA Authenticator trước khi chạy flow này.
5. **Màn hình Google Prompt (`challenge/dp` hoặc body chứa prompt điện thoại):**
   - Bắt URL `challenge/dp`, `challenge/ipp` hoặc body text chứa "samsung", "tap yes", "nhấn có".
   - **Google Text Update:** Google đổi text nút từ "Thử cách khác" sang **"Cách xác minh khác"** (hoặc "More ways to verify"). Selector BẮT BUỘC quét cả 2 biến thể trên `button`, `div[role="button"]`, `a`, `span`:
     ```python
     try_another = page.locator(
         'button:has-text("Cách xác minh khác"), button:has-text("Thử cách khác"), '
         'button:has-text("Try another way"), button:has-text("More ways to verify"), '
         'div[role="button"]:has-text("Cách xác minh khác"), div[role="button"]:has-text("Thử cách khác"), '
         'div[role="button"]:has-text("Try another way"), '
         'a:has-text("Cách xác minh khác"), a:has-text("Thử cách khác"), a:has-text("Try another way"), '
         'span:has-text("Cách xác minh khác"), span:has-text("Thử cách khác")'
     )
     if try_another.count() > 0 and try_another.first.is_visible():
         try_another.first.click()
     ```
6. **Recovery Email Challenge:** `div[data-challengetype="12"]` hoặc input `knowledge-preregistered-email-response`.
7. **Timeout nâng cấp:** Mặc định `--timeout 60` giây (thay vì 45s) để đảm bảo độ trễ tải trang qua proxy di động / MikroTik.

---

## 3. Tự Động Gán Proxy 1:1 & Sync Models Sau Khi Exchange
Khi `POST /api/oauth/antigravity/exchange` thành công:
1. Trích xuất port từ tên profile hoặc proxy string: `re.search(r'[-_:\s](\d{4,5})', profile_info['name'])`.
2. Tìm Proxy ID tương ứng trong `GET /api/settings/proxies`.
3. Gán proxy theo đúng scope `account`:
   ```http
   PUT /api/settings/proxies/assignments
   {"scope": "account", "scopeId": "<connection_id>", "proxyId": "<proxy_id>"}
   ```
4. Kích hoạt danh mục model:
   ```http
   POST /api/providers/<connection_id>/sync-models
   ```
