# OpenAI `account_deactivated` Detection, GPM Re-login Flow & OmniRoute/9Router Purge

## 1. Triệu chứng & Bản chất lỗi (Deactivated Signature)

### Triệu chứng phía Proxy (OmniRoute / 9Router)
- **Codex Pool:** Token refresh thất bại với `Token invalid or revoked` / `API returned 401 after token refresh`.
- **ChatGPT-Web Pool:** Lỗi `Sentinel/Turnstile required` hoặc `401/403` liên tiếp kích hoạt Circuit Breaker 30 phút.
- **Bản chất thực tế:** Đây KHÔNG PHẢI lỗi tạm thời hay do Cloudflare chặn proxy, mà do OpenAI đã **vô hiệu hóa vĩnh viễn user ID** trên máy chủ (`error_code: account_deactivated`).

---

## 2. Quy trình Re-Login kiểm tra tận mắt trên GPM Browser

### Bước 1: Khởi động Profile & Truy cập Auth
- Mở profile qua GPM API: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
- Kết nối CDP WebSocket (`websocket.create_connection(..., suppress_origin=True)`).
- Điều hướng thẳng vào URL đăng nhập chính thức: `https://chatgpt.com/auth/login`.

### Bẫy chết người khi chọn nút Submit Email (Critical Pitfall)
- **CẢNH BÁO BẮT NHẦM NÚT GOOGLE:** 
  Trên trang `chatgpt.com/auth/login`, có các nút: *"Tiếp tục với Google"*, *"Tiếp tục với Apple"*, *"Tiếp tục với số điện thoại"*, và nút submit form email *"Tiếp tục"*.
  Nếu dùng selector lỏng lẻo `button.find(b => b.innerText.includes('Tiếp tục'))`, code sẽ **bắt nhầm nút "Tiếp tục với Google"** khiến trình duyệt nhảy sang `accounts.google.com/signin`, dẫn đến việc điền OTP vào ô email của Google và chụp nhầm màn hình đăng nhập Google.
- **Selector chuẩn bắt buộc:**
  ```javascript
  const buttons = Array.from(document.querySelectorAll('button'));
  const contBtn = buttons.find(b => {
      const t = (b.innerText || '').trim();
      return (t === 'Tiếp tục' || t === 'Continue' || b.type === 'submit') 
          && !t.includes('Google') && !t.includes('Apple') && !t.includes('thoại');
  });
  if (contBtn) contBtn.click();
  ```

### Bước 2: Bóc mã OTP từ Microsoft Graph API
- Scope bắt buộc: `"https://graph.microsoft.com/Mail.Read offline_access"` (CẤM dùng `.default` vì sẽ ăn lỗi `HTTP 400 Bad Request`).
- Header request exchange token: `{"Content-Type": "application/x-www-form-urlencoded"}`.
- Kéo email mới nhất từ `https://graph.microsoft.com/v1.0/me/messages?$top=3&$orderby=receivedDateTime%20desc`.
- Trích xuất mã OTP 6 số từ subject/preview: `r'\b(\d{6})\b'`.

### Bước 3: Điền OTP & Xác định trạng thái tài khoản
- Điền OTP vào ô `input[type="text"], input[name="code"], input` và click submit.
- **Cạm bẫy Post-Submit Latency, Redirect Pending & Onboarding Interstitial (False-UNKNOWN Trap):**
  * Sau khi bấm submit OTP, OpenAI thường mất 8–15 giây để xác thực và chuyển hướng từ `auth.openai.com` về `chatgpt.com`.
  * Nếu chỉ chờ 5 giây rồi kiểm tra `document.body.innerText` một lần duy nhất, script sẽ đọc trúng lúc trang đang loading hoặc chưa load xong dashboard, dẫn đến kết luận nhầm `UNKNOWN`.
  * Ngoài ra, các tài khoản gặp màn hình Onboarding ("Tell us about you", chọn ngày sinh), popup điều khoản, hoặc banner tính năng mới sẽ không hiển thị ngay các marker thông thường (`New chat`, `Cuộc trò chuyện mới`).
  * **Giải pháp chuẩn hóa:** Bắt buộc polling kiểm tra URL chuyển sang `chatgpt.com` (tối đa 15–20s). Nếu URL đã là `chatgpt.com` và không dính `account_deactivated`, kiểm tra sự xuất hiện của cookie `__Secure-next-auth.session-token` hoặc các phần tử dashboard để xác định `LIVE`. Tuyệt đối fail-closed: `UNKNOWN` không được ngộ nhận là `DEAD` và cấm purge.
- Đọc text trên trang phản hồi:
  * **Trường hợp DIE (Bị vô hiệu hóa):**
    Màn hình ném ra tiêu đề **"Lỗi xác thực - OpenAI"** kèm text:
    > *"Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa. Nếu bạn cho rằng đây là một nhầm lẫn, vui lòng liên hệ với chúng tôi qua trung tâm trợ giúp tại help.openai.com."*
    > `error_code: account_deactivated` | `request_id: <uuid>`
    $\rightarrow$ Chụp ảnh màn hình lưu bằng chứng tại `D:/Taadaa/runtime/artifacts/deactivated_{email}.png` và kích hoạt hàm Purge.
  * **Trường hợp LIVE:** Trình duyệt chuyển hướng vào dashboard ChatGPT (`https://chatgpt.com/`).

---

## 3. Quy trình Purge sạch tài khoản Die khỏi OmniRoute & 9Router

### Bước 1: Gửi lệnh DELETE API
- OmniRoute: `DELETE http://127.0.0.1:20129/api/providers/{provider_id}`.
- 9Router: `DELETE http://127.0.0.1:20128/api/providers/{provider_id}`.

### Bước 2: Dọn dẹp trong CSDL SQLite OmniRoute (`~/.omniroute/storage.sqlite`)
- Xóa kết nối:
  ```sql
  DELETE FROM provider_connections WHERE email LIKE '%{email}%' OR name LIKE '%{email}%';
  ```
- **Lưu ý cấu trúc bảng `combos`:**
  * Bảng `combos` lưu dữ liệu cấu hình trong cột **`data`** (chuỗi JSON), KHÔNG CÓ cột `models`.
  * Phải parse `json.loads(data)`, lọc bỏ các item chứa `provider_id` hoặc `email` đã xóa trong mảng `data["models"]`, sau đó cập nhật lại cột `data`.

### Bước 3: Đồng bộ bộ nhớ (Zero Downtime)
- Gửi request `PUT http://127.0.0.1:20129/api/combos/{combo_id}` với body là toàn bộ object `data` đã cập nhật để OmniRoute đồng bộ lại bộ nhớ RAM mà không cần khởi động lại tiến trình.

---

## 4. Kỷ luật Soi Mắt Đọc Ảnh Trước Khi Báo Cáo (Anti-Blind Delivery)
- Khi chụp ảnh từ CDP hay browser, **BẮT BUỘC dùng WinRT OCR hoặc vision đọc từng chữ trong ảnh thật** trước khi kết luận.
- Tuyệt đối không được suy diễn nội dung từ turn trước mà bỏ qua bước soi mắt ảnh mới tạo, tránh tình trạng script click nhầm nút dẫn đến chụp sai màn hình.
