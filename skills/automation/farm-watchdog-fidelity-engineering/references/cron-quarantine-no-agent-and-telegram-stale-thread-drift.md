# Cron Quarantine (Missing no_agent=True) & Telegram Stale Thread Delivery Drift

## 1. Sự Cố 1: Heavy Automation Script Kẹt Trong LLM Agent Cron (`no_agent=False`)

### Hiện Tượng:
- Cron job định kỳ (ví dụ `cron-auto-feed-chatgpt-pool` - ID `3269c6faeb03`) liên tục báo trạng thái `last_status: error`.
- Hoặc các job tương tự bị cơ chế giám sát tự động gắn cờ vô hiệu hóa:
  `paused_reason: AUTO_QUARANTINE: Cronjob missing no_agent=True` (như `chatgpt-account-lifecycle-healer` - ID `8b9ef68ac4ab`).

### Nguyên Nhân Gốc Rễ:
- Khi tạo cron job chạy script bằng prompt:
  ```json
  {
    "name": "cron-auto-feed-chatgpt-pool",
    "prompt": "Chạy lệnh: python \"D:/Taadaa/GPM auto/scripts/cron_auto_feed_chatgpt_pool.py\" Đọc stdout và tóm tắt...",
    "no_agent": false
  }
  ```
- Scheduler sẽ spawn một LLM Agent phiên con mỗi tick. Các script cứu hộ tài nguyên, duyệt profile GPMLogin, Playwright mở browser và giải captcha thường tốn 3–10 phút, vượt xa ngưỡng timeout của Agent (180s) $\to$ Agent bị kill giữa chừng $\to$ Job dính `error` và lãng phí token LLM vô ích.

### Invariant & Chuẩn Hóa Bắt Buộc:
- **TẤT CẢ các script tự động hóa, giải cứu tài nguyên, watchdog và batch job BẮT BUỘC dùng `no_agent=True`:**
  ```json
  {
    "action": "update",
    "job_id": "<job_id>",
    "no_agent": true,
    "script": "cron_auto_feed_chatgpt_pool.py",
    "prompt": ""
  }
  ```
- Tuyệt đối không để LLM Agent làm wrapper trung gian cho các script chạy nặng.

---

## 2. Sự Cố 2: Lệch Mã Telegram Topic/Thread Khi Giao Tin Cron (`thread_id not found`)

### Hiện Tượng:
- Cron job chạy thành công (`last_status: ok`) nhưng kèm theo cảnh báo giao nhận lặp đi lặp lại:
  `last_delivery_error: configured thread_id 245405 for telegram:1076231895 was not found; delivered without thread_id`

### Nguyên Nhân:
- Job được tạo từ một phiên chat Telegram có bật forum/topic thread tạm thời (`thread_id`).
- Khi topic đó bị đóng, xóa hoặc hết hạn, Hermes vẫn tìm cách nhắm đến `thread_id` cũ. Dù hệ thống có cơ chế fallback tự gửi về root chat, warning vẫn sinh ra trong state của job và làm bẩn telemetry.

### Cách Khắc Phục:
- Khi cấu hình trường `deliver` cho các cron job báo cáo định kỳ:
  - Nếu gửi về DM của User: Chỉ để `origin` hoặc `telegram:1076231895` (bỏ `:thread_id` phía sau).
  - Nếu gửi về Channel/Group cố định của Farm: Dùng chat ID cố định của Group, ví dụ:
    - Báo cáo Farm Alert: `telegram:-5373649734`
    - Báo cáo TikTok Follow: `telegram:-5127276494`
    - Báo cáo TikTok Feed: `telegram:-5377611430`
    - Báo cáo GPM: `telegram:-5256944036`
