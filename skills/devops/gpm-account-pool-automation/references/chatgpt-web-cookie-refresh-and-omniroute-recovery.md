# ChatGPT Web Cookie Refresh & OmniRoute Pool Recovery Flow

## 1. Bối cảnh & Hiện tượng
- Tài khoản `chatgpt-web` trên OmniRoute (`:20129`) sau một thời gian có thể bị chuyển sang trạng thái `expired`, `banned` hoặc `is_active=0` do session cookie `__Secure-next-auth.session-token` hết hạn.
- Profile GPM chứa sẵn Google login đã mở được ChatGPT Web, nhưng cookie chưa được đồng bộ sang OmniRoute.

## 2. Điểm kỹ thuật quan trọng (Pitfalls)
1. **Chunked Cookies (> 4KB)**:
   - Trình duyệt Chrome phân mảnh `__Secure-next-auth.session-token` thành nhiều chunk: `.0`, `.1`, ...
   - Không được chỉ lấy chuỗi trần của `.0`. Cần lấy toàn bộ cookie từ domain `https://chatgpt.com` hoặc ghép chuỗi `__Secure-next-auth.session-token.0=...; __Secure-next-auth.session-token.1=...`.
   - Cách an toàn nhất qua Playwright CDP:
     ```python
     cookies = ctx.cookies(['https://chatgpt.com'])
     cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
     ```

2. **Dọn dẹp GPM Profile an toàn**:
   - Luôn bọc trong `try ... finally` để gọi endpoint đóng profile:
     ```python
     requests.get(f'http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}', timeout=15)
     # hoặc /api/v3/profiles/stop/{profile_id}
     ```

3. **Xác thực trước khi nạp vào OmniRoute**:
   - Endpoint test validation của OmniRoute:
     `POST http://127.0.0.1:20129/api/providers/validate`
     Body: `{"provider": "chatgpt-web", "apiKey": cookie_str}`
   - Trả về `{"valid": true}` mới tiến hành cập nhật vào database.

4. **Cập nhật SQLite OmniRoute (`~/.omniroute/storage.sqlite`)**:
   - Bảng `provider_connections`:
     ```sql
     UPDATE provider_connections 
     SET api_key = ?, is_active = 1, test_status = 'active', 
         last_error = NULL, last_error_at = NULL, backoff_level = 0, 
         rate_limited_until = NULL, updated_at = CURRENT_TIMESTAMP 
     WHERE id = ?;
     ```
   - Bảng `combos`: Với combo `chatgpt-web-pool` (ID: `9c68197d-410a-4267-a3e7-c843aa82cab0`), kiểm tra mảng `models` trong JSON để bổ sung model target tương ứng nếu chưa có.

5. **CDP Readiness Polling chống lỗi ECONNREFUSED**:
   - Sau khi gọi `/profiles/start/{pid}`, GPM trả về `remote_debugging_address` ngay nhưng Chrome mất 1-3 giây để mở socket. Nếu gọi `connect_over_cdp` lập tức sẽ bị văng `ECONNREFUSED`.
   - Bắt buộc poll `http://{cdp_addr}/json` trả về HTTP 200 trước khi kết nối:
     ```python
     for _ in range(20):
         try:
             with urllib.request.urlopen(f"http://{cdp_addr}/json", timeout=1) as r:
                 if r.status == 200: break
         except Exception:
             time.sleep(1)
     ```

6. **Bẫy Giao diện Tiếng Việt & Cookie Banner (Chấp nhận tất cả)**:
   - ChatGPT Web trên IP Việt Nam hiển thị banner cookie che toàn màn hình: `"Chúng tôi sử dụng cookie... Chấp nhận tất cả"`.
   - Bắt buộc click nút `"Chấp nhận tất cả"` hoặc `"Accept all"` trước khi thao tác các nút khác.

7. **Bẫy Guest Mode vs Logged-in & Selector Modal Đăng nhập**:
   - ChatGPT cho phép chat ở chế độ khách (Guest). Ô nhập `#prompt-textarea` VẪN XUẤT HIỆN ở Guest mode -> Không được dùng `#prompt-textarea` để khẳng định đã login!
   - Guest cookies chỉ có ~9-14 cookies và thiếu `__Secure-next-auth.session-token`.
   - Modal chào xuất hiện có nút `"Đăng nhập"` / `"Đăng ký miễn phí"`. Nếu dùng `.locator('button:has-text("Đăng nhập")').first` trong Playwright, nó sẽ bắt trúng phần tử ẩn ở sidebar (`is_visible() == False`) khiến script bỏ qua!
   - Giải pháp: Lọc phần tử visible (`offsetParent !== null` và `getBoundingClientRect()`) hoặc điều hướng thẳng tới `https://chatgpt.com/auth/login` để kích hoạt flow OAuth Google SSO.
