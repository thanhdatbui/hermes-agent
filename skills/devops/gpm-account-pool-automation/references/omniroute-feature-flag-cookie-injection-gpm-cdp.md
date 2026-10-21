# Khôi Phục Session ChatGPT Web Trên GPM Qua OmniRoute Cookie Injection & CDP

## 1. Bối Cảnh & Vấn Đề
- Khi mở profile GPMLogin để người dùng hoặc automation truy cập ChatGPT Web (`https://chatgpt.com`), trình duyệt có thể hiển thị trạng thái chưa đăng nhập (`Where should we begin? / Log in / Sign up for free`) do:
  1. Trình duyệt bị tắt đột ngột (crash/unclean exit), chưa khôi phục trang (`Restore`).
  2. GPM profile mới hoặc session cookie trên Chrome bị hết hạn/xóa cache.
- Việc đăng nhập lại thủ công hoặc qua SSO (Google SSO / OTP) tốn nhiều thời gian và có nguy cơ kích hoạt checkpoint bảo mật / Captcha.
- Trong khi đó, **OmniRoute** (port 20129) đã có sẵn connection của tài khoản này trong pool `chatgpt-web` với session cookie (`__Secure-next-auth.session-token`) đang sống và hoạt động tốt.

---

## 2. Thách Thức Kỹ Thuật (API Key Masking)
- Theo mặc định trong OmniRoute (`src/app/api/providers/[id]/route.ts`), endpoint `GET /api/providers/:id` sẽ ẩn/che giấu API Key qua hàm `maskStoredApiKey` (trả về dạng `__Secure****CR2A`).
- `apiKey` trong DB `C:\Users\Kibe\.omniroute\storage.sqlite` được mã hóa `enc:v1:...`.
- Tuy nhiên, OmniRoute hỗ trợ cơ chế Feature Flag: `isApiKeyRevealEnabled()` kiểm tra cờ `ALLOW_API_KEY_REVEAL`.
- Thứ tự ưu tiên giải quyết cờ (`resolveFeatureFlag`):
  `DB override (bảng key_value, namespace='feature_flags') > process.env > definition.defaultValue`.

---

## 3. Quy Trình Trích Xuất & Inject Cookie Tự Động (O(1))

### Bước 1: Kích hoạt tạm thời Feature Flag trong SQLite
Ghi trực tiếp bản ghi override vào bảng `key_value` của `storage.sqlite`:
```python
import sqlite3

db_path = r"C:\Users\Kibe\.omniroute\storage.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("INSERT OR REPLACE INTO key_value (namespace, key, value) VALUES ('feature_flags', 'ALLOW_API_KEY_REVEAL', 'true')")
conn.commit()
```

### Bước 2: Gọi API lấy unmasked cookie & Rollback cờ ngay lập tức
Bọc trong khối `try...finally` để đảm bảo cờ luôn được xóa sạch khỏi DB:
```python
import urllib.request, json

conn_id = "<connection_uuid>"
try:
    url = f"http://127.0.0.1:20129/api/providers/{conn_id}"
    req = urllib.request.urlopen(url, timeout=5)
    data = json.loads(req.read().decode())
    api_key_str = data.get("connection", {}).get("apiKey")
finally:
    cur.execute("DELETE FROM key_value WHERE namespace='feature_flags' AND key='ALLOW_API_KEY_REVEAL'")
    conn.commit()
    conn.close()
```

### Bước 3: Phân tích và nạp Cookie vào Chromium qua Playwright CDP
Chuỗi `api_key_str` có định dạng header `cookie`: `name1=val1; name2=val2; ...`.
Tách từng cookie và nạp vào browser context:
```python
from playwright.sync_api import sync_playwright

cookie_items = []
for p in api_key_str.split(";"):
    p = p.strip()
    if not p or "=" not in p:
        continue
    eq_idx = p.find("=")
    k, v = p[:eq_idx].strip(), p[eq_idx+1:].strip()
    cookie_items.append({
        "name": k,
        "value": v,
        "domain": ".chatgpt.com",
        "path": "/",
        "httpOnly": True if any(x in k.lower() for x in ["secure", "token", "auth"]) else False,
        "secure": True,
        "sameSite": "Lax"
    })

with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
    ctx = browser.contexts[0]
    ctx.add_cookies(cookie_items)
    
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://chatgpt.com/", timeout=30000)
    
    # Xác thực session đã kích hoạt
    sess = page.evaluate("async () => await fetch('/api/auth/session').then(r => r.json())")
    assert sess.get("user") is not None, "Session injection failed!"
    browser.close()
```

---

## 4. Các Lưu Ý Sống Còn
1. **Rollback cờ bắt buộc:** Tuyệt đối không để cờ `ALLOW_API_KEY_REVEAL` tồn tại lâu dài trong `key_value` table để bảo vệ an toàn bảo mật cho toàn hệ thống OmniRoute.
2. **Domain cookie:** Bắt buộc đặt `domain=".chatgpt.com"` và `path="/"`, `secure=True`. Cookie quan trọng nhất là `__Secure-next-auth.session-token`.
3. **Kiểm tra Session API:** Luôn gọi `GET /api/auth/session` sau khi inject để xác nhận `user.email` và `user.name` đã load thành công trước khi báo cho user hoặc thực hiện automation tiếp theo.
