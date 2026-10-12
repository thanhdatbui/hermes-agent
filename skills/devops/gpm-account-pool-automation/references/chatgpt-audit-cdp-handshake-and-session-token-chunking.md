# ChatGPT Audit & GPM Automation: CDP Origin Handshake, NextAuth Chunking & Onboarding Routing

## 1. CDP WebSocket Handshake 403 Forbidden (Chromium 142+)
### Triệu chứng
Khi kết nối CDP WebSocket tới profile GPM (`http://127.0.0.1:<port>/json`):
```text
websocket._exceptions.WebSocketBadStatusException: Handshake status 403 Forbidden -+-+- Rejected an incoming WebSocket connection from the http://127.0.0.1:<port> origin. Use the command line flag --remote-allow-origins=...
```

### Nguyên nhân & Cách khắc phục
Chromium Core 142+ trên GPM bật bảo vệ Host/Origin header kiểm soát WebSocket. Thư viện `websocket-client` trong Python mặc định gửi header `Origin: http://127.0.0.1:<port>`, khiến Chrome từ chối kết nối nếu không có cờ `--remote-allow-origins=*`.
**Khắc phục chuẩn:**
Khi khởi tạo `websocket.create_connection`, bắt buộc truyền tham số `suppress_origin=True`:
```python
ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
```

---

## 2. NextAuth Session Token Chunking (`.0`, `.1`)
### Triệu chứng
Tài khoản đã đăng nhập thành công vào ChatGPT (`https://chatgpt.com/`, body có "Trò chuyện mới" / "New chat"), nhưng script báo `has_token: false` và không trích xuất được session token để đồng bộ sang OmniRoute / 9Router.

### Nguyên nhân & Cách khắc phục
NextAuth.js chia nhỏ session cookie khi kích thước vượt quá ~4KB để tránh giới hạn kích thước header của trình duyệt:
- Cookie chuẩn: `__Secure-next-auth.session-token`
- Cookie phân mảnh: `__Secure-next-auth.session-token.0`, `__Secure-next-auth.session-token.1`, ...
**Khắc phục chuẩn:**
Hàm trích xuất cookie cần kiểm tra cả cookie đơn và ghép các mảnh chunked:
```python
def extract_full_session_token(cookies):
    # 1. Thử cookie đơn
    for ck in cookies:
        if ck.get("name") == "__Secure-next-auth.session-token":
            return ck.get("value")
    # 2. Ghép chuỗi phân mảnh theo thứ tự index .0, .1, ...
    chunks = {}
    prefix = "__Secure-next-auth.session-token."
    for ck in cookies:
        name = ck.get("name", "")
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            if suffix.isdigit():
                chunks[int(suffix)] = ck.get("value", "")
    if chunks:
        return "".join(chunks[i] for i in sorted(chunks.keys()))
    return None
```

---

## 3. Onboarding Redirect (`/about-you`) vs Deactivation
### Hiện tượng
Sau khi submit OTP hợp lệ, tài khoản không chuyển thẳng sang `https://chatgpt.com/` mà dừng ở `https://auth.openai.com/about-you` ("Bạn bao nhiêu tuổi?" / Họ và tên, Tuổi).
- Đây là tài khoản **chưa hoàn tất hồ sơ**, KHÔNG PHẢI tài khoản bị vô hiệu hóa (`account_deactivated`).
- Phải giữ trạng thái `UNKNOWN` hoặc phân loại `PENDING_ONBOARDING`, tuyệt đối **không được kích hoạt purge**.
