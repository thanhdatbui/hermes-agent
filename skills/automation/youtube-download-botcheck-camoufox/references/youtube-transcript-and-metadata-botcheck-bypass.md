# YouTube Transcript & Metadata Bot-Check Bypass (Android Client & Public Endpoints)

## Bối cảnh & Hiện tượng
Khi cào dữ liệu, giải thích video hoặc lấy transcript/phụ đề từ YouTube (`youtube-transcript-api` hoặc `yt-dlp` mặc định):
- YouTube trả về lỗi: `HTTP Error 429: Too Many Requests` hoặc `Sign in to confirm you’re not a bot`.
- `browser_navigate` hoặc Chrome headless cũng có thể bị chuyển hướng vào trang `google.com/sorry/index`.
- Nguyên nhân: Client mặc định (`WEB` hoặc `visionos`) bị Google xếp vào diện tự động hóa/cào dữ liệu trái phép.

## 1. Giải pháp 1: Ép Android Player Client trong yt-dlp (Lấy Full Metadata & Transcript không cần Cookies)
YouTube Android app sử dụng luồng API riêng ít bị thách thức bot-check so với Web client.

```python
import yt_dlp
import urllib.request
import json

ydl_opts = {
    'skip_download': True,
    'extractor_args': {'youtube': {'player_client': ['android']}},
    'quiet': True,
    'no_warnings': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/watch?v=VIDEO_ID", download=False)
    title = info.get("title")
    desc = info.get("description")
    duration = info.get("duration")
    
    # Trích xuất phụ đề tự động (auto subtitles/captions)
    auto_caps = info.get("automatic_captions", {})
    # Chọn ngôn ngữ (ví dụ: vi, vi-orig, en)
    sub_tracks = auto_caps.get("vi-orig") or auto_caps.get("vi") or auto_caps.get("en")
    
    if sub_tracks:
        # Ưu tiên định dạng json3 để dễ parse timestamp
        target_fmt = next((f for f in sub_tracks if f.get("ext") == "json3"), sub_tracks[0])
        req = urllib.request.Request(target_fmt["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            sub_json = json.loads(r.read().decode("utf-8"))
            # Duyệt các events để lấy text có timestamp
            transcript = []
            for ev in sub_json.get("events", []):
                t_ms = ev.get("tStartMs", 0)
                text = "".join(s.get("utf8", "") for s in ev.get("segs", []))
                if text.strip():
                    transcript.append((t_ms / 1000.0, text.strip()))
```

## 2. Giải pháp 2: Trích xuất nhanh siêu tốc không dính Bot-Check
Khi chỉ cần lấy tiêu đề, tác giả, mô tả hoặc bình luận mà không cần tải phụ đề chi tiết:

1. **oEmbed Endpoint (Zero-Check):**
   - URL: `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=VIDEO_ID&format=json`
   - Trả về: `title`, `author_name`, `author_url`, `thumbnail_url`.
   - Không bao giờ bị chặn bởi Google Sorry hay bot-check IP.

2. **Jina Reader Endpoint:**
   - URL: `https://r.jina.ai/https://www.youtube.com/watch?v=VIDEO_ID`
   - Đọc trực tiếp trang YouTube thành định dạng Markdown, trích xuất đầy đủ: Tiêu đề, Số lượt xem, Ngày đăng, Toàn bộ mô tả (Description), và Top các bình luận nổi bật (Comments).
