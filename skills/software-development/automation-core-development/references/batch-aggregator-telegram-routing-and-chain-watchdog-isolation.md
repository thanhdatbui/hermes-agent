# Batch Aggregator Telegram Routing & Chain Watchdog Isolation

## 1. Batch Aggregator Telegram Routing Contract
Khi `batch_aggregator.py` phát hiện lỗi lan rộng (systemic failure) và được kích hoạt cờ `--telegram`:
- CẤM TUYỆT ĐỐI gán cứng `chat_id = DEFAULT_ALERT_CHAT_ID` (`-5373649734` Farm Alerts).
- BẮT BUỘC gọi `_resolve_script_chat_id(script_name)` từ `automation_core.alerts` để giải quyết `target_chat_id` theo đúng nhóm repo phụ trách:
  + `register-gmail` / `reg_gmail` -> `-5139245637` (Gmai reg)
  + `tiktok-add-2fa` / `2fa` -> `-5468653590` (Tiktok add 2fa)
  + `feed` -> `-5377611430` (Tiktok Luot Nuoi Acc)
  + `upload` / `avatar` -> `-5435853713` (Tiktok video)
  + `follow` -> `-5127276494` (Tiktok Follow)
  + Chỉ fallback về `DEFAULT_ALERT_CHAT_ID` (`-5373649734`) khi `script_name` không khớp bất kỳ alias nào.

## 2. Chain Watchdog (Chuỗi liên hoàn đa Phase) & Hermes Cron Deliver Guard
Khi một script Watchdog thực thi chuỗi liên hoàn nhiều Phase thuộc các repo khác nhau (ví dụ: `post_noon_chain_watchdog.py` hoặc `cron_night_tiktok_2fa_watchdog.py` chạy Phase 1: Reg Gmail -> Phase 2: Add 2FA TikTok):
1. **Tránh bẫy Hermes Cron deliver:**
   - Trong `jobs.json`, cấu hình `deliver` BẮT BUỘC là `local` (hoặc omit target chung).
   - Nếu để `deliver: telegram:-5373649734`, Hermes sẽ bắt stdout của toàn bộ chuỗi và ném về Farm Alerts, phá vỡ cấu trúc phân luồng theo nhóm.
2. **Dispatch độc lập từng Phase trong Python script:**
   - Từng Phase sau khi hoàn tất tự gọi hàm gửi Telegram chuyên trách:
     + Phase Reg Gmail: dispatch report về `GMAIL_REPORT_CHAT_ID = "-5139245637"`
     + Phase Add 2FA TikTok: dispatch report về `TIKTOK_REPORT_CHAT_ID = "-5468653590"`
   - Sử dụng `_send_telegram_text` từ `automation_core.alerts`.
3. **Chống treo claim lane / cờ tiến trình ban đêm:**
   - Kiểm tra quỹ thời gian trước các mốc cấm (`ROLLING_BLOCK_WINDOWS` / reboot 05:20): nếu thời gian còn lại < 45 phút, cấm spawn batch 2FA mới.
   - Khi có crash hoặc tiến trình bị ngắt ngoài ý muốn, cần cơ chế giải phóng `running_since` TTL an toàn.
