# Quy tắc Vận Hành Reg TikTok, Cooldown 1 Ngày & An Toàn Cron (2026-08-26)

## 1. CẤM PAUSE CRON KHI CHẠY THỦ CÔNG HOẶC RECOVERY
- **Nguyên tắc cốt lõi:** Tuyệt đối KHÔNG ĐƯỢC dùng `cronjob pause` hoặc tắt cron của farm khi chạy lệnh tay, chạy batch reg hay recovery.
- **Cơ chế tự bảo vệ của Cron:** Mọi runner/cron định kỳ (nuôi acc, feed session, reg đêm) đều đã tích hợp `filter_unlocked_targets` / `device_lock`. Khi tới giờ chạy, cron tự động bỏ qua (skip) các máy đang có lock hợp lệ và chạy các máy rảnh còn lại.
- **Hậu quả nghiêm trọng nếu pause cron:**
  - Làm chết `device-locks-watchdog` (mất cảnh báo kẹt máy về Telegram).
  - Làm chết `reap-dead-owner-locks` (vô hiệu hóa cơ chế tự động giải phóng lock quá hạn TTL 2 tiếng và tự động force-stop đưa máy về Home).
  - Khiến máy bị kẹt màn hình lỗi/OTP/rate-limit nhiều giờ liền không người xử lý.

## 2. GIỚI HẠN REG 1 LẦN / NGÀY / MÁY (DAILY COOLDOWN)
- **Mục tiêu:** Chống TikTok quét tần suất đăng ký trên cùng thiết bị (tránh dính banner "Bạn truy cập dịch vụ của chúng tôi quá thường xuyên").
- **Cơ chế:**
  - Máy đăng ký `SUCCESS` hôm nay $\rightarrow$ Ghi nhận vào `C:\Users\Kibe\.codex\device-locks\reg_daily_cooldowns.json` với `cooldown_until` = ngày hôm sau (00:00).
  - Detector `_detect_clean.py` khi quét sẽ loại bỏ các máy này với lý do `REG_DAILY_COOLDOWN_ACTIVE` (status: `temporarily_skipped`), không bao giờ cấp phát mail mới để lập batch.
  - Lỗi / `PENDING` $\rightarrow$ KHÔNG cooldown theo ngày.
  - Phát hiện rate-limit ("truy cập quá thường xuyên") $\rightarrow$ Cách ly Cooldown 48 giờ vào `D:\Taadaa\runtime\kibe\device_cooldowns.json`.

## 3. KHÓA PHẠM VI RECOVERY (RECOVERY SCOPE LOCK)
- **CẤM MỞ RỘNG BATCH:** Khi recovery lỗi, BẮT BUỘC chỉ chạy đúng danh sách STT máy lỗi thực tế (lấy từ `all_results.json` của run trước).
- **Tuyệt đối không gọi `_detect_clean.py` để lấy lại toàn bộ pending targets** vì sẽ vô tình biến recovery thành full-batch (chạy lại hàng chục máy đã thành công hoặc máy không liên quan).

## 4. DUNG LƯỢNG MÁY & CHU KỲ 6 ACC / MÁY
- Mỗi máy nuôi tối đa **6 accounts** (cấu trúc Master Sheet `taikhoan_dat_v2_updated .xlsx` chuẩn 6 dòng/máy = 480 dòng/80 máy).
- Khi một máy đã đủ 6 ID TikTok $\rightarrow$ Detector tự động LOẠI BỎ máy đó khỏi mọi kế hoạch reg.
- Vòng đời: 6 acc nuôi luân phiên 3 ca chẵn/lẻ $\rightarrow$ Đạt $\ge 1,000$ follow $\rightarrow$ Bật 2FA TOTP Key $\rightarrow$ Xuất Excel $\rightarrow$ Factory Reset máy để bắt đầu mẻ 6 acc mới.

## 5. PACKAGE NAME TRONG CLEANUP VÀ REAPER
- TikTok Global trên farm sử dụng package **`com.ss.android.ugc.trill`**.
- Mọi script cleanup, recovery, watchdog, reaper bắt buộc phải gửi lệnh force-stop cho cả `com.ss.android.ugc.trill` và `com.zhiliaoapp.musically` cùng phím Home (`keyevent 3`).
