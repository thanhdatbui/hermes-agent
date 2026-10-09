# Xử lý Lỗi YouTube "Video unavailable" (VisionOS Client) & Rate Limit 1 Giờ

## 1. Hiện tượng & Triệu chứng

Khi tải YouTube Shorts bằng `yt-dlp` phiên bản mới (2026.07+ / 2026.08+):
1. **Lỗi `Video unavailable` dù video vẫn sống**:
   ```text
   [youtube] <id>: Downloading webpage
   [youtube] <id>: Downloading visionos player API JSON
   ERROR: [youtube] <id>: Video unavailable
   ```
   - **Nguyên nhân**: `yt-dlp` mặc định thử client `visionos` hoặc `mweb`, và YouTube chặn các API client này đối với nhiều Shorts hoặc IP cụ thể.
2. **Lỗi Rate Limit 1 Giờ trên Single IP**:
   ```text
   ERROR: [youtube] <id>: This content isn't available, try again later.
   The current session has been rate-limited by YouTube for up to an hour.
   It is recommended to use `-t sleep` to add a delay between video requests to avoid exceeding the rate limit.
   ```
   - **Nguyên nhân**: Quét/tải liên tục nhiều video từ cùng một địa chỉ IP khiến YouTube tạm khóa phiên IP đó trong 1 giờ.
3. **Cảnh báo thiếu JavaScript Runtime**:
   ```text
   WARNING: [youtube] No supported JavaScript runtime could be found.
   Only deno is enabled by default; to use another runtime add --js-runtimes RUNTIME[:PATH]
   ```

---

## 2. Giải Pháp Toàn Diện (Đã Kiểm Chứng Thực Tế)

### A. Chuyển sang Android Player Client (`player_client: ['android']`)
Cấu hình trong `ydl_opts`:
```python
ydl_opts = {
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    },
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
}
```
- **Hiệu quả**: Chuyển API giải mã từ `visionos` sang `android player API JSON`. Khắc phục triệt để lỗi `Video unavailable` giả, tải video chuẩn MP4 chất lượng cao.

### B. Cài Đặt Deno Standalone làm JS Runtime
Chỉ cần cài đặt package `deno` qua pip trong active virtualenv:
```bash
python -m pip install deno
```
- `yt-dlp` sẽ tự động phát hiện `deno.exe` tại `<venv>/Scripts/deno.exe` mà không cần thêm cờ cấu hình phức tạp.

### C. Thoát Rate Limit 1 Giờ bằng MikroTik LAN PPPoE Proxy Pool
Khi IP bị YouTube rate-limit ("rate-limited by YouTube for up to an hour"), không cần chờ 1 tiếng:
- **Cụm MikroTik PPPoE LAN**: Nằm tại `192.168.110.2:10001..10035` (35 cổng).
- **Xác thực**: `admin@1:admin@1`.
- **Định dạng Proxy URL**:
  ```python
  import urllib.parse
  proxy_url = f"http://{urllib.parse.quote('admin@1')}:{urllib.parse.quote('admin@1')}@192.168.110.2:{port}"
  ydl_opts["proxy"] = proxy_url
  ```
- **Đặc tính**: Độ trễ nội bộ siêu thấp (0.01s), mỗi cổng tương ứng 1 IP mạng cố định/di động riêng biệt, tốc độ tải thực tế đạt **10–26 MB/s**, xóa bỏ hoàn toàn rate limit.

### D. Chuẩn Hóa Đường Dẫn Kênh Shorts (`/shorts`)
Khi lấy danh sách video từ kênh YouTube:
```python
if ch_url and "youtube.com" in ch_url and not ch_url.endswith("/shorts"):
    ch_url = ch_url.rstrip("/") + "/shorts"
```
- Tránh việc `yt-dlp` quét trang chủ kênh và lấy nhầm playlist hoặc bài viết cộng đồng thay vì video ngắn.
