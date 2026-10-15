# ChatGPT-Web Account Harvesting, Proxy Authentication & Session Token Pitfalls

## 1. Bẫy Token Giả (False Positive JWT Detection)
- **Triệu chứng:** Script nạp tài khoản báo thành công (token dài vài nghìn ký tự), nhưng khi OmniRoute gửi request tới `chatgpt.com/api/auth/session` thì lập tức trả về **HTTP 401** `ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie`.
- **Nguyên nhân:**
  - Script cũ kiểm tra:
    ```python
    has_token = any((c.get("value") or "").startswith("eyJhbG") for c in cookies)
    ```
  - Khi profile mở vào `auth.openai.com` chưa đăng nhập thành công, OpenAI vẫn set các cookie tạm thời như `oai-did`, `auth0`, `__cf_bm` có giá trị bắt đầu bằng `eyJhbG`.
- **Giải pháp bắt buộc:**
  - Cookie session hợp lệ của ChatGPT Web **BẮT BUỘC phải có `name` chứa `session-token`**:
    ```python
    has_token = any("session-token" in (c.get("name") or "") for c in all_cookies)
    ```
  - Hỗ trợ cả cookie đơn `__Secure-next-auth.session-token` lẫn chunked cookie `__Secure-next-auth.session-token.0`, `.1`.

---

## 2. Bẫy Xác Thực Proxy Mobi (Port-Specific Proxy Credentials)
- **Triệu chứng:** Khi gọi request qua combo hoặc direct connection, OmniRoute lập tức ngắt với lỗi:
  `[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5104` (HTTP 503).
- **Nguyên nhân:**
  - Dải proxy Mobi `test.taadaa.click` từ port 5101 đến 5138 **KHÔNG dùng chung username**:
    + Port 5101: `mobi1`
    + Port 5104: `mobi4`
    + Port 5128: `mobi28`
    + Password chung: `TaadaaMobi#2026!`
  - Nếu ghi vào `proxy_registry` hardcode username `mobi28` cho tất cả các port, proxy server trả về **HTTP 407 Proxy Authentication Required**. OmniRoute coi đây là proxy chết và bật Circuit Breaker Fast-Fail làm chết chùm cả pool.
- **Giải pháp:**
  - Khi sync proxy vào `proxy_registry`, bắt buộc tính username động theo port:
    ```python
    user = f"mobi{port - 5100}" if 5101 <= port <= 5138 else ...
    ```

---

## 3. Bẫy Regex Lọc Tài Khoản Bỏ Sót Hotmail
- **Hiện tượng:** Kho GPM có tới 460 profile `@hotmail.com` đã đăng nhập ChatGPT sẵn từ trước, nhưng pool ChatGPT-Web luôn thiếu tài khoản vì các script import (`batch_chatgpt_web_5workers.py`, `batch_rescue`) chỉ dùng regex cứng:
  `re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', name)`
- **Giải pháp:** Mở rộng regex để nhận diện cả `@hotmail.com`:
  `re.search(r'([a-zA-Z0-9_.+-]+@(gmail|hotmail)\.com)', name)`
