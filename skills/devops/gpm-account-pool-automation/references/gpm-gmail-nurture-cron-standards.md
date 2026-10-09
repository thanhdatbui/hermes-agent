# Hermes Cron GPM Gmail Nurture: Logging, Watchdog Silent & Acceptance Media Standards

Tài liệu hướng dẫn quy chuẩn xây dựng và tối ưu các script cron tự động hoá trên GPM (điển hình: `cron_gpm_gmail_nurture.py`).

## 1. Nguyên tắc tách biệt Logging và Stdout

Hermes Cron runner bắt toàn bộ `stdout` để gửi thông báo/báo cáo về kênh chat (Telegram/Hermes feed). Do đó:
- **Tuyệt đối KHÔNG dùng `StreamHandler(sys.stdout)`** cho các logger chi tiết (CDP, Playwright step-by-step, start/stop profile, sleep delays).
- Toàn bộ log chi tiết phải ghi vào file log qua `RotatingFileHandler`:
  ```python
  import os
  from logging.handlers import RotatingFileHandler

  LOG_DIR = r"D:\Taadaa\GPM auto\logs"
  LOG_FILE = os.path.join(LOG_DIR, "cron_gpm_gmail_nurture.log")
  os.makedirs(LOG_DIR, exist_ok=True)

  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(levelname)s] %(message)s",
      handlers=[
          RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
      ]
  )
  logger = logging.getLogger("gpm_gmail_nurture")
  ```

## 2. Tiêu chuẩn Silent Watchdog (Khi không có task đến hạn)

Khi script chạy định kỳ để quét trạng thái (state file / interval check):
- Nếu **không có profile nào cần xử lý** (`not target_profiles`):
  - Ghi log `logger.info("Không có profile nào cần nuôi trong tick này...")` vào file log.
  - **KHÔNG print bất kỳ ký tự nào ra `sys.stdout`** (để stdout rỗng hoàn toàn).
  - Thoát sạch (exit 0 / return).
  - *Ý nghĩa:* Hermes cron runner sẽ không kích hoạt notification rác khi hệ thống ở trạng thái bình thường/chưa tới lịch.

## 3. Báo cáo nghiệm thu & Kỷ luật CẤM in MEDIA: trong Cron Nuôi

- **Kỷ luật CẤM in MEDIA:** Cron nuôi GPM tuyệt đối KHÔNG in tiền tố `MEDIA:<path>` ra stdout/Telegram. Toàn bộ ảnh screenshot (`nurture_{email}.png`) chỉ lưu nội bộ tại `D:\Taadaa\GPM auto\debug_screenshots` sau khi video phát ổn định >= 25s để tra cứu O(1) khi cần debug.
- **Định dạng stdout:** Khi có profile được xử lý và hoàn tất phiên chạy, script chỉ in báo cáo ngắn gọn (summary text) hoặc để im lặng hoàn toàn. Tuyệt đối không để `StreamHandler(sys.stdout)` in chi tiết log trung gian.

## 4. Quy tắc Cấu hình Cronjob: BẮT BUỘC `deliver: "local"` (CẤM SPAM Farm Alert)

- **Cấu hình `deliver`:** Job cron `gpm-gmail-nurture-watchdog` chạy trên PC định kỳ 2 tiếng/lần BẮT BUỘC phải đặt `deliver: "local"`.
- **CẤM gửi Farm Alert:** Tuyệt đối KHÔNG cấu hình `deliver: "telegram:-5373649734"` hay bất kỳ kênh chat nào cho cron nuôi GPM. Kênh Farm Alert là kênh vận hành thiết bị nghiêm ngặt, chỉ nhận cảnh báo checkpoint/sự cố farm hoặc báo cáo chốt ca. Mọi hành vi để cron nuôi PC bắn log/summary vào Farm Alert đều bị coi là SPAM nghiêm trọng.

## 5. Quy tắc đồng bộ Dual-Location (Production Script Sync)

Các script cron phục vụ Hermes trên máy Kibe phải luôn được cập nhật đồng bộ 2 vị trí:
1. `D:\Taadaa\GPM auto\scripts\<script_name>.py` (Thư mục repo/làm việc chính của GPM).
2. `C:\Users\Kibe\AppData\Local\hermes\scripts\<script_name>.py` (Thư mục runtime/cron của Hermes).
3. Luôn chạy cú pháp `python -m py_compile` trên cả hai file sau khi chỉnh sửa/đồng bộ để đảm bảo không có lỗi cú pháp.

## 6. Phân bổ Tỷ lệ Hành vi Thực tế (Dynamic Behavioral Entropy)

Không rập khuôn profile nào cũng thực hiện đủ 3 tác vụ (dễ bị Google phạt bot pattern). Bắt buộc phân chia kịch bản theo tỷ lệ xác suất:
- **50% lượt nuôi (Hành vi giải trí):** CHỈ xem YouTube (1 video 90-120s, xử lý skip ad thông minh, like/scroll nhẹ).
- **30% lượt nuôi (Hành vi đọc tin tức):** Đọc Google News (45-60s, cuộn bài báo) + sau đó Search Google 1 từ khóa (15-20s). Tuyệt đối KHÔNG mở YouTube.
- **20% lượt nuôi (Hành vi hỗn hợp):** Xem YouTube + Đọc Google News hoặc Search Google (làm tuần tự 2 việc, thứ tự ngẫu nhiên).
- Dù rơi vào kịch bản nào, ảnh debug `nurture_{email}.png` chỉ lưu cục bộ tại thư mục debug_screenshots, tuyệt đối không in MEDIA: ra Telegram.

## 7. Quản lý Tab Tuần tự (Sequential Tab Lifecycle)

- **Nguyên tắc 1 Tab duy nhất:** Trình duyệt tại mỗi thời điểm chỉ được duy trì DUY NHẤT 1 tab hoạt động (`context.pages[0]`).
- Tuyệt đối không mở đồng thời 2-3 tab chạy ngầm (YouTube chạy ngầm trong khi đọc báo/search gây ngốn RAM/CPU và lộ rõ dấu hiệu bot).
- Cơ chế chuyển tab an toàn:
  - Khi click bài báo trên Google News mở tab mới (`target="_blank"`), lập tức gọi `news_page.close()` để chỉ giữ lại tab bài báo.
  - Giữa các tác vụ, tái sử dụng tab bằng `page.goto()` hoặc dọn sạch tab thừa bằng hàm `cleanup_extra_tabs(context, keep_page)`.

## 8. Đóng dứt điểm Profile GPM (Hard Process Cleanup)

Để tránh hiện tượng profile GPM bị treo hoặc đọng lại icon dưới thanh taskbar sau khi cron kết thúc:
1. **Chuẩn hóa API đóng profile:** Hàm `stop_gpm_profile(profile_id)` phải gọi:
   - `GET /api/v3/profiles/close/{profile_id}`: endpoint chuẩn của GPM v3.
   - `GET /api/v3/profiles/stop/{profile_id}`: fallback phụ trợ.
2. **Khối `finally` bảo đảm:**
   - Đóng `context.close()` và `browser.close()`.
   - Gọi `stop_gpm_profile(p_id)`.
   - Chờ 2s kiểm tra trạng thái thực tế (qua socket debug port hoặc `psutil` tìm tiến trình Chrome với `--remote-debugging-port` và `--user-data-dir`).
   - Nếu tiến trình vẫn còn chạy sau 2s, bắt buộc gọi force kill dứt điểm bằng `p.terminate()` / `p.kill()`.

