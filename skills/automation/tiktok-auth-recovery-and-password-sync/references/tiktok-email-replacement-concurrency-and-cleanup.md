# TikTok Email Replacement at Scale (Farm S7) & Concurrency Guard

## 1. Bản Chất Kỹ Thuật Đổi Email Trên App TikTok S7
- **Không đòi OTP Gmail cũ bị DIE:** Khi vào `Settings & Privacy > Account > Account Information > Email > Change Email`, app TikTok trên phiên bản Android S7 KHÔNG yêu cầu xác thực OTP từ Gmail cũ nếu session tài khoản đang sống trên app.
- Form sẽ mở thẳng ra ô `Nhập email` mới.
- Sau khi điền Hotmail mới có Microsoft Graph API, TikTok gửi mã OTP 6 số về Hotmail.
- Hệ thống bốc mã OTP qua Graph API (`login.live.com/oauth20_token.srf` + `graph.microsoft.com/v1.0/me/messages?$top=5`) và điền vào app TikTok trong vòng 2-3 giây.

## 2. Pitfalls Khi Đẩy Workers Song Song (Batch Concurrency Pitfall)
- **Bẫy Ảo Giác "Captcha" Từ Màn Hình Camera/LIVE Overlay:**
  - Khi TikTok mở app hoặc kết thúc ca trước, app thường dừng ở màn hình **Tạo video / Camera & LIVE** với các text `CAMERA`, `LIVE`, `ẢNH`, `15s`, `60s`.
  - **CẢNH BÁO:** Không được nhầm các nhãn này thành Captcha hay Security Challenge! Bấm nút `X` đóng Camera ở góc trên bên trái `[36,108][168,240]` (click `(102, 174)`) để đưa giao diện trở lại tab Hồ sơ.
- **Cấm đẩy quá cao (> 5 workers đồng thời):** Khi đẩy worker lên 15 luồng đồng loạt gửi request đổi email:
  1. TikTok backend kích hoạt ngay **Captcha trượt hình ảnh (Slide to complete the puzzle)** làm che khuất nút Tiếp tục $\rightarrow$ TikTok không gửi OTP $\rightarrow$ Timeout fail hàng loạt.
  2. Mạng Wi-Fi và ADB daemon quá tải làm app TikTok load chậm $\rightarrow$ tap Profile trượt vào màn Splash/Home (`Current profile: @None`).
- **Khuyến nghị an toàn:** Chỉ chạy song song từ 3 đến 5 workers kèm stagger 5-10s giữa các máy.
- **Xử lý Captcha đóng (`verify-bar-close`):** Khi gặp màn hình Captcha trượt thật sự, kiểm tra các node con có resource-id chứa `verify-bar-close` hoặc text/desc `Đóng` để dismiss popup thay vì đứng chờ timeout.

## 3. Quy Tắc Điều Khiển atx-agent & uiautomator Stub Trên S7
- **Deterministic Port Forward:** Dùng `zlib.crc32(serial.encode('utf-8')) % 800 + 17900` để map local port riêng cho từng máy, cấm dùng `hash(serial)` tránh collision.
- **Fix lỗi HTTP 502 Bad Gateway:** Trước khi tương tác, dọn sạch zombie và kích hoạt stub bằng pattern chuẩn:
  ```bash
  am force-stop com.github.uiautomator 2>/dev/null; killall atx-agent 2>/dev/null; /data/local/tmp/atx-agent server -d --addr 127.0.0.1:7912; monkey -p com.github.uiautomator 1 >/dev/null 2>&1 &
  ```

## 4. Dọn Dẹp Gmail DIE Ba Tầng (Three-Tier Cleanup)
1. **Tầng 1 (Android S7):** Mở khóa `tiktok_bound_emails` sau khi đổi Hotmail thành công $\rightarrow$ gọi `remove_account_adb()` gỡ sạch Gmail DIE khỏi Cài đặt tài khoản thiết bị.
2. **Tầng 2 (SQLite SSOT):** Cập nhật `email = <hotmail_mới>` vào bảng `tiktok_accounts` qua `farm_db.update_tiktok_credentials(username, email=...)`.
3. **Tầng 3 (Master Excel Mirror):** Cập nhật cột GMAIL và PASS MAIL trên `taikhoan_dat_v2_updated .xlsx` để dữ liệu backup đồng nhất 100%.
