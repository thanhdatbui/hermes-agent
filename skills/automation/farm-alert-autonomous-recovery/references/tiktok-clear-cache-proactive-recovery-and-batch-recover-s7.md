# TikTok Clear Cache Failures & Proactive Auto-Recovery Pipeline

> Ref: `cron_clear_tiktok_cache.py`, `batch_recover_s7.py`, `recover_stuck_s7.py`, `inspect_machine.py`.

## 1. Pitfall: Passive Reporting vs Autonomous Recovery ("Fix Đi Chứ")
- **Antipattern**: Nhận báo cáo dọn cache có máy lỗi (Timeout, WIDGET_MISS), tóm tắt xong buông thõng: *"Khi cần xử lý, anh nhắn..."*.
- **Directive**: Farm Alert hoặc báo cáo cronjob có thiết bị lỗi BẮT BUỘC tự động kích hoạt cứu hộ phục hồi ngay lập tức, không chờ user nhắc "Fix đi chứ".

## 2. Standard Rapid Recovery Protocol
Khi có máy lỗi dọn cache TikTok:
1. **Chạy cứu hộ phân tầng cấp tốc qua batch_recover_s7.py**:
   - Cụm Kibe Local:
     `python D:/Taadaa/tools/batch_recover_s7.py --cluster kibe --machines <list_máy_lỗi>`
   - Cụm Admin Remote:
     `python D:/Taadaa/tools/batch_recover_s7.py --cluster admin --machines <list_máy_lỗi>`
   - `batch_recover_s7.py` thực thi Level 1 Soft Recovery (`am force-stop com.ss.android.ugc.trill`, `input keyevent 223 KEYCODE_SLEEP`, verify ping) giải phóng I/O và ADB socket chỉ trong ~2 giây.
2. **Nghiệm thu O(1) qua inspect_machine.py**:
   - Kiểm tra xác nhận máy đã về `LauncherActivity`, IP và proxy sống:
     `python D:/Taadaa/tools/inspect_machine.py <N>`
3. **Re-run Cronjob dọn cache cho máy hoàn tất**:
   - Gọi `cronjob(action='run', job_id='79021fa79d8b')` để dọn bù cache ngay trong ca rảnh.
