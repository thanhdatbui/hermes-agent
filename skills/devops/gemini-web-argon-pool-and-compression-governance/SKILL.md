---
name: gemini-web-argon-pool-and-compression-governance
description: "Vận hành Pool Gemini-Web (Argon 1M), tự động bóc cookie GPM CDP khi 401, và tối ưu nén context cơ học Hermes."
---
# Gemini-Web (Argon Pool) & Compression Governance

Sử dụng quy chuẩn này khi vận hành pool tài khoản `gemini-web` (Argon 1M context) trên OmniRoute (`:20129`), xử lý lỗi xác thực 401 qua GPMLogin, hoặc cấu hình nén ngữ cảnh Hermes.

## 1. Bản Chất Sự Cố Pool Gemini-Web (401 Unauthorized)
* Model `gemini-web` (Argon Pool) sử dụng Cookie Session:
  - `__Secure-1PSID`
  - `__Secure-1PSIDTS`
  - `__Secure-1PSIDCC`
* Khi Google hết hạn phiên hoặc đổi security token, OmniRoute ghi nhận:
  `[401]: Gemini Web session is not authenticated; refresh the __Secure-1PSID cookies.`
* **Nguyên nhân bỏ sót:**
  - Watchdog `cron_chatgpt_web_pool_watchdog.py` ban đầu chỉ quét `chatgpt-web`, `antigravity` và `codex`.
  - Thiếu nhánh cho `gemini-web` khiến tài khoản bị 401 nằm chết âm thầm dù profile GPM và tài khoản Google vẫn sống 100%.

## 2. Quy Trình Hồi Sinh Tự Động Qua GPM + CDP Playwright
1. **Truy vấn tài khoản lỗi trong SQLite (`storage.sqlite`):**
   ```sql
   SELECT id, email, name FROM provider_connections 
   WHERE provider='gemini-web' AND (is_active=0 OR last_error LIKE '%401%' OR test_status != 'ok');
   ```
2. **Khớp Profile GPM theo Email:**
   Gọi GPM API (`http://127.0.0.1:19995/api/v3/profiles?per_page=100`) tìm profile có tên chứa email tương ứng.
3. **Mở Profile và kết nối CDP:**
   - Khởi động: `GET /api/v3/profiles/start/{id}?skip_proxy_check=true`.
   - Kết nối Chromium qua `remote_debugging_address`.
4. **Bóc tách Cookie sống:**
   - Điều hướng `https://gemini.google.com/app` (chờ `domcontentloaded`).
   - Lấy cookies thuộc domain `.google.com` và `gemini.google.com`.
   - Trích xuất: `__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC`.
5. **Ghi đè CSDL OmniRoute (`storage.sqlite`):**
   ```python
   data["cookie"] = f"__Secure-1PSID={psid}; __Secure-1PSIDTS={psidts}; __Secure-1PSIDCC={psidcc}"
   if "apiKeyHealth" in data:
       data["apiKeyHealth"]["primary"]["status"] = "healthy"
       data["apiKeyHealth"]["primary"]["failures"] = 0
   cursor.execute("""
       UPDATE provider_connections
       SET provider_specific_data = ?, last_error = NULL, test_status = 'ok', is_active = 1
       WHERE id = ?
   """, (json.dumps(data), conn_id))
   ```
6. **Đóng Profile GPM:** `GET /api/v3/profiles/close/{id}`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
