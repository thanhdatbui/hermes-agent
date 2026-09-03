# TikTok discovery và tải direct

## Triệu chứng đã tái hiện

- `yt-dlp 2026.7.4` và bản mới nhất `2026.8.19` đều có thể trả `Unexpected response from webpage request` khi mở profile/video TikTok.
- Camoufox có lúc render được profile và nhận response public `/api/post/item_list/` HTTP 200; có lúc TikTok trả `Drag the slider to fit the puzzle`, không có item-list response.
- TikWM direct resolver vẫn tải được khi đã có URL video cụ thể.

## Đường fallback đã kiểm chứng

1. **Profile browser:** mở profile bằng Camoufox, chờ DOM/network, bắt response URL chứa `/api/post/item_list/`. Parse `itemList` hoặc `item_list`; mỗi item lấy `id`, `desc`, `stats.playCount`, `video.duration`, `author.uniqueId`.
2. **CAPTCHA fallback:** không bypass slider. Dùng DDGS/Bing public search:
   `site:tiktok.com/@<handle>/video/`
   và fallback `site:tiktok.com <handle> video`.
   Chuẩn hóa URL, bỏ query string, dedupe theo URL.
3. **Media:** gọi TikWM `https://tikwm.com/api/?url=<video_url>`, lấy `data.play`, tải bytes MP4. Chỉ chấp nhận file tồn tại và >1024 bytes.

## Canary evidence pattern

- Discovery profile `@quangvinhartist` từng trả 19 URL từ public search; canary cuối trả 9 URL.
- URL cụ thể đã tải qua production helper thành công: MP4 5,101,876 bytes; `ffprobe` đọc duration 15.133333s.
- Một canary khác tạo MP4 16,229,126 bytes; `ffprobe` đọc duration 252.9s.

## Quy tắc báo cáo

- `direct URL download OK` chỉ chứng minh tải một video cụ thể.
- Chỉ nói `profile discovery OK` khi có candidate count > 0.
- Chỉ nói `batch ready` sau canary folder hoặc tối thiểu discovery + media canary theo đúng production code.
- Wrapper exit 0, report record-level, hoặc file tạm chưa qua `ffprobe` không phải bằng chứng thành công.
- Nếu nhiều profile đều trả slider CAPTCHA: báo `BLOCKED_DISCOVERY_CAPTCHA`, không chạy batch rộng với source pool rỗng.

## Pitfall implementation

- DDGS trong môi trường đã kiểm chứng không dùng được với `with DDGS(...)`; khởi tạo `search = DDGS(timeout=30)` rồi gọi `search.text(...)`.
- Regex phải dùng dạng runtime đúng, ví dụ `r"https?://(?:www\\.)?tiktok\\.com/@[^/]+/video/(\\d{15,25})$"`; tránh escape dư khi patch qua shell.
- Sau khi chuyển TikTok sang direct-first, vẫn giữ yt-dlp cho YouTube và làm fallback TikTok, không thay đổi YouTube route.
