# Multi-Phase Chain Watchdog & Batch Aggregator Telegram Routing

## 1. Bối cảnh & Nguyên nhân lỗi (Root Cause)
Khi vận hành chuỗi liên hoàn (Chain Watchdog) trên Farm:
- **Ca trưa (`post_noon_chain_watchdog.py`)**: Phase 1 = Reg Gmail $\to$ Phase 2 = Add 2FA TikTok.
- **Ca đêm (`cron_night_tiktok_2fa_watchdog.py`)**: Phase 1 = Reg Gmail $\to$ Phase 2 = Add 2FA TikTok.

Xảy ra 3 lỗi phổ biến khiến báo cáo không về đúng nhóm Telegram của repo:
1. **Gom chung stdout đẩy về 1 chat:** Watchdog in toàn bộ text các phase ra stdout, trong khi cronjob cấu hình `deliver: telegram:-5373649734` (Farm Alerts). Hermes cron tự động đẩy cả cục về Farm Alerts.
2. **Hardcode `DEFAULT_ALERT_CHAT_ID` trong `batch_aggregator.py`:** Khi `register gmail` hay `run_batch_live_2fa` gọi `batch_aggregator --telegram` để báo cáo lỗi hàng loạt, `batch_aggregator.py` gán cứng `DEFAULT_ALERT_CHAT_ID = -5373649734` thay vì phân giải theo script.
3. **Kẹt cờ claim lane sau crash/reboot:** Cờ `tiktok_running_since` hoặc `gmail_running_since` trong state file bị treo quá TTL khi máy reboot đột ngột hoặc chạm khung cấm rolling block, khiến các tick sau từ chối chạy.

## 2. Giải pháp kỹ thuật chuẩn hóa (Pattern & Invariants)

### A. Tách biệt báo cáo từng Phase (Per-Phase Dispatch)
Trong script chain watchdog (`post_noon_chain_watchdog.py`, `cron_night_tiktok_2fa_watchdog.py`):
- Mỗi phase độc lập gọi `dispatch_report()` gửi riêng về chat_id tương ứng:
  - **Reg Gmail**: Nhóm **Gmai reg** (`-5139245637`).
  - **Add 2FA TikTok**: Nhóm **Tiktok add 2fa** (`-5468653590`).
- Cấu hình cronjob trong `jobs.json`:
  - **BẮT BUỘC ĐỂ `deliver: local`** đối với chain watchdog có cơ chế tự gửi Telegram nội bộ.
  - Tuyệt đối không để `deliver: telegram:...` tránh việc Hermes bắt stdout và gửi thêm 1 tin nhắn gom gộp vào nhóm khác.

### B. Dynamic Script Resolution trong `batch_aggregator.py`
Tại các vị trí phát hiện lỗi hệ thống cần gửi alert (`args.telegram and should_alert`):
```python
from automation_core.alerts import (
    DEFAULT_ALERT_CHAT_ID,
    _load_bot_token,
    _resolve_script_chat_id,
    _send_telegram_photo,
    _send_telegram_text,
)
token = _load_bot_token()
chat_id = _resolve_script_chat_id(script_name) if script_name else DEFAULT_ALERT_CHAT_ID
```
Điều này đảm bảo khi CLI truyền `--script register-gmail` hoặc `--script tiktok-add-2fa`, alert lỗi lô sẽ về thẳng nhóm chuyên trách của quy trình đó.

### C. Cơ chế kiểm tra và dọn cờ kẹt State
Khi điều tra cron không gửi báo cáo hoặc im lặng kéo dài:
1. Đọc state file (`night_tiktok_2fa_state.json` hoặc `post_noon_chain_state.json`).
2. Kiểm tra nếu có trường `*_running_since` còn tồn tại trong khi tiến trình thực thi không còn trên hệ điều hành (`psutil` check sạch): Xóa bỏ cờ đó ngay để giải phóng lane.
