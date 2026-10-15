# ChatGPT Web Session Token Extraction & Per-Port Proxy Auth Pitfalls

## 1. BẪY NHẬN DIỆN TOKEN JWT RÁC (SESSION-TOKEN TRAP)
- **Hiện tượng**: Script kiểm tra cookie bằng `cookie.value.startswith('eyJhbG')` và kết luận profile đã đăng nhập ChatGPT thành công. Khi nạp vào OmniRoute, endpoint trả về `401 Unauthorized: ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie from chatgpt.com`.
- **Nguyên nhân gốc rễ**: Trang đăng nhập OAuth của OpenAI (`auth.openai.com`) khi người dùng **CHƯA ĐĂNG NHẬP** vẫn cấp các cookie tạm thời dạng JWT (như `oai-did`, `auth0`, `__cf_bm`) có value bắt đầu bằng `eyJhbG`.
- **Quy chuẩn bắt buộc**:
  - Chỉ coi là **ĐÃ ĐĂNG NHẬP** khi tìm thấy cookie có tên chứa `__Secure-next-auth.session-token` (hoặc dạng chunked `__Secure-next-auth.session-token.0`, `.1`).
  - Code chuẩn:
    ```python
    has_token = any('session-token' in (c.get('name') or '') for c in all_cookies)
    ```

## 2. CHUẨN AUTH THEO TỪNG PORT PROXY MOBI (`test.taadaa.click:5101..5138`)
- **Hiện tượng**: OmniRoute trả về `503 Service Unavailable: [Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5104`.
- **Nguyên nhân**: Script khi ghi vào `proxy_registry` của OmniRoute hardcode username `mobi28` cho tất cả các port. Proxy server trả về `407 Proxy Authentication Required` khiến OmniRoute kích hoạt mạch ngắt `Proxy Fast-Fail` làm tê liệt cả pool.
- **Quy tắc gán username chuẩn**:
  - Mỗi port dải Mobi 51xx có username riêng theo công thức:
    `username = f"mobi{port - 5100}"` (ví dụ: port 5101 là `mobi1`, 5104 là `mobi4`, 5128 là `mobi28`).
  - Password dùng chung: `TaadaaMobi#2026!`.

## 3. BỎ SÓT KHO TÀI KHOẢN HOTMAIL GPM VÌ REGEX CỨNG
- **Hiện tượng**: Pool thiếu tài khoản trầm trọng (chỉ nạp 3-6 Gmail), trong khi kho GPM có hơn 460 profile Hotmail đã reg ChatGPT.
- **Nguyên nhân**: Script cào/nạp cũ lọc cứng `re.search(r'@gmail\.com', profile_name)` nên tự động bỏ qua toàn bộ profile `@hotmail.com`.
- **Kỷ luật vận hành**:
  - Khi quét GPM profile để bổ sung quota ChatGPT-Web, regex bắt buộc phải chấp nhận cả `@hotmail.com`:
    ```python
    re.search(r'([a-zA-Z0-9_.+-]+@(gmail|hotmail)\.com)', profile_name)
    ```
  - Phần lớn Hotmail trong GPM đã được reg ChatGPT từ trước, khi mở bằng Playwright CDP có sẵn session token hợp lệ mà không cần trải qua luồng Google OAuth.
