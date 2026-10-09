# Xóa Dữ Liệu Tách Biệt Theo Domain (Surgical Site Cache Clearing) & Quy Trình Codex OAuth OmniRoute

## 1. Bối cảnh & Vấn đề
Khi một dịch vụ AI bên thứ ba (như OpenAI / ChatGPT / Claude / Anthropic) bị vô hiệu hóa tài khoản (`account_deactivated`), việc giữ lại cookie và LocalStorage cũ sẽ khiến trình duyệt liên tục báo lỗi xác thực hoặc tự động chuyển hướng vào session chết.
Tuy nhiên, profile GPM đó đang chứa session Google/Gmail quý giá (đã login, có cookie lịch sử, liên kết farm S7). **Tuyệt đối không được xóa toàn bộ profile hay clear toàn bộ browser data**, vì sẽ làm mất session Google/Gmail.

---

## 2. Kỹ Thuật Xóa Dữ Liệu Tách Biệt Theo Domain (SQLite Offline)

Thực hiện dọn dẹp trực tiếp trên thư mục dữ liệu Chrome của profile khi browser đã đóng (hoặc sau khi gọi `GET /api/v3/profiles/stop/{id}`):

### Bước 1: Sao lưu trước khi can thiệp
```python
shutil.copy2(cookies_path, cookies_path + ".bak_site")
shutil.copy2(login_data_path, login_data_path + ".bak_site")
```

### Bước 2: Xóa Cookie cô lập theo Host Key
File `Default/Network/Cookies` là cơ sở dữ liệu SQLite:
```sql
-- Kiểm tra số lượng cookie trước khi xóa
SELECT count(*) FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%';
SELECT count(*) FROM cookies WHERE host_key LIKE '%google%';

-- Xóa sạch cookie của riêng domain mục tiêu
DELETE FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%';
VACUUM;
```
*Kết quả kiểm chứng:* 75/75 cookies của Google/YouTube được bảo toàn nguyên vẹn 100%, cookie OpenAI trở về 0.

### Bước 3: Xóa thông tin đăng nhập tự động (Autofill Password)
File `Default/Login Data`:
```sql
DELETE FROM logins WHERE origin_url LIKE '%openai%' OR origin_url LIKE '%chatgpt%';
VACUUM;
```
Tránh việc Chrome autofill lại mật khẩu của tài khoản đã bị vô hiệu hóa.

### Bước 4: Xóa Storage / IndexedDB của Domain
Quét và xóa các thư mục LevelDB của riêng domain đó:
- `Default/IndexedDB/https_chatgpt.com_0.indexeddb.leveldb`
- `Default/IndexedDB/https_auth.openai.com_0.indexeddb.leveldb`
- `Default/Local Storage/leveldb` (nếu cần dọn sâu).

---

## 3. Bản Chất Fingerprint Khi Đăng Ký Lại Tài Khoản (Re-registration)

### Câu hỏi: Giữ nguyên Fingerprint GPM có reg lại tài khoản OpenAI được không?
- **Hoàn toàn được và tối ưu nhất.**
- OpenAI không ban phần cứng (Hardware ID) như game anticheat. Họ định danh trình duyệt qua:
  1. **Storage định danh:** Token `oai-did`, `oaicom-stable-id` lưu trong cookie/localStorage. Khi dọn sạch theo mục 2, trình duyệt trở thành "khách truy cập mới toanh" (Fresh Visitor).
  2. **Địa chỉ IP:** Dàn profile chạy qua Proxy 4G Mobi (`test.taadaa.click:5101..5138`) là dải IP mạng di động dân cư sạch, độ tin cậy Cloudflare cao.
  3. **Email & Số điện thoại lúc reg:** Kiểm tra tài khoản mới hoặc dùng "Tiếp tục với Google" với Gmail đang live trong profile.
- **Vai trò của Fingerprint GPM:** Canvas/WebGL/Audio noise có sẵn giúp chứng minh môi trường người dùng thật, giúp Cloudflare Turnstile tự động vượt qua (bypass Turnstile mà không bị văng challenge bot). Do đó, **giữ nguyên Fingerprint là an toàn nhất cho cả Google session và tài khoản mới**.

---

## 4. Quy Trình Codex OAuth Vào OmniRoute (:20129)

Khi thêm hoặc đăng nhập lại tài khoản Codex (ChatGPT Plus / Team) vào OmniRoute:

1. **Khởi động Callback Server:**
   - `GET http://localhost:20129/api/oauth/codex/start-callback-server`
   - OmniRoute mở HTTP server tại cổng `1455` đường dẫn `/auth/callback` và trả về `authUrl`.

2. **Mở Profile GPM & Kết Nối Playwright CDP:**
   - `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}` lấy `remote_debugging_address`.
   - Kết nối `playwright.chromium.connect_over_cdp()`.

3. **Cơ Chế Forward Loopback Callback (Tránh Hairpin NAT qua Proxy 4G):**
   - Khi trình duyệt chạy qua proxy 4G ngoài, việc redirect về `http://localhost:1455/auth/callback` có thể bị proxy từ chối (loopback connection refused).
   - Thiết lập network interceptor trong Playwright:
     ```python
     def on_request(req):
         if "1455" in req.url or "code=" in req.url:
             try:
                 local_url = req.url.replace("localhost", "127.0.0.1")
                 requests.get(local_url, timeout=5)
             except Exception:
                 pass
     page.on("request", on_request)
     ```

4. **Poll & Trao Đổi Token:**
   - Poll `POST http://localhost:20129/api/oauth/codex/poll-callback` với body `{}` mỗi 3s.
   - Khi nhận được `connection.id`, tiến hành gán proxy 1:1.

5. **Gán Proxy 1:1 Cho Connection Codex:**
   ```json
   PUT http://localhost:20129/api/settings/proxies/assignments
   {
     "scope": "account",
     "scopeId": "<connection_id>",
     "proxyId": "<omniroute_proxy_id>"
   }
   ```
