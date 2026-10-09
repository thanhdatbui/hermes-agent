# NextAuth Session Token Chunking & OmniRoute ChatGPT-Web Integration

## 1. Vấn đề Cookie Chunking trong NextAuth
Khi người dùng đăng nhập ChatGPT Web (`chatgpt.com`), phiên xác thực được lưu dưới cookie `__Secure-next-auth.session-token`. Khi kích thước payload JWT vượt quá giới hạn 4096 bytes của trình duyệt, NextAuth tự động chia nhỏ cookie thành các chunk có hậu tố số:
- `__Secure-next-auth.session-token.0`
- `__Secure-next-auth.session-token.1`
- `__Secure-next-auth.session-token.2`...

### Pitfall trích xuất từ Playwright CDP
- Nếu code chỉ tìm cookie chứa `session-token` và lấy giá trị bắt đầu bằng `eyJhbG`, nó sẽ chỉ lấy giá trị của chunk `.0`. Chuỗi này bị cắt cụt (truncated JWT), khiến request gửi lên ChatGPT API/Web bị lỗi `401 Unauthorized`.
- Nếu cookie đã bị chunked, phải gom toàn bộ các chunk lại, sắp xếp theo index số (`.0`, `.1`, ...) và định dạng thành chuỗi HTTP Cookie `k1=v1; k2=v2`.

## 2. Giải thuật trích xuất chuẩn trong Playwright
```python
# Bước trích xuất cookie session-token trong Playwright sync_api
all_cookies = context.cookies()
session_token = None

# 1. Tìm các chunk __Secure-next-auth.session-token.<n>
chunk_cookies = [
    ck for ck in all_cookies
    if ck.get("name", "").startswith("__Secure-next-auth.session-token.")
]

if chunk_cookies:
    # Sắp xếp đúng theo thứ tự index .0, .1, ...
    def get_chunk_idx(ck):
        m = re.search(r'\.(\d+)$', ck.get("name", ""))
        return int(m.group(1)) if m else 0

    chunk_cookies.sort(key=get_chunk_idx)
    session_token = "; ".join(f"{ck['name']}={ck['value']}" for ck in chunk_cookies)
else:
    # 2. Trường hợp token đơn (không bị chunk)
    for ck in all_cookies:
        name = ck.get("name") or ""
        val = ck.get("value") or ""
        if "session-token" in name and (val.startswith("eyJhbG") or val):
            session_token = val
            break
```

## 3. Lọc Provider Active trong OmniRoute (`:20129`)
Khi gọi `GET /api/providers`, OmniRoute che giấu (mask) API key trả về:
- Token JWT thuần: `eyJhbGci****<hash>` (bắt đầu bằng `eyJhbG`)
- Cookie chunked: `__Secure****<hash>` (bắt đầu bằng `__Secure`)

### Pitfall lọc trùng tài khoản
- Nếu chỉ kiểm tra `key.startswith("eyJhbG")`, script sẽ bỏ sót tất cả tài khoản đang dùng cookie chunked bắt đầu bằng `__Secure`.
- Hậu quả: Script quét lại và chạy lại login cho các profile GPM đã hoạt động tốt, gây lãng phí proxy và rủi ro checkpoint Google.

### Code lọc chuẩn xác
```python
r = requests.get(f"{OMNIROUTE_BASE}/api/providers", timeout=10).json()
conns = r.get("connections", [])
web_active = set()
for c in conns:
    if c.get("provider") == "chatgpt-web":
        key = c.get("apiKey", "")
        # Masked key trong OmniRoute có thể bắt đầu bằng eyJhbG hoặc chứa __Secure
        if key and (key.startswith("eyJhbG") or "__Secure" in key):
            m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', c.get("name", "").lower())
            if m:
                web_active.add(m.group(1).lower())
```
