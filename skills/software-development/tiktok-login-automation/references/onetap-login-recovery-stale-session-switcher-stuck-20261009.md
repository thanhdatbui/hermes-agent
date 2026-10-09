# Hiện Tượng Văng Phiên Khiến Account Switcher Liệt & One-Tap Login Recovery (2026-10-09)

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ
- **Hiện tượng**: Trên máy Android farm (đặc biệt dòng Samsung Galaxy S7 / TikTok v46.6.3), khi bấm vào display name / avatar trên header trang Profile hoặc cuộn xuống tap thanh sticky bar (`pmf` / `pmi`), giao diện **Account Switcher hoàn toàn không bung ra**, dẫn đến lỗi timeout `[03_dropdown] Khong mo duoc account dropdown`.
- **Bản chất**:
  1. Khi một hoặc nhiều tài khoản trên máy bị **văng phiên (session expired / token stale)**, TikTok không xóa tài khoản mà chuyển các tài khoản này vào danh sách đệm **One-tap Login** (*"Chào mừng bạn trở lại"* / *"Welcome back"*).
  2. Tại trang Profile, app TikTok chỉ đang render view tĩnh rỗng của tài khoản cũ chưa kích hoạt lại session. Do không có context session sống, app không load được danh sách tài khoản liên kết, biến text header thành nhãn tĩnh không clickable hoặc click vào bị no-op.

## 2. Quy Trình Khôi Phục & Kích Hoạt Lại Session (One-Tap Recovery Flow)
Khi Account Switcher không bung do văng phiên, không cố click mò header mà thực hiện quy trình phục hồi One-tap:
1. **Truy cập màn hình One-tap Login**:
   - Nếu đang ở Profile rỗng/văng: Vào *Menu hồ sơ (954, 96)* -> *Cài đặt và quyền riêng tư (540, 1278)* -> Cuộn xuống đáy chọn *Đăng xuất* -> Xác nhận Đăng xuất.
   - Thao tác này đưa app về màn hình Profile đăng xuất an toàn mà không làm mất cookie/credentials đã lưu.
   - Bấm vào tab *Hồ sơ* -> Bấm nút đỏ *Đăng nhập* (`540, 1094`) để mở bottom sheet *"Chào mừng bạn trở lại"*.
2. **Kích hoạt phiên One-tap (Zero OTP / Zero Password)**:
   - Toàn bộ các nick đã lưu (ví dụ `@letam2502`, `@bongbong02892`) hiển thị rõ danh sách trong sheet *"Chào mừng bạn trở lại"*.
   - Tap trực tiếp vào hàng tài khoản tương ứng: TikTok tự động nạp lại session token đã lưu mà không đòi hỏi nhập mật khẩu hay gửi OTP mail.
   - Chuyển vào Profile cá nhân của nick đó trong <= 2 giây.
3. **Mở đường cho Reg thêm nick mới**:
   - Màn hình *"Chào mừng bạn trở lại"* có sẵn nút **"Thêm tài khoản khác"** (`Thêm tài khoản khác` / `Add another account`) và **"Bạn không có tài khoản? Đăng ký"**.
   - Bấm trực tiếp vào các nút này để tiếp tục luồng tạo/đăng ký tài khoản cho các slot tiếp theo mà không bị kẹt ở dropdown Profile.

## 3. Cập Nhật Bổ Trợ Script `tiktok_login_v1.py` Cho Cụm Admin
- Khi chạy script `tiktok_login_v1.py` trên cụm Admin (Máy 201–280):
  - Bắt buộc kiểm tra `resolve_device(stt)`: Danh sách cứng `ACCOUNTS` chỉ chứa Máy 1–80 (Kibe). Cần fallback sang `load_machine_devices(TARGET_INVENTORY_WORKBOOK)` (`taikhoan_run_safe.xlsx`) để lấy đúng device serial cho Máy 201–280.
  - Bắt buộc truyền socket ADB phù hợp (`ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"`) để tránh rơi về localhost:5037 gây lỗi `device not found / VPN GATE BLOCKED`.
