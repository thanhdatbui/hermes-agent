# Quy Trình Đổi Email Liên Kết Trực Tiếp Trên TikTok Native App (Samsung S7)

## 1. Ngữ Cảnh Kỹ Thuật & Khác Biệt Giữa Lý Thuyết vs Thực Tế
- **Lý thuyết sai lầm thường gặp**: Tưởng rằng TikTok bắt buộc phải gửi mã OTP về email cũ trước khi cho đổi sang email mới, dẫn đến tâm lý "Gmail cũ die rồi thì không thể đổi sang mail mới trong app".
- **Thực tế trên giao diện TikTok native app**:
  - Khi nick đã đăng nhập native trên thiết bị đáng tin cậy (trusted device / Samsung S7 farm), vào `Thông tin tài khoản` -> chọn `Email`.
  - Popup hiện ra gồm 2 lựa chọn: **Thay đổi email** và **Hủy liên kết email**.
  - Bấm **Thay đổi email** -> TikTok chuyển thẳng vào form **Nhập email mới**, **HOÀN TOÀN KHÔNG BẮT NHẬP OTP MAIL CŨ** nếu phiên máy thật có độ trust cao.

## 2. Các Bước Thực Thi Chuẩn Qua ATX-Agent (Port 7912)

### B1: Định vị và switch đúng nick đích
1. Mở app TikTok (`com.ss.android.ugc.trill`).
2. Bấm vào tab **Hồ sơ** (`Profile` ở góc dưới cùng bên phải: tọa độ `[864,1794][1080,1920]`, tâm `(972, 1857)`).
3. Kiểm tra xem header có đúng `@username` cần đổi không.
4. Nếu đang ở nick khác: Bấm vào tên header (hoặc biểu tượng switcher) để bung bảng **Chuyển đổi tài khoản**, chọn đúng nick đích.

### B2: Điều hướng vào Thông tin tài khoản
1. Bấm **Menu hồ sơ** (icon 3 gạch góc trên phải: `bounds=[954,96][1056,204]`, tâm `(1005, 150)`).
2. Bấm **Cài đặt và quyền riêng tư** (tâm `(621, 1248)`).
3. Bấm mục **Tài khoản** (hàng `[24,1722][1056,1899]`, tâm `(540, 1810)`).
4. Bấm **Thông tin tài khoản** (hàng `[24,246][1056,402]`, tâm `(540, 324)`).

### B3: Mở modal đổi email
1. Bấm vào dòng **Email** (tâm `(136, 480)`).
2. Khi modal bật lên (gồm `Thay đổi email` và `Hủy liên kết email`), bấm **Thay đổi email** (tâm `(540, 1362)`).
3. **Lưu ý hộp thoại xác nhận 2FA (nếu có)**: Trên một số tài khoản đã bật 2FA hoặc phiên bảo mật cao (như Máy 02 và Máy 42), TikTok hiện thêm popup cảnh báo: *"Thay đổi email? Email mới của bạn cũng sẽ được sử dụng cho xác minh 2 bước"*. Tại đây bắt buộc bấm nút **Tiếp tục** ở bên phải (bounds `[541,1212][960,1355]`, tâm `(750, 1283)`) thì mới chuyển sang form nhập email mới.

### B4: Điền Hotmail mới & Bấm Tiếp tục
1. Form **Thay đổi email** hiện ô nhập `Nhập email` (bounds `[162,570][918,630]`).
2. Nhập username của Hotmail mới qua `pressKeyCode` của ATX-agent (tránh dùng `input_text` đụng phải Samsung Keypad Settings gây mất focus).
3. Bấm vào nút gợi ý `@hotmail.com` (bounds `[809,927][1080,1011]`, tâm `(944, 969)`) để điền hoàn chỉnh email.
4. Bấm nút **Tiếp tục** (tâm `(540, 813)`).

### B5: Bóc OTP qua Microsoft Graph API & Xác nhận hoàn tất
1. TikTok chuyển sang màn hình **Xác minh email** (đếm ngược 60s) gửi mã về Hotmail mới.
2. Gọi Graph API bóc mã OTP 6 số từ `register@account.tiktok.com` (qua endpoint `https://graph.microsoft.com/v1.0/me/messages?$top=5`).
3. Dùng `pressKeyCode` nhập lần lượt 6 chữ số OTP vào giao diện.
4. Màn hình tự động quay lại **Thông tin tài khoản**, mục Email đổi sang `c***<số>@hotmail.com`.

## 3. Đồng Bộ Đa Tầng & Dọn Dẹp Sau Khi Đổi Thành Công
- **SQLite Master Ledger (`farm_master.db`)**: Cập nhật cột `email` trong bảng `tiktok_accounts` cho `@username` qua DAL `farm_db.update_tiktok_credentials(username, email=new_email)`.
- **Master Excel (`taikhoan_dat_v2_updated .xlsx`)**: Cập nhật Cột F (`GMAIL`) và Cột G (`PASS MAIL`) tương ứng với dòng của máy/nick đó.
- **Cơ chế dọn dẹp Gmail DIE trên Android OS (`dumpsys account` / Settings)**:
  - Khi nick TikTok còn liên kết với Gmail DIE cũ, hệ thống cấm gỡ Gmail khỏi máy để tránh mất dấu.
  - Ngay sau khi hoàn tất đổi sang Hotmail mới trên app TikTok, tài khoản TikTok đã được bảo vệ độc lập -> Thực hiện gỡ bỏ hoàn toàn Gmail DIE cũ khỏi Android OS Settings (`preflight_s7_rolling_cleanup.py` / `remove_account_adb`) để giải phóng slot máy và làm sạch danh bạ tài khoản.
- **Dọn dẹp thiết bị**: Gửi lệnh bấm `home` và `power` đưa máy về trạng thái ngủ an toàn.
