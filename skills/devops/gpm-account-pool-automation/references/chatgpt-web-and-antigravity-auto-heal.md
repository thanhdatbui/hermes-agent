# Tự Động Hồi Sinh Session ChatGPT-Web & Antigravity OAuth Qua GPM

Quy trình tự động hóa cứu vớt session cho watchdog định kỳ (`cron_chatgpt_web_pool_watchdog.py`) hoặc chạy ad-hoc khi tài khoản bị văng session trên OmniRoute (`:20129`).

---

## 1. Bản Chất & Thử Thách Kỹ Thuật

### A. ChatGPT-Web
1. **Direct Google OAuth Bypass**:
   - Thay vì bấm qua giao diện `chatgpt.com` (dễ bị kẹt bởi nút "Đăng nhập" render giả hoặc modal cookie chặn click), điều hướng trực tiếp bằng URL:
     ```text
     https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true
     ```
2. **Google Account Chooser**:
   - Nếu profile đã có session Google: click trực tiếp vào dòng email (`page.get_by_text(email)` hoặc `[data-identifier="{email}"]`).
3. **Google Sign-in Identifier**:
   - Input nhập email trên Google là `input[name="identifier"]` hoặc `#identifierId` (type="text", KHÔNG PHẢI `type="email"`).
4. **TOTP 2FA**:
   - Tự động đọc secret key từ `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Sinh mã 6 số qua `pyotp.TOTP(totp_key).now()`, điền vào `#totpPin` hoặc `input[type="tel"]` và bấm Next.
5. **OpenAI Onboarding Form (`https://auth.openai.com/about-you`)**:
   - Form yêu cầu:
     + `input[name="name"]`: Điền họ tên (VD: "Quynh Le").
     + `input[name="age"]` (type="number"): **Điền TUỔI** (VD: "24"), KHÔNG PHẢI ngày sinh.
     + Click `button[type="submit"]` ("Tiếp tục").
   - Sau bước này, trang sẽ redirect về `https://chatgpt.com` và phát sinh 30+ cookies session hợp lệ.

---

## 2. Antigravity OAuth Flow Qua GPM

1. **Lấy Authorize URL**:
   - Gọi `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http%3A%2F%2F127.0.0.1%3A20129%2Fcallback`
   - Nhận về `authUrl`, `codeVerifier`, `state`.
2. **Lắng nghe URL / Network trên Playwright**:
   - Điều hướng `page.goto(authUrl)`.
   - Lắng nghe sự kiện `request`/`response` hoặc kiểm tra URL chứa `/callback?code=...`.
   - Xử lý Account Chooser và Consent screen ("Cho phép" / "Tiếp tục").
3. **Exchange Code Lấy Refresh Token**:
   - Gửi `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange` với payload:
     ```json
     {
       "code": captured_code,
       "redirectUri": "http://127.0.0.1:20129/callback",
       "codeVerifier": code_verifier,
       "state": state
     }
     ```
   - Cập nhật connection antigravity sống lại và gán proxy tương ứng theo port.

---

## 3. Codex OAuth & Tự Động Phục Hồi (Auto-Heal 3 Pool)

### A. Tích hợp Codex vào Watchdog Giám sát Sức khỏe (`cron_chatgpt_web_pool_watchdog.py`)
Watchdog quét định kỳ đồng thời 3 provider: `chatgpt-web`, `antigravity`, và `codex`:
1. **Auto-Heal Toggled-Off Connection:**
   - Nếu connection có `testStatus == 'active'` nhưng `isActive == False` (bị tắt toggle giao diện hoặc do auto-failover):
   - Tự động bật lại qua SQLite mà không cần mở profile GPM:
     ```python
     conn = sqlite3.connect(r"C:\Users\Kibe\.omniroute\storage.sqlite")
     cur = conn.cursor()
     cur.execute("UPDATE provider_connections SET is_active=1 WHERE id=?", (cid,))
     conn.commit()
     ```
2. **Quy tắc Refresh Token Codex:**
   - `POST /api/providers/{id}/refresh-token` KHÔNG hỗ trợ Codex (trả về `Manual token refresh not supported for provider codex`).
   - Khi token Codex bị lỗi 401 (`Token invalid or revoked`): **BẮT BUỘC** phải chạy lại luồng OAuth hoàn chỉnh (`start-callback-server` + CDP GPM) để cấp quyền mới, không được gọi API refresh đơn lẻ.
3. **Báo cáo chuẩn Markdown Farm (CẤM dùng raw HTML):**
   ```text
   🤖 [POOL HEALER] BÁO CÁO SỨC KHỎE
   • ChatGPT-Web: 16/21 ACTIVE
   • Antigravity: 114/121 ACTIVE
   • Codex: 13/18 ACTIVE
   ```

---

## 4. OmniRoute Proxy Assignment API & Verification

Để gán đúng proxy 1-1 cho Connection (ChatGPT-Web, Codex, Antigravity):
1. **Tạo Proxy trong Registry (nếu chưa có):**
   ```python
   # POST http://127.0.0.1:20129/api/settings/proxies
   payload = {
       "name": f"Proxy {host}:{port}",
       "type": "http",
       "host": host,
       "port": port,
       "username": user,
       "password": pwd
   }
   ```
2. **Gán Proxy vào Connection (scope=account):**
   ```python
   # PUT http://127.0.0.1:20129/api/settings/proxies/assignments
   payload = {
       "scope": "account",
       "scopeId": connection_id,
       "proxyId": proxy_id
   }
   ```
3. **Kiểm tra / Verify Proxy Resolved:**
   ```python
   # GET http://127.0.0.1:20129/api/settings/proxy?resolve={connection_id}
   # Trả về: {"proxy": {"host": "...", "port": ...}, "level": "account", "source": "registry"}
   ```

---

## 5. Dọn Dẹp Chrome GPM Chạy Ngầm (Chống Rò Rỉ Tài Nguyên & Kẹt CDP)

Khi chạy lặp qua nhiều profile GPM trong các script batch:
- Các tiến trình Chrome của GPM có thể không thoát hẳn khi gọi API `/profiles/stop/{pid}` hoặc khi script bị gián đoạn.
- Khi tích tụ hàng trăm Chrome zombie (thực nghiệm từng phát hiện tới 441 processes), máy chủ bị cạn kiệt port CDP và RAM, gây ra lỗi `connect ECONNREFUSED` và timeout.
- **Quy tắc dọn dẹp an toàn (CHỈ KILL CHROME CỦA GPM, CẤM ẢNH HƯỞNG CHROME CÁ NHÂN CỦA USER):**
  ```python
  import psutil
  killed = 0
  for p in psutil.process_iter(["name", "exe"]):
      try:
          exe = (p.info["exe"] or "").lower()
          if "gpmlogin" in exe and "chrome.exe" in exe:
              p.kill()
              killed += 1
      except Exception:
          pass
  ```

---

## 3. Pitfalls Cần Tránh

| Pitfall | Nguyên Nhân | Giải Pháp |
| :--- | :--- | :--- |
| **Bấm nút Đăng nhập không ăn** | ChatGPT render button dạng thẻ giả hoặc bị chặn bởi modal cookie | Dùng Direct OAuth URL: `chatgpt.com/auth/login_with?...` |
| **Kẹt form `about-you`** | Cố tình format `DD/MM/YYYY` vào ô tuổi | `input[name="age"]` là số nguyên (tuổi), tính tuổi từ năm sinh và điền số |
| **Selector email không tìm thấy** | Input email Google là `type="text"`, selector `input[type="email"]` bị miss | Dùng `#identifierId` hoặc `input[name="identifier"]` |
| **Google reCAPTCHA v2 / Enterprise** | IP proxy bị flag hoặc thiết bị mới hoàn toàn chưa từng login Google | Tuân thủ Gate 4 Fail-Fast: Dừng ngay, đóng profile để user giải captcha thủ công 1 lần |
