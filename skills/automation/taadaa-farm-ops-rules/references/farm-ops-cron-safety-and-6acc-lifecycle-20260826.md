# Quy tắc Vận Hành Farm TikTok 160 Máy: Quản Lý 6 Acc/Máy, Chu Kỳ Nuôi, Jitter & An Toàn Cron (2026-08-26)

## 1. CẤM PAUSE CRON KHI CHẠY THỦ CÔNG HOẶC RECOVERY
- **CẤM DÙNG `cronjob pause` đối với các cron của farm khi chạy test, chạy tay hay recovery.**
- Mọi cron (nuôi acc, feed session, reg đêm) đã có cơ chế tự lọc `device_lock` để skip các máy đang bận và chạy tiếp máy rảnh.
- Việc pause cron sẽ làm chết watchdog và script dọn dẹp giải phóng lock quá hạn (TTL 2h), khiến máy kẹt màn hình lỗi/OTP/rate-limit nhiều giờ liền không người xử lý.

## 2. QUY TRÌNH NUÔI 6 ACC / MÁY VÀ VÒNG ĐỜI BATCH 75 NGÀY
- **Cấu hình:** Mỗi máy nuôi cố định **6 acc** (chia 6 slot trong file master).
- **Phân bổ chạy 1 ngày 3 ca (mỗi ca 1 acc duy nhất):**
  - Ngày chẵn: Chạy Slot 1 (Ca 1), Slot 2 (Ca 2), Slot 3 (Ca 3).
  - Ngày lẻ: Chạy Slot 4 (Ca 1), Slot 5 (Ca 2), Slot 6 (Ca 3).
  - Mỗi acc được chạy và đăng video 1 lần mỗi 48 giờ (2 ngày 1 lần).
- **Lộ trình phát triển:**
  - **14 ngày đầu (Warmup):** Lướt For You tự nhiên 10-15 phút/phiên, like nhẹ 2-4 video, follow 1 creator lớn. Đăng đều 2 ngày/video (đạt $\ge 5$ video để qua Video Gate). Không follow chéo nội bộ.
  - **55-60 ngày tiếp theo (Tăng tốc):** Tiếp tục đăng video đều đặn (đạt 30-40 video/acc) + Bật follow chéo nội bộ (25-30 lượt follow/acc/ca hoạt động).
  - **Cán mốc $\ge 1,000$ follow:** Bật 2FA TOTP Secret Key (Authenticator) $\rightarrow$ Xuất toàn bộ thông tin tài khoản ra Excel bàn giao.
  - **Factory Reset:** Xóa sạch dữ liệu máy, Factory Reset máy về mặc định để triệt tiêu toàn bộ hardware fingerprint cũ $\rightarrow$ Khởi tạo reg và nuôi lô 6 acc mới từ đầu.

## 3. CƠ CHẾ DAILY REG COOLDOWN & 48H RATE-LIMIT COOLDOWN
- **Daily Cooldown:** Máy nào đăng ký `SUCCESS` hôm nay $\rightarrow$ Ghi nhận vào `C:\Users\Kibe\.codex\device-locks\reg_daily_cooldowns.json` để detector tự động skip máy đó cho tới ngày hôm sau (00:00). Mỗi máy chỉ reg tối đa 1 lần/ngày.
- **48H Rate-limit Cooldown:** Khi máy dính banner "Bạn truy cập dịch vụ của chúng tôi quá thường xuyên" $\rightarrow$ Ghi nhận vào `D:\Taadaa\runtime\kibe\device_cooldowns.json` với TTL 48 giờ. Tuyệt đối không retry nóng vào máy đang bị rate-limit.
- **Dung lượng tối đa:** Máy đã có đủ 6 ID TikTok $\rightarrow$ Detector tự động LOẠI BỎ máy đó khỏi danh sách reg, không cấp phát thêm mail.

## 4. PACKAGE NAME CHUẨN TRONG CLEANUP & REAPER
- TikTok Global trên farm sử dụng package **`com.ss.android.ugc.trill`**.
- Mọi script cleanup, recovery, watchdog, reaper bắt buộc phải gửi lệnh force-stop cho cả `com.ss.android.ugc.trill` và `com.zhiliaoapp.musically` cùng phím Home (`keyevent 3`).
