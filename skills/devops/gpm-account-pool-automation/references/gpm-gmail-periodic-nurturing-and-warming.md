# Quy trình nuôi định kỳ Gmail trên GPMLogin (Identity Warming & Behavior Dilution)

## 1. Mục đích & Nguyên tắc cốt lõi
- **Chạy hoàn toàn trên PC qua GPMLogin Chromium & Proxy 4G**, tuyệt đối **KHÔNG đụng tới điện thoại S7 / ADB**.
- Nuôi tài khoản định kỳ (YouTube, Google News, Google Search) nhằm duy trì độ trust, warming cookie và pha loãng hành vi máy móc (noise injection) sau khi sync OAuth hoặc đăng nhập.
- Trạng thái nuôi được lưu bền vững tại: `D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json`.
- Chu kỳ xoay vòng: Lọc các profile chưa nuôi hoặc `last_nurtured > 5 ngày`.
- Giới hạn batch: Mỗi tick chạy an toàn `BATCH_SIZE = 2` profile tuần tự để tránh nghẽn băng thông và xung đột cổng proxy.

## 2. Kịch bản nuôi chi tiết (3 Tabs)
Mỗi profile khi khởi động sẽ trải qua 3 bước tương tác tự nhiên:
1. **Tab 1 - YouTube Warming (90 - 120s, Bắt buộc vào trang /watch thật & Chống click Ad):**
   - Mở `https://www.youtube.com`. Nếu feed trống, chuyển qua Shorts xem 5-8s hoặc search từ khóa để bung feed.
   - **Lọc bỏ quảng cáo triệt để:** Quét danh sách link video (`a#video-title-link[href*='/watch'], ytd-rich-grid-media a#video-title-link, a#thumbnail[href*='/watch'], ytd-video-renderer a#video-title[href*='/watch']`). Kiểm tra phần tử tổ tiên (`ancestor::ytd-rich-item-renderer | ancestor::ytd-video-renderer`) để loại bỏ hoàn toàn các card có chữ *"Được tài trợ"*, *"Sponsored"*, *"Ad"*, *"advertisement"*.
   - **Click & Đảm bảo chuyển trang:** Click vào `target_video`. Nếu click không ăn hoặc bị chặn, chuyển hướng trực tiếp bằng `yt_page.goto(target_url)`.
   - **Chờ player sẵn sàng:** `yt_page.wait_for_url("**/watch*", timeout=15000)`, ngủ 5s để video render, gửi phím `'k'` unpause nếu video ở trạng thái pause.
   - **Nghiệm thu ảnh chụp (Visual Evidence):** Chụp trực tiếp màn hình YouTube player (`nurture_{email}.png` hoặc `dual_{email}_done.png`) khi chắc chắn đang ở URL `/watch` có player video và tiêu đề video.
   - Xem video trong **90 - 120 giây** tự nhiên.
2. **Tab 2 - Google News (Đọc báo 45 - 60s & Mô phỏng cuộn trang):**
   - Mở `https://news.google.com`, cuộn trang đọc lướt feed 2-3 lần.
   - Click vào 1 bài báo thật sự (`article a[href*='./read/'], article a[href*='/articles/']`). Sử dụng `context.expect_page()` để bắt tab bài báo mới nếu mở tab mới, hoặc đọc trên trang hiện tại.
   - Đọc bài báo trong **45 - 60 giây**, vừa đọc vừa cuộn trang từ từ mô phỏng người thật: 5-8 giây cuộn 1 lần (250 - 500px), cuộn 3-5 lần.
   - Sau đủ 45-60s đọc báo mới đóng tab bài báo và tab Google News.
3. **Tab 3 - Google Search (10 - 15s):**
   - Mở `https://www.google.com/search?q=...` với từ khóa đời sống ngẫu nhiên (thời tiết, thể thao, công nghệ, du lịch, ẩm thực...).
   - Cuộn nhẹ trang và dừng lại 10 - 15 giây xem kết quả.
   - Đóng tab Google Search.

## 3. Quản lý trạng thái và Dọn dẹp an toàn
- Luôn đặt `stop_gpm_profile(profile_id)` trong khối `finally` để giải phóng tiến trình Chromium và port CDP ngay cả khi gặp sự cố mạng hoặc timeout.
- Cập nhật timestamp `last_nurtured` và `status: "success"` vào file state sau khi hoàn tất.
- Script runner tiêu chuẩn: `D:\Taadaa\GPM auto\scripts\cron_gpm_gmail_nurture.py`.
- Hỗ trợ cờ dòng lệnh: `--email <email>` (chạy canary đơn lẻ) và `--limit <int>`.
