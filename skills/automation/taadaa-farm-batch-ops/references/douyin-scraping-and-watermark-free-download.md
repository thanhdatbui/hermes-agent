# Cào & Tải Video Douyin Nội Địa Trung Quốc Không Watermark (f2 + Chrome CDP Cookies + Proxy)

> 📌 **Tổng quan**: Douyin (TikTok nội địa Trung Quốc) áp dụng hệ thống bảo mật WAF nghiêm ngặt (chữ ký `a_bogus`, `msToken`, token CSRF, TLS fingerprinting và bắt buộc quét mã QR khi search). Tài liệu này hướng dẫn quy trình tự động hóa 100% để bóc tách video MP4 Full HD 1080p không logo/watermark từ Douyin về máy chủ Taadaa.

---

## 1. Kiến Trúc Phòng Thủ Của Douyin & Cách Hóa Giải

| Cơ Chế Phòng Thủ | Biểu Hiện Khi Gọi Trực Tiếp | Giải Pháp Hóa Giải |
| :--- | :--- | :--- |
| **Tengine Anti-Bot (HTTP Gateway)** | `curl` hoặc `requests` thô trả về `HTTP 1.1 404 Not Found` | Sử dụng browser có TLS engine chuẩn (Chrome CDP port 9222) hoặc thư viện bọc HTTP/2 `f2` (httpx). |
| **WAF Detail API Block** | `f2` hoặc `yt-dlp` trả về `HTTP 403 Forbidden` (`Fresh cookies needed`) | Trích xuất cookie sống từ phiên Chrome CDP qua giao thức DevTools Protocol `Network.getCookies`. |
| **Search Login Gate** | Truy cập `/search/<từ_khóa>` bị popup QR Code che màn hình, DOM trả về 0 kết quả | Chuyển sang cào từ feed `/jingxuan` hoặc category tabs (`美妆穿搭`) không bị popup chặn; hoặc cào theo URL profile creator. |
| **Geo-blocking / Firewall** | Kết nối bị timeout hoặc bóp băng thông từ ngoài lãnh thổ Trung Quốc | Định tuyến qua proxy pool farm (`D:/Taadaa/Tiktok-video/proxy_pool_67.txt`) có URL-encode credential. |

---

## 2. Công Cụ Thực Thi: `f2` CLI

Thư viện mã nguồn mở chuyên dụng: `Johnserf-Seed/f2` (Python 3.10+):
```bash
# Đảm bảo đã cài đặt trong môi trường Python
pip install f2
f2 --help
```

### Cú pháp tải chuẩn
1. **Tải 1 video lẻ (Single Video Mode)**:
   ```bash
   f2 dy -u "https://www.douyin.com/video/<video_id>" -M one -k "<cookie_string>" -p "D:/video goc/<folder>"
   ```
2. **Tải toàn bộ trang cá nhân (Creator Profile Mode - Độc Quyền)**:
   ```bash
   f2 dy -u "https://www.douyin.com/user/<sec_user_id>" -M post -o 40 -k "<cookie_string>" -p "D:/video goc/<folder>"
   ```
3. **Kèm proxy qua tường lửa**:
   ```bash
   f2 dy -u "<url>" -M one -p "<output_dir>" -P "http://user:pass@host:port" -k "<cookie_string>"
   ```

---

## 3. Quy Trình Tự Động Trích Xuất Cookie Sống Qua Chrome CDP

Chrome CDP (port 9222) đã khởi chạy sẵn với profile trình duyệt thật. Sử dụng script Python kết nối WebSocket DevTools Protocol để đọc cookie không cần can thiệp tay:

```python
import asyncio, json, socket, os
from urllib.parse import urlparse

async def get_douyin_cookie_string(ws_url: str) -> str:
    """Trích xuất chuỗi cookie định dạng name=val; name2=val2 từ Chrome CDP."""
    parsed = urlparse(ws_url)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((parsed.hostname, parsed.port))
    
    # WebSocket Handshake
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    req = (
        f"GET {parsed.path} HTTP/1.1\r\n"
        f"Host: {parsed.hostname}:{parsed.port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode())
    sock.recv(4096)
    
    # Gửi lệnh Network.getCookies
    msg = json.dumps({"id": 101, "method": "Network.getCookies", "params": {"urls": ["https://www.douyin.com"]}})
    data = msg.encode()
    length = len(data)
    frame = bytearray([0x81])
    frame.append(0x80 | 126)
    frame.extend(length.to_bytes(2, "big"))
    mask = os.urandom(4)
    frame.extend(mask)
    masked = bytearray(data[i] ^ mask[i % 4] for i in range(length))
    frame.extend(masked)
    sock.sendall(frame)
    
    # Đọc response
    buf = sock.recv(65536)
    idx = buf.find(b'{"id":101')
    if idx != -1:
        res = json.loads(buf[idx:].decode("utf-8", errors="ignore"))
        cookies = res.get("result", {}).get("cookies", [])
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies if c.get("name") and c.get("value")])
        return cookie_str
    return ""
```

---

## 4. Kiểm Thử & Nghiệm Thu Chất Lượng Video

Sau khi tải file video MP4 về từ Douyin:
1. **Kiểm tra thông số kỹ thuật qua `ffprobe`**:
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,duration,bit_rate -of default=noprint_wrappers=1 <video.mp4>
   ```
   - **Chuẩn chấp nhận**: Resolution 1080x1920 (dọc) hoặc 1920x1080 (ngang), Codec `h264`, duration 10s–65s, sạch 100% không watermark.
2. **Trích xuất ảnh frame nghiệm thu**:
   ```bash
   ffmpeg -y -ss 00:00:02 -i <video.mp4> -vframes 1 evidence_frame.jpg
   ```
3. **Thẩm định tự động qua AI Vision ViT ONNX**:
   - Chạy `AIFemaleFilter.classify_frame(evidence_frame.jpg)`.
   - Nếu `female_prob >= 0.60` -> Đạt chuẩn bạn nữ thật.
   - Nếu là game, hoạt hình, cảnh vật hoặc nam giới -> Tự động xóa file và bù video khác.
