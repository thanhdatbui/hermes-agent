# Farm Cron Coexistence & Automatic Lock Reaper (2026-08-26)

## 1. Cơ Chế Tự Động Phân Luồng Qua Device Lock
- Mọi cron job trên farm (feed runner, feed watcher, sync, night reg) đều được thiết kế để **tự kiểm tra `device_lock`**.
- Khi một tác vụ chạy thủ công (reg, test, recovery) chiếm lock của Máy X:
  - Các cron job định kỳ đến giờ chạy sẽ thấy Máy X đang có lock và **tự động skip máy đó**, tiếp tục vận hành các máy rảnh còn lại.
  - Không bao giờ có sự tranh chấp thiết bị nếu script tuân thủ việc lấy lock.

## 2. Cấm Pause Cron Hệ Thống
- **Nguyên tắc:** Tuyệt đối không pause cron của farm khi chạy lệnh thủ công hay recovery.
- **Hệ quả của việc pause cron:**
  - Vô hiệu hóa `reap-dead-owner-locks`: cron chạy mỗi 15 phút để kiểm tra TTL 2 tiếng (7200s). Nếu máy lỗi/kẹt quá 2h không được can thiệp, script này sẽ tự động thu hồi lock, `am force-stop` TikTok và bấm Home để giải phóng máy.
  - Vô hiệu hóa `device-locks-watchdog`: watchdog cảnh báo Telegram khi có lock bị giữ bất thường.

## 3. Package Name Chuẩn Cho Lệnh Force-Stop
- Package chuẩn của TikTok trên farm là `com.ss.android.ugc.trill`. Mọi lệnh dọn dẹp, watchdog, reap-lock bắt buộc phải bao gồm package này (`am force-stop com.ss.android.ugc.trill`) thay vì chỉ gọi `com.zhiliaoapp.musically`.
