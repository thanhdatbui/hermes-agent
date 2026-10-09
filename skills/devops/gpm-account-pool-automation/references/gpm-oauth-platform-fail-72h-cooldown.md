# GPM OAuth Platform Failure Handling & 72h Cooldown Protocol

## 1. Bản chất sự cố & Phân loại lỗi
Trong luồng nạp tự động GPM OAuth lên OmniRoute (`:20129`), lỗi được phân loại nghiêm ngặt:
- **Lỗi SCRIPT / DỮ LIỆU NỘI BỘ (Script Error):**
  - Thiếu mật khẩu trong Excel quản lý (`master_gmail_manager.xlsx`, `gmail_clean_v2.xlsx`).
  - GPM API start timeout / crash hoặc CDP disconnect.
  - Bỏ qua an toàn do mail khôi phục dính `khoaleemagic`.
  - **Xử lý:** KHÔNG tính quota IP (IP được thử tài khoản khác). Đánh dấu email vào `failed_script_emails` để tránh lặp vô tận trong ngày.
- **Lỗi NỀN TẢNG (Platform Error):**
  - Google Checkpoint bắt số điện thoại xác minh (`challenge/iap`).
  - Google reCAPTCHA Challenge không tự vượt qua được.
  - Google từ chối cấp quyền / tạm khóa tài khoản (`signin/rejected`).
  - **Xử lý BẮT BUỘC theo chỉ đạo:**
    1. **Cooldown 72h cho Account:** Ghi nhận vào `oauth_pipeline_status.json` mục `cooldown_72h` với `retry_after = now + 72h`. CẢ `cron_gpm_oauth_full_pool.py` VÀ `add_oauth_omniroute.py` đều phải kiểm tra và bỏ qua tuyệt đối cho đến khi hết 72h để nhả checkpoint.
    2. **Khóa IP Proxy trong ngày:** Khóa cổng proxy/IP đó đến 00:00 (tính 1 lượt như SUCCESS) để chống lây cờ sang các tài khoản khác cùng dải IP.

## 2. Truy xuất thông tin xác thực (Credential Lookup)
- Khi nick cũ bị trôi khỏi `gmail_clean_v2.xlsx` do farm reg đè dữ liệu máy mới, mật khẩu và 2FA TOTP secret gốc phải được đối soát nạp bổ sung vào `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx` sheet `Master_All`.
- `CredentialLookup.load_all()` đọc ưu tiên `master_gmail_manager.xlsx` trước rồi đến `gmail_clean_v2.xlsx`.
- Trường hợp tài khoản bị yêu cầu 2FA TOTP: sử dụng `pyotp.TOTP(clean_secret).now()` tự động sinh mã xác thực 6 số.

## 3. Kiến trúc State & Báo cáo 6h
- File tracker dài hạn: `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json` (`cooldown_72h`, `cooldown_7days`, `omniroute_success`).
- File state hàng ngày: `D:/Taadaa/runtime/kibe/cron-state/gpm_oauth_daily_state.json` (`used_proxies`, `events`, `failed_script_emails`).
- Báo cáo 6h (`cron_gpm_oauth_pool_6h_report.py`) deduplicate theo email và phân tách 3 cột:
  - ✓ Thành công
  - 🛑 Lỗi nền tảng (Cooldown 72h & Khóa IP)
  - ⚠️ Lỗi script / nội bộ (IP được giữ)
