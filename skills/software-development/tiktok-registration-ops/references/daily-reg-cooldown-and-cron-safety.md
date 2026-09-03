# Registration Cooldown, Device Locks & Farm Cron Safety (2026-08-26)

## 1. Cơ Chế Cooldown 1 Ngày / 1 Máy (Daily Reg Limit)
- **Quy tắc:** Mỗi máy trong farm tối đa chỉ reg thành công 1 lần/ngày.
- **Cơ chế ghi:** Khi flow đăng ký đạt `SUCCESS` / `VERIFIED_SUCCESS`:
  - Ghi nhận máy vào `C:\Users\Kibe\.codex\device-locks\reg_daily_cooldowns.json` với `cooldown_until: <ngày hôm sau>`.
  - `_detect_clean.py` / `filter_unlocked_targets` tự động kiểm tra `is_machine_reg_cooldown_active()` và từ chối chọn máy với lý do `REG_DAILY_COOLDOWN_ACTIVE` (status `temporarily_skipped`).
- **Ngoại lệ:** Máy bị lỗi (`PENDING`, `FINAL_BLOCKED`, UI XML timeout) KHÔNG được ghi daily cooldown, để cho phép recovery sửa lỗi.

## 2. Rate-Limit Cooldown 48 Giờ
- **Dấu hiệu:** Màn hình đỏ / popup "Bạn truy cập dịch vụ của chúng tôi quá thường xuyên" hoặc "too frequently".
- **Xử lý:**
  - Ghi vào `D:\Taadaa\runtime\kibe\device_cooldowns.json` với `ttl_hours: 48`.
  - Tuyệt đối không retry nóng vào máy bị rate-limit.

## 3. Cấm Tuyệt Đối Pause Cron Khi Chạy Tay / Recovery
- **Nguyên lý:** Mọi cron nuôi acc (`tiktok_runner.py`), feed (`tiktok_watcher.py`), reg đêm (`night_chain_reg`) đều tự tích hợp kiểm tra `device_lock`. Khi cron chạy, nếu thấy máy đang có lock hợp lệ thì tự động skip máy đó và tiếp tục chạy các máy rảnh còn lại.
- **Hậu quả nếu pause cron:**
  - Làm tê liệt `reap-dead-owner-locks` (script giải phóng lock chết sau TTL 2h).
  - Khi máy kẹt quá 2h không có cron dọn dẹp, app TikTok không được `am force-stop` và màn hình bị treo mãi mãi.
  - Làm tê liệt `device-locks-watchdog` (báo cáo Telegram khi có máy giữ lock quá hạn).
- **Quy tắc:** Không bao giờ dùng `cronjob(action='pause')` khi thực hiện thao tác thủ công.

## 4. Recovery Đúng Phạm Vi Danh Sách Lỗi
- **Bài học xương máu:** Khi recovery một nhóm máy lỗi (ví dụ 10 máy), bắt buộc phải tạo manifest recovery riêng biệt chỉ chứa đúng STT máy lỗi.
- **Cấm:** Không gọi `_run_all_targets.py` trực tiếp khi chưa gán manifest hẹp, vì runner sẽ tự động kích hoạt `_detect_clean.py` và quét toàn bộ danh sách pending 70+ máy, làm bùng phát thành đợt reg hàng loạt và gây dính rate-limit cả farm.

## 5. Package Name TikTok Farm
- Luôn đảm bảo script dọn dẹp / force-stop hỗ trợ đúng package: `com.ss.android.ugc.trill` (bản TikTok global đang chạy trên farm) song song với `com.zhiliaoapp.musically`.
