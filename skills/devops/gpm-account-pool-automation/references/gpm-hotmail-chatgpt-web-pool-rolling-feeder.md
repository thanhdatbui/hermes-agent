# Hotmail ChatGPT Web Pool Feeder (5 Workers Rolling Automation)

## Bối cảnh & Vấn đề
- Kho GPM có hơn 460 profile `@hotmail.com` đã đăng ký và đăng nhập ChatGPT web từ trước (`__Secure-next-auth.session-token` live), nhưng các script cũ (`batch_chatgpt_web_5workers.py`, `batch_rescue`) bị hardcode regex lọc `re.search(r'@gmail\.com')` nên bỏ sót toàn bộ kho Hotmail.
- Cần cơ chế nạp tự động định kỳ (cron), cuốn chiếu 5 worker song song, lấy token và gán proxy Mobi 1-1 fail-closed, sau đó đóng sạch 100% profile.

## Kiến trúc Script & Cron
1. **Script:** `D:/Taadaa/GPM auto/scripts/cron_auto_feed_chatgpt_pool.py`
   - **Concurrency:** `ThreadPoolExecutor(max_workers=5)` xử lý 5 profile đồng thời.
   - **Dynamic Candidates:** Truy vấn SQLite GPM (`profile_data.db` read-only) lấy profile `@hotmail.com` / `@gmail.com` mang port proxy hợp lệ (`5101..5138` hoặc `10001..10007`) chưa active trong OmniRoute (`storage.sqlite`). Ưu tiên Hotmail vì đã lưu cookie sẵn.
   - **Token Guard:** Chỉ chấp nhận cookie có tên chứa `session-token` (tránh token tạm của `auth.openai.com` chưa đăng nhập).
   - **Fail-Closed Proxy:** Tra cứu `proxy_registry` đúng `host:port` (Mobi host `test.taadaa.click`, username `mobi<port-5100>`, pass chuẩn), bắt buộc INSERT/UPDATE `proxy_assignments` trước khi kích hoạt `is_active = 1`.
   - **Cleanup Guard (Đóng sạch profile 100%):** Trong khối `finally`, luôn gọi:
     1. GPM API `GET /profiles/stop/{pid}`.
     2. Kill sạch tiến trình `chrome.exe` theo `profile_path` bằng `psutil` để chống rò rỉ RAM/CPU.
   - **Lock Guard:** Sử dụng file lock `cron_auto_feed_chatgpt_pool.lock` (kiểm tra mtime < 300s) để chống chạy đè giữa các tick.

2. **Cronjob:** `cron-auto-feed-chatgpt-pool` (ID: `3269c6faeb03`)
   - Schedule: `*/15 * * * *` (mỗi 15 phút chạy 1 batch 10 profiles).
   - Delivery: `local` (ghi log ngầm, không spam Telegram).
   - Workdir: `D:\Taadaa\GPM auto\scripts`.
