# TikTok Multi-Account Fast Login & TOTP Re-sync Recovery (2026-09-02)

## 1. Fast-Login Selection Surface ("Chào mừng bạn trở lại")
Khi thiết bị bị đăng xuất hàng loạt hoặc mất session, khi mở TikTok vào tab Hồ sơ sẽ xuất hiện màn hình `SignUpOrLoginActivity` ("Chào mừng bạn trở lại") liệt kê các nick từng đăng nhập trên máy:
- **Tọa độ tài khoản trong danh sách trượt:**
  - Row 1: `(540, 765)`
  - Row 2: `(540, 996)`
  - Row 3: `(540, 1180)`
- **Luồng 1-Tap Fast-Path:**
  - Tap trực tiếp vào nick trong danh sách -> TikTok sẽ tự động bỏ qua bước nhập identifier và chuyển thẳng vào màn hình nhập 2FA TOTP hoặc đăng nhập thẳng.
  - Sau khi vào màn 2FA: sinh mã TOTP từ cột `2FA` trong `taikhoan_dat_v2_updated .xlsx`, nhập 6 số và tap "Tiếp tục" `(540, 1806)`.

## 2. Xử lý Lỗi "Nhập mã hợp lệ" khi Submit TOTP
- **Hiện tượng:** Màn hình 2FA báo lỗi đỏ `Nhập mã hợp lệ` (`id/i7f` bounds `[144,840][978,888]`) sau khi submit mã TOTP.
- **Nguyên nhân:** Mã TOTP bị hết hạn theo chu kỳ 30s hoặc ô input còn dính ký tự rác/mã cũ.
- **Quy trình xử lý:**
  1. Gửi chuỗi `input keyevent 67` (DEL) từ 6-8 lần để xóa sạch ký tự cũ trong ô OTP.
  2. Tap lại vào ô nhập `(540, 730)`.
  3. Sinh mã `pyotp.TOTP(secret).now()` tươi mới tại thời điểm hiện tại.
  4. Broadcast `ADB_KEYBOARD_INPUT_TEXT` với chuỗi mã base64.
  5. Tap "Tiếp tục" `(540, 1806)` để hoàn tất xác thực 2FA.

## 3. Luồng Chuyển đổi & Đăng nhập tiếp các nick còn lại (Bottom Sheet Switcher)
Sau khi login thành công nick đầu tiên:
1. Vào tab Hồ sơ `(972, 1857)`.
2. Tap vào display name ở header `(250, 322)` (`id/sv6`) để mở bảng trượt `Chuyển đổi tài khoản` (`id/fxs`).
3. Tap "Thêm tài khoản" `(540, 1788)`.
4. Nếu xuất hiện màn hình gợi ý nick cũ:
   - Tap "Thêm tài khoản khác" `(540, 1507)`.
   - Tap "Bạn đã có tài khoản? Đăng nhập" `(540, 1830)`.
   - Tap "Sử dụng số điện thoại/email/tên người dùng" `(540, 788)`.
   - Chuyển sang tab "Email/tên người dùng" `(713, 288)`.
5. Điền identifier (`anhtruong840`, `laquyen2601`, `khoa50076`, `tranvantrang9810`...) -> nhập mật khẩu/2FA.
6. Lặp lại quy trình cho đến khi đủ số lượng tài khoản trên máy.

## 4. Phục hồi kết nối ADB & VPN khi thiết bị reconnect
- Khi thiết bị rớt kết nối ADB tạm thời (`device not found` -> `device`):
  1. Đảm bảo màn hình mở khóa: `input keyevent 82; input keyevent 3`.
  2. Khởi động lại atx-agent server: `nohup /data/local/tmp/atx-agent server >/dev/null 2>&1 &`.
  3. Chạy `gan_proxy_fleet.py run --machines <M> --mapping <file> --full-scope-takeover` để kích hoạt lại tunnel ViChanger VPN (`tun0`).
