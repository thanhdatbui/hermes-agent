# Local Vision Inspection & Browser Hang Prevention (06/10/2026)

## 1. Sự cố thực tế ngày 06/10/2026: Agent treo cứng do gọi `browser_navigate` để soi ảnh đĩa
1. **Bối cảnh:**
   - Để tuân thủ Invariant *"LLM soi mắt đọc ảnh trước khi gửi (chống gửi cho có lệ)"*, Coordinator cần kiểm tra 2 file avatar cục bộ (`D:/video goc/81/avatar.jpg` và `D:/video goc/11/avatar.jpg`).
   - Agent tạo file HTML cục bộ `file:///C:/Users/Kibe/AppData/Local/Temp/inspect_avatars.html` rồi gọi tool `browser_navigate(...)`.

2. **Hậu quả & Triệu chứng:**
   - Daemon `agent-browser` bị lỗi xung đột cấu hình daemon ngầm:
     `"A daemon for session 'h_c3a7b3641b' started concurrently with different daemon configuration. Retry the command so agent-browser can restart it with the requested configuration."`
   - Quá trình chạy bị loop hoặc kẹt kết nối, khiến session chính bị đơ, không phản hồi người dùng.
   - Operator bức xúc chấn chỉnh gay gắt: *"lí do treo..."*.

3. **Nguyên nhân gốc rễ:**
   - `browser_navigate` và bộ tool browser sinh ra để tương tác Web động (click/type/SPA/DOM), hoàn toàn KHÔNG phù hợp để soi ảnh tĩnh trên đĩa cứng cục bộ.
   - Khi chạy headless browser cho `file://`, Node process `agent-browser` phải khởi động cả runtime Chromium, tạo socket IPC, quản lý session lock. Nếu có session ngầm khác đang chạy hoặc phiên bản daemon lệch, nó sẽ văng lỗi concurrency conflict và retry gây treo lượt gọi.

---

## 2. Giải pháp chuẩn xác & Tốc độ cao: Direct Vision qua 9Router Proxy

### Kỹ thuật gọi Vision Model qua 9Router (`ag/gemini-3.7-flash-high`):
- Endpoint: `http://127.0.0.1:20128/v1/chat/completions`
- Token: Bearer token lấy từ `os.environ.get('NINEROUTER_API_KEY', '')`
- Image Format: Base64 data URL (`data:image/jpeg;base64,...`)
- **CRITICAL PARAMETER:** Bắt buộc truyền `'stream': False`. Nếu không truyền hoặc để mặc định stream, 9Router sẽ trả về Server-Sent Events (`data: {...}` chunks) khiến `json.loads(resp.read())` bị văng `JSONDecodeError`.

### Snippet chuẩn O(1) soi ảnh không treo:
```python
import base64
import json
import os
import urllib.request

key = os.environ.get("NINEROUTER_API_KEY", "")
with open("D:/path/to/image.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "ag/gemini-3.7-flash-high",
    "stream": False,
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Soi mắt kiểm tra chi tiết ảnh này: nhân vật, khuôn mặt, biểu cảm, chất lượng, có phù hợp niche không?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }
    ],
}

req = urllib.request.Request(
    "http://127.0.0.1:20128/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
)

with urllib.request.urlopen(req, timeout=30) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print(res["choices"][0]["message"]["content"])
```

---

## 3. Quy trình giải phóng khi phát hiện kẹt daemon agent-browser
Nếu hệ thống lỡ vướng daemon `agent-browser` bị treo hoặc xung đột session:
1. Chạy ngay lệnh CLI dọn dẹp:
   ```bash
   npx agent-browser close --all
   ```
2. Không cố gọi lại `browser_navigate` trong cùng session khi daemon đang conflict.
3. Chuyển ngay sang WinRT OCR (đọc chữ) hoặc 9Router Vision API (soi hình ảnh).
