# Quy Tắc Cooldown Reg Hàng Ngày, Giới Hạn 6 Acc & Cấm Pause Cron (2026-08-26)

## 1. CẤM PAUSE CRON KHI CHẠY THỦ CÔNG HOẶC RECOVERY (User chốt gắt 2026-08-26)
- **Tuyệt đối cấm dùng `cronjob(action='pause')`** đối với bất kỳ cron job nào của farm khi đang chạy tay, test hay recovery.
- **Cơ chế tự động:** Mọi cron định kỳ (`phase9-runner-tiktok-feed`, `night-chain-reg-gmail-tiktok`,...) đều đã tích hợp `filter_unlocked_targets` / `device_lock`. Đến giờ chạy, cron thấy máy nào đang bị lock thủ công thì **tự động skip máy đó** để chạy các máy rảnh còn lại.
- **Hậu quả khi pause cron:**
  - Làm tê liệt `reap-dead-owner-locks` (script quét dọn lock quá hạn TTL 2 tiếng).
  - Làm tê liệt `device-locks-watchdog` (báo cáo cảnh báo kẹt máy).
  - Dẫn đến việc các máy lỗi bị giữ nguyên màn hình đăng ký/OTP suốt nhiều giờ mà không tự động `force-stop` đưa về Home.

## 2. KHÓA CỨNG: 1 MÁY REG TỐI ĐA 1 LẦN / NGÀY (Daily Reg Cooldown)
- **Quy tắc:**
  - Máy nào có kết quả reg `SUCCESS` / `VERIFIED_SUCCESS` hôm nay $\rightarrow$ Ghi nhận ngay vào `C:\Users\Kibe\.codex\device-locks\reg_daily_cooldowns.json` với `cooldown_until` là 00:00 ngày hôm sau.
  - Detector `_detect_clean.py` đọc file này và tự động loại bỏ máy với mã `REG_DAILY_COOLDOWN_ACTIVE`.
  - Máy bị lỗi (`FAILED_EXIT_1`, `FINAL_BLOCKED`, `PENDING`) **không bị cooldown ngày**, cho phép rerun recovery theo danh sách chỉ định.

## 3. CÁCH LY 48H KHI DÍNH RATE LIMIT "TRUY CẬP QUÁ THƯỜNG XUYÊN"
- **Dấu hiệu:** Màn hình đỏ / UI XML có chữ "Bạn truy cập dịch vụ của chúng tôi quá thường xuyên" hoặc "too frequently".
- **Hành động:**
  - Không retry nóng.
  - Ghi vào `D:\Taadaa\runtime\kibe\device_cooldowns.json` với `ttl_hours: 48`.
  - `am force-stop com.ss.android.ugc.trill` và gửi `keyevent 3` (Home) ngay lập tức.

## 4. GIỚI HẠN 6 ACC / MÁY & QUY TRÌNH VÒNG ĐỜI (Lifecycle Batch)
- **Cấu trúc Excel:** Mỗi máy có đúng **6 dòng** trong sheet `Tài Khoản` của master workbook `taikhoan_dat_v2_updated .xlsx` (tổng 480 dòng cho 80 máy).
- **Auto-Exclude:** Khi máy đã có đủ **6 ID TikTok** trong tracking, detector `_detect_clean.py` tự động loại bỏ máy đó vĩnh viễn khỏi các batch reg tiếp theo.
- **Vòng đời mẻ nuôi (75 ngày / 2.5 tháng):**
  - Warmup 14 ngày (lướt feed For You + like/follow nhẹ tự nhiên) $\rightarrow$ Đăng video 2 ngày/lần $\ge 5$ video.
  - Bật follow chéo (25–30 lượt/ngày) $\rightarrow$ Đạt mốc $\ge$ 1,000 follow.
  - Bật 2FA Secret Key (Google Authenticator) $\rightarrow$ Xuất toàn bộ dữ liệu ra Excel bàn giao.
  - Factory Reset máy về mặc định để làm sạch 100% Android ID/GSF/SSAID/Keystore $\rightarrow$ Khởi tạo nuôi lô 6 acc mới toanh.

## 5. RECOVERY PHẢI ĐÚNG DANH SÁCH LỖI, CẤM CHẠY FULL PENDING
- Khi có lỗi ở một batch reg, manifest recovery `_clean_targets.json` phải **chỉ chứa đúng danh sách STT của các máy bị FAILED**.
- Tuyệt đối không để runner tự động gọi lại `_detect_clean.py` để quét lại toàn bộ pending (dẫn đến việc 70+ máy bị chạy đi chạy lại nhiều lần trong ngày gây rate limit).

## 6. PACKAGE NAME CHUẨN KHI REAP LOCK & FORCE STOP
- App TikTok global trên farm sử dụng package **`com.ss.android.ugc.trill`** (song song với `com.zhiliaoapp.musically`).
- Mọi lệnh dọn dẹp, đóng app trong `reap-dead-owner-locks.py` và watchdog bắt buộc phải gọi force-stop cho cả 2 package:
  ```bash
  adb -s <serial> shell am force-stop com.ss.android.ugc.trill
  adb -s <serial> shell am force-stop com.zhiliaoapp.musically
  adb -s <serial> shell input keyevent 3
  ```
