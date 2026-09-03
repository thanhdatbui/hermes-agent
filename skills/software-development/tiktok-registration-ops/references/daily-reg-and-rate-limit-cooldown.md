# Rate-Limit & Daily Reg Cooldown Rules (User Enforcement 2026-08-26)

## 1. Quy tắc 1 máy / 1 lần / ngày (Bắt buộc)
- Mỗi máy chỉ được reg thành công tối đa 1 lần/ngày.
- Khi flow đạt `SUCCESS` hoặc `VERIFIED_SUCCESS`, hệ thống ghi nhận vào:
  `C:\Users\Kibe\.codex\device-locks\reg_daily_cooldowns.json`
  với `cooldown_until` là `00:00` ngày hôm sau (`date.today() + timedelta(days=1)`).
- `_detect_clean.py` / `filter_unlocked_targets` phải tự động skip các máy này trước khi lập batch:
  `reason: REG_DAILY_COOLDOWN_ACTIVE`, `owner_status: temporarily_skipped`.
- Không ghi cooldown cho `PENDING` hoặc lỗi UI/timeout (máy lỗi được phép retry nếu đúng quy trình).

## 2. Quy tắc Recovery đúng phạm vi (Chống cháy farm)
- Khi thực hiện recovery sau một batch lỗi, **CHỈ ĐƯỢC PHÉP** chạy đúng danh sách STT máy lỗi.
- **CẤM** gọi runner quét lại toàn bộ pending manifest (`tiktok_reg_clean_targets.json`), vì điều này sẽ lặp lại toàn bộ 70-80 máy, gây reg đi reg lại trong ngày.
- Hậu quả: TikTok phát hiện tần suất bất thường từ cùng thiết bị/IP và kích hoạt cấm form đăng ký:
  *"Bạn truy cập dịch vụ của chúng tôi quá thường xuyên."*

## 3. Xử lý khi gặp Rate-Limit "Truy cập quá thường xuyên"
- **Nhận diện:** Màn hình đỏ cảnh báo `Bạn truy cập dịch vụ của chúng tôi quá thường xuyên.` (hoặc keyword `too frequently`, `quá thường xuyên` trong UI XML).
- **Hành động ngay lập tức:**
  1. Ghi nhận máy vào `D:\Taadaa\runtime\kibe\device_cooldowns.json` với `ttl_hours: 48` (khóa 48 giờ).
  2. `am force-stop com.ss.android.ugc.trill` và đưa máy về Home (`input keyevent 3`).
  3. **TUYỆT ĐỐI CẤM retry nóng** trên các máy này.
