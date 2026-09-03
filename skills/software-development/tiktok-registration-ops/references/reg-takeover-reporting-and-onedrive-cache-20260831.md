# TikTok Reg: Takeover, Gmail Popups, Reporting & OneDrive Cache (2026-08-31)

## 1. Format báo cáo kết quả
Báo cáo batch / reg / cron theo định dạng rút gọn:
```
Success:
- Machine <STT>: <tiktok_id> (<email>, row <N>)

Fail:
- Machine <STT>: <MÃ_LỖI>
```

## 2. Quy tắc Takeover 1 Máy khi Farm đang chạy Multi-Machine Feed Session
- Khi user yêu cầu takeover 1 máy để reg khi phiên nuôi acc đang chạy trên dàn:
  * **TUYỆT ĐỐI CẤM kill PID parent của feed runner** (tránh làm sập toàn bộ các máy khác).
  * Kiểm tra trạng thái máy đích: nếu máy đã chạy xong hoặc ở trạng thái giữ hiện trường `blocked`/`handoff` (`owner_active: false`), dùng script chính thức:
    `python python_runner/scripts/release-device-lock.py --machine <STT> --serial <SERIAL> --reason "takeover-for-tiktok-reg"`
  * Sau khi nhả lock an toàn của đúng máy đó, chạy runner reg cho riêng máy đó với `DEVICE_LOCK_ENABLED=1`.

## 3. Xử lý Popup Gmail & Fallback Check-Live
- Trong `social_reg_v1.py::_dismiss_gmail_popups`:
  * Alert dialog `Bật tính năng tự động đồng bộ hóa?` -> tap `Bật` (`android:id/button1`).
  * Auto-sync off banner -> tap `com.google.android.gm:id/dismiss_icon` hoặc `Bật` / `Bỏ qua`.
  * Phishing protection popup (`Tăng cường khả năng bảo vệ trước hành vi lừa đảo`) -> tap `Không, cảm ơn`.
  * Welcome tour -> tap `OK`.
  * Sender image tooltip -> tap `Bỏ qua`.
  * Meet onboarding banner -> tap `Đã hiểu`.
  * Setup addresses -> tap `ĐƯA TÔI TỚI GMAIL`.
  * Khi timeout không thấy OTP -> tự động gọi `check_google_account_health_from_gmail` để phân loại Google Account LIVE hay dính CAPTCHA/relogin.

## 4. Xử lý xung đột OneDrive Excel "UPLOAD BLOCKED / Discard Changes"
- Khi mở file Excel trong OneDrive (`gmail_clean_v2.xlsx`, `taikhoan_run_safe.xlsx`) bị thanh vàng/đỏ "UPLOAD BLOCKED / Discard Changes":
  * Do Office Document Cache trên máy giữ phiên bản cũ trong khi script Python ghi trực tiếp lên đĩa.
  * Hướng dẫn user bấm **`Discard Changes` -> `Yes`** để Excel xóa cache và tải lại dữ liệu mới nhất từ ổ đĩa mà không mất dữ liệu.

## 5. Quy tắc Tài khoản Die & Tracking Sheet
- Khi một tài khoản TikTok bị die/ban:
  * CHỈ xóa `ID / PASS / 2FA` của TikTok trong `taikhoan_dat_v2_updated .xlsx` và trên TikTok app.
  * BẮT BUỘC giữ nguyên cột `GMAIL` và `PASS MAIL` (và giữ Google account trên máy).
  * Code đọc nguồn reg (`load_registered_mailboxes`, `load_registered_tiktok_emails`) coi mọi email đã xuất hiện ở cột `GMAIL` trong tracking là ĐÃ SỬ DỤNG, không bao giờ cấp lại để reg mới.
