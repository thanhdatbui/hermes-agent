# ChatGPT-Web Chunked NextAuth Cookie Reconstruction & Cascade 401 Healer

## 1. Bản chất phân mảnh Cookie (> 4KB) trên NextAuth / ChatGPT
Khi đăng nhập ChatGPT trên Chrome (bao gồm các profile GPM):
- Cookie session `__Secure-next-auth.session-token` thường xuyên vượt quá giới hạn 4096 bytes do chứa cả JWT payload, session ID và claims.
- Trình duyệt Chrome và thư viện web tự động tách cookie này thành 2 hoặc nhiều mảnh:
  - `__Secure-next-auth.session-token.0` (chứa phần đầu, thường ~3933 - 3968 bytes, bắt đầu bằng `eyJhbGci...`)
  - `__Secure-next-auth.session-token.1` (chứa phần đuôi còn lại, ~80 - 750 bytes)
- **Cạm bẫy automation**: Nếu script trích xuất chỉ lấy chuỗi của chunk `.0` (dạng bare JWT) và bỏ qua chunk `.1` hoặc không giữ nguyên tên cookie, khi nạp vào OmniRoute:
  - OmniRoute gửi session cookie không hoàn chỉnh hoặc sai định dạng tới `chatgpt.com/api/auth/session`.
  - OpenAI từ chối xác thực và dội về mã **401 Unauthorized**:
    `[401]: ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie from chatgpt.com.`

---

## 2. Ảo giác Failover Cascade (Single Live Account Illusion)
- Khi người dùng gọi model (ví dụ `gpt-5.6-luna-free` hoặc `gpt-5.6-sol-high`), OmniRoute duyệt tuần tự qua danh sách các connection trong pool `chatgpt-web`.
- Các tài khoản lỗi ở đầu danh sách (dính 401 do cookie thiếu chunk) kích hoạt router chuyển tiếp failover.
- Ngay khi gặp tài khoản hợp lệ đầu tiên (ví dụ `luuhuong` trả về **200 OK `[healed]`**), **chuỗi failover lập tức dừng lại**.
- Tất cả các tài khoản khỏe mạnh xếp sau đó hoàn toàn không được gọi trong request đó.
- **Hệ quả phân tích sai**: Người vận hành nhìn vào bảng log request của 1 lượt gọi model thấy 1 chuỗi 401 và duy nhất 1 tài khoản 200, dễ kết luận sai lầm rằng *"cả pool chỉ có đúng 1 tài khoản sống, các tài khoản còn lại chết hết"*.
- **Cách đối soát chuẩn**:
  - Kiểm tra log của sự kiện `connection-test` (khi OmniRoute quét kiểm tra độc lập từng connection).
  - Hoặc test trực tiếp completion với header ghim connection: `x-connection-id: <connection_id>`.

---

## 3. Quy trình Trích xuất & Tái cấu trúc Cookie Trọn Vẹn (Reconstruction)
Khi đọc từ database SQLite `Cookies` của profile Chromium/GPM:
1. Giải mã master key từ file `Local State` bằng Windows DPAPI (`CryptUnprotectData`).
2. Truy vấn tất cả cookies có tên chứa `session-token` cho domain `chatgpt.com`, sắp xếp theo thứ tự `name ASC` (`.0`, `.1`...).
3. Giải mã AES-GCM (bỏ 3 bytes prefix `v10`/`v11`, nonce 12 bytes, ciphertext + tag, và offset 32 bytes header nếu đọc raw).
4. Ghép lại chuỗi hoàn chỉnh theo đúng định dạng Cookie header:
   ```python
   full_cookie = f"__Secure-next-auth.session-token.0={val0}; __Secure-next-auth.session-token.1={val1}"
   ```
5. Cập nhật vào OmniRoute qua `PUT /api/providers/{id}` với `apiKey: full_cookie`.

---

## 4. Reset Stale Error Code & Accept HTTP 201
1. **Chấp nhận HTTP 201 Created**: Khi tạo mới connection qua `POST /api/providers`, OmniRoute có thể trả về HTTP 201 thay vì 200. Hook cần kiểm tra `status_code in (200, 201)` để tránh false-negative.
2. **Dọn dẹp cờ lỗi cũ**: Sau khi cập nhật cookie mới vào connection, xóa sạch các trường `error_code`, `last_error`, `last_error_at` cũ trong SQLite (`provider_connections`) để router không lưu vết lỗi quá khứ.
