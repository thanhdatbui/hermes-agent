# TikTok Reg Daily Cooldown, Rate-Limit 48h & Recovery Scope Rules (2026-08-26)

## 1. CẤM CHẠY RECOVERY BẰNG FULL DETECT BATCH
- Khi recovery / rerun nhóm máy lỗi sau một batch reg, **TUYỆT ĐỐI KHÔNG** gọi `_run_all_targets.py` chay mà chưa cô lập manifest.
- Lý do: `_run_all_targets.py` luôn gọi `_detect_clean.py` để tìm target, nếu không giới hạn nó sẽ kéo lại toàn bộ 71+ máy pending thành một batch khổng lồ, khiến các máy đã chạy bị reg lại nhiều lần.
- **Quy tắc:** Bắt buộc tạo manifest hẹp `_clean_targets.json` chỉ chứa đúng danh sách STT lỗi cần xử lý và đảm bảo runner đọc đúng file đó.

## 2. ÉP COOLDOWN 1 MÁY / 1 LẦN / NGÀY
- **Contract:** Mỗi máy vật lý chỉ được reg tối đa 1 nick thành công mỗi ngày.
- Khi một máy đạt `SUCCESS` / `VERIFIED_SUCCESS`:
  - Ghi nhận trạng thái vào `C:\Users\Kibe\.codex\device-locks\reg_daily_cooldowns.json` với `reg_success_date = TODAY` và `cooldown_until = TOMORROW 00:00`.
  - `_detect_clean.py` / `filter_unlocked_targets` phải tự động loại bỏ máy này với lý do `REG_DAILY_COOLDOWN_ACTIVE` (`status=temporarily_skipped`).
  - Không ghi cooldown cho máy `PENDING`, lỗi UI, timeout hay `handoff`.

## 3. XỬ LÝ RATE-LIMIT "TRUY CẬP QUÁ THƯỜNG XUYÊN" (COOLDOWN 48H)
- Khi phát hiện màn hình đỏ "Bạn truy cập dịch vụ của chúng tôi quá thường xuyên" (hoặc "too frequently"):
  - **CẤM retry nóng!** Càng bấm retry càng bị TikTok gắn cờ thiết bị/IP.
  - Ghi nhận ngay vào file `D:\Taadaa\runtime\kibe\device_cooldowns.json` với TTL 48 giờ (`ttl_hours: 48`).
  - Lập tức thực hiện `am force-stop` ứng dụng TikTok và gửi `input keyevent 3` (Home) để giải phóng màn hình máy.

## 4. CHUẨN HÓA PACKAGE NAME TIKTOK FARM
- Trên toàn bộ dàn máy farm Android, TikTok chạy dưới package name chính thức: **`com.ss.android.ugc.trill`** (song song một số bản cũ `com.zhiliaoapp.musically`).
- Mọi script watchdog, cleanup, lock-reaper khi kill TikTok bắt buộc phải gọi cả 2 package để tránh tình trạng máy bị treo màn hình quá 2h TTL mà script reaper không tắt được app.
