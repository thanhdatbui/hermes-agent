# Quy Tắc Phân Luồng Telegram Alert Theo Repo & Script

## 1. Nguyên Tắc Cốt Lõi
- **Đúng nhóm, đúng repo:** Cảnh báo (Farm Alert / Machine Alert / Script Alert / Cron Watchdog Report) của quy trình hoặc repo nào BẮT BUỘC gửi về nhóm Telegram riêng của repo đó.
- **Không spam Farm Alerts:** Nhóm chung `Farm Alerts` (`-5373649734`) CHỈ dành riêng cho các tác vụ hạ tầng cấp farm không thuộc repo riêng (dọn cache toàn farm, reboot PC, sync mây OneDrive đa luồng, hoặc các script không xác định).

## 2. Bảng Định Tuyến Telegram Group Sinks

| Quy trình / Repo | Script & Alert liên quan | Nhóm Telegram | Chat ID |
| :--- | :--- | :--- | :--- |
| **Nuôi Acc / Lướt Feed** (`tiktok-luot nuoi acc`) | • Cron `tiktok-feed-session-watchdog` (`feed_session_watchdog.py`)<br>• Farm Alert từ `multi_machine_feed_session` | **Tiktok Luot Nuoi Acc** | `-5377611430` |
| **Upload Video & Avatar** (`Tiktok-video`) | • Cron `farm-render-download-watchdog`<br>• Watchdog `post_evening_avatar_watchdog.py`<br>• Alert máy khi chạy upload/avatar | **Tiktok video** | `-5435853713` |
| **Bật 2FA TikTok** (`tiktok-add-bao-mat-f2a`) | • Cron `night-tiktok-2fa-watchdog`<br>• Alert máy khi chạy 2FA TikTok | **Tiktok add 2fa** | `-5468653590` |
| **Follow TikTok** (`tiktok-follow`) | • Alert máy & flow `tiktok-follow` | **Tiktok Follow** | `-5127276494` |
| **Đăng Ký TikTok** (`Tiktok_Reg`) | • Alert máy & flow `Tiktok_Reg` | **Tikok Reg** | `-5494641602` |
| **Đăng Ký Gmail** (`register gmail`) | • Alert máy & flow `register gmail` | **Gmai reg** | `-5139245637` |
| **Đăng Nhập TikTok** (`tiktok-log-in`) | • Alert máy & flow `tiktok-log-in` | **Tiktok Log In** | `-5145780745` |
| **GPM Automation** (`GPM auto`) | • Toàn bộ cụm cron report & nurture GPM | **GPM Auto** | `-5256944036` |
| **Hotmail Automation** (`Hotmail`) | • Cron `hotmail-gpm-lifecycle-6h-report` | **hotmail** | `-5583559484` |
| **Gán Proxy** (`gan-proxy`) | • Alert liên quan proxy / Android VPN | **gan proxy** | `-5468841134` |
| **Automation Core** (`automation-core`) | • Alert lõi hệ thống automation-core | **Automation Core** | `-5331653038` |
| **Hạ tầng chung Farm** | • `cron_clear_tiktok_cache`<br>• `farm_scheduled_reboot`<br>• `sync_onedrive_multicloud` | **Farm Alerts** | `-5373649734` |

## 3. Kiến Trúc Trong `automation_core.alerts`
- `_SCRIPT_METADATA` trong `alerts.py` chứa thuộc tính `"chat_id"` tương ứng cho từng quy trình (`feed`, `avatar`, `upload`, `follow`, `2fa`, `reg_tiktok`, `reg_gmail`, `login`, `gpm`, `hotmail`, `proxy`, `automation_core`).
- Helper `_resolve_script_chat_id(script_name)` tự động ánh xạ script name về nhóm đích. Nếu không tìm thấy, mới fallback về `DEFAULT_ALERT_CHAT_ID` (`-5373649734`).
- Các hàm `send_farm_machine_alert` và `send_farm_script_alert` tự động phân giải `target_chat_id` khi caller truyền `chat_id=DEFAULT_ALERT_CHAT_ID` hoặc `None`.
