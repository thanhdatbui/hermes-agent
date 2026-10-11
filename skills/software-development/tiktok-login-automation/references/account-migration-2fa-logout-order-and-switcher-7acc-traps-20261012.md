# Kỷ luật Di dời Nick Non & Thao tác Switcher 7-8 Nick (Session 2026-10-12)

## 1. Kỷ luật Bắt buộc khi Di dời Tài khoản (Add 2FA -> Logout -> Login)
- **Nguyên tắc bất di bất dịch:** Khi điều chuyển nick (đặc biệt là nick non) từ máy đầy (8 nick) sang máy trống/máy khác:
  1. **BƯỚC 1 - Add 2FA & Lưu Master DAT:** BẮT BUỘC bật 2FA TOTP Authenticator và khởi tạo mật khẩu chuẩn farm trên thiết bị đang có session active TRƯỚC TIÊN. Ghi ngay TOTP Secret và mật khẩu vào Master DAT / Workbook của máy đích.
  2. **BƯỚC 2 - Logout khỏi máy cũ:** Sau khi 2FA đã được lưu an toàn vào hệ thống, mới thực hiện đăng xuất dứt điểm nick đó khỏi máy cũ để giải phóng slot (hạ danh sách Switcher xuống 7 nick).
  3. **BƯỚC 3 - Login nick đích:** Đăng nhập nick mới vào máy cũ.
  4. **CẤM:** Tuyệt đối KHÔNG đăng nhập nick non lên máy mới khi chưa có chỉ đạo của User. Chỉ ghi nhận định danh vào sổ sách/database.

## 2. Bẫy Active Profile vs Switcher khi Logout
- **Hiện tượng:** Trong TikTok (v46-v47), khi mở bottom sheet Switcher ("Chuyển đổi tài khoản"), danh sách chỉ liệt kê các tài khoản phụ (tối đa 7 nick). Tài khoản đang active hiển thị ở header Profile và **KHÔNG nằm trong danh sách Switcher**.
- **Hậu quả:** Script tìm nick cần logout trong Switcher không thấy -> tưởng nick không có trên máy hoặc báo fail im lặng.
- **Xử lý chuẩn:**
  - Kiểm tra active profile trên màn hình Hồ sơ trước. Nếu nick cần logout chính là active profile -> ĐÓNG Switcher (`tap 540, 200` hoặc keyevent BACK), đi thẳng vào `Menu 3 gạch > Cài đặt và quyền riêng tư > Cuộn xuống đáy > Đăng xuất`.
  - Nếu không phải active profile mới tìm trong Switcher để switch sang rồi mới logout.

## 3. Bẫy SparkActivity / "Thời gian sử dụng màn hình" trong Cài đặt
- **Hiện tượng:** Trong trang Cài đặt, cuộn tìm nút "Đăng xuất" hoặc "Chuyển đổi tài khoản" nếu vuốt chạm vào giữa màn hình có thể kích hoạt webview hybrid `SparkActivity` ("Thời gian sử dụng màn hình").
- Khi rơi vào `SparkActivity`:
  - `atx-agent` / `uiautomator` dump UI bị rỗng hoặc chỉ còn status bar Android.
  - `open_app()` kiểm tra foreground thấy package TikTok nên tưởng app đã sẵn sàng và không khởi động lại.
- **Xử lý chuẩn:**
  - Trong `go_to_profile()`, kiểm tra nếu `mCurrentFocus` chứa `SparkActivity` hoặc `SettingContainerActivity` -> bấm `BACK` (keyevent 4) 2 lần để thoát về màn hình chính.
  - Trước khi chạy flow login mới, nên `am force-stop com.ss.android.ugc.trill` để đảm bảo sạch trạng thái.

## 4. Tọa độ Nút "Thêm tài khoản" khi Switcher có 7 Nick
- **Hiện tượng:** Khi máy có 7 nick, nút "Thêm tài khoản" nằm kịch sàn ở đáy màn hình tại tọa độ `(540, 1850)` (bounds `[0,1788][1080,1920]`, `h=132`).
- Text của button có thể bị cắt lẹm trong XML dump khiến `find_node_in_xml` không bắt được text chuẩn.
- **Xử lý chuẩn:**
  - Thêm fallback tap trực tiếp vào tọa độ `(540, 1850)` trong `tap_add_account` và kiểm tra sự xuất hiện của login modal trước khi rơi vào vòng lặp swipe/timeout.
