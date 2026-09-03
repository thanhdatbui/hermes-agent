# Quy Tắc Bảo Vệ Cron & Cấm Tự Ý Pause Toàn Hệ Thống

## 1. Cấm Pause Cron Khi Chạy Vận Hành Thủ Công
- Mọi cron nuôi acc, feed runner, reg ban đêm đều có bộ lọc `device_lock` tích hợp (`filter_unlocked_targets`).
- Khi tới lịch, cron tự động bỏ qua máy đang có lock hợp lệ để tiếp tục chạy các máy rảnh khác.
- Việc pause cron của hệ thống là **hành động sai quy chuẩn nghiêm trọng**, làm vô hiệu hóa các cron giám sát an toàn:
  - `reap-dead-owner-locks`: Quét dọn lock chết, tự động force-stop TikTok và đưa máy về Home sau khi hết hạn TTL 2 tiếng.
  - `device-locks-watchdog`: Báo cáo cảnh báo máy kẹt về Telegram.

## 2. Package Name Chuẩn Cho Lệnh Force-Stop / Home
Khi thực hiện force-stop app TikTok trên toàn bộ các dòng máy farm, luôn luôn gọi cho cả 2 package:
```bash
adb -s <serial> shell am force-stop com.ss.android.ugc.trill
adb -s <serial> shell am force-stop com.zhiliaoapp.musically
adb -s <serial> shell input keyevent 3
```
