# Quy trình Logout Nick Ký Sinh / Nick Rác trên TikTok bằng OCR + Coordinates

## Mục đích
Khi một thiết bị trên Farm dính nick lạ / nick ký sinh (parasite account) không nằm trong inventory hoặc kẹt giới hạn slot tài khoản, cần thực hiện logout nick này bằng phương pháp OCR + Coordinates kết hợp screencap nghiệm thu không làm ảnh hưởng tới các tài khoản chính.

## Quy trình chuẩn từng bước (1080x1920)

1. **Mở ứng dụng TikTok**:
   ```bash
   adb -s <SERIAL> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
   ```
   Chờ 5s cho app khởi động hoàn tất.

2. **Vào trang Profile (Hồ sơ)**:
   - Tọa độ icon Hồ sơ ở thanh bottom navigation: `(972, 1857)`.
   - Sleep 3s.

3. **Mở Account Switcher (Trình chuyển tài khoản)**:
   - Tọa độ dropdown tên tài khoản ở header: `(539, 140)`.
   - Sleep 3s.

4. **Quét OCR tìm nick mục tiêu**:
   - Dùng WinRT OCR (`windows-native-ocr` skill) phân tích screencap switcher.
   - Tìm tọa độ bounding box của nick mục tiêu (`verdhsclf6f`, v.v.).
   - Nếu tìm thấy: tap vào tọa độ `(cx, cy)` của dòng nick.
   - Nếu OCR không ra do font mờ, fallback vị trí danh sách (hàng thứ 7 thường ở `y ≈ 1380` - `1450`).
   - Sleep 5s để app switch sang tài khoản đích.

5. **Mở Menu Cài đặt & Quyền riêng tư**:
   - Tap Hồ sơ: `(972, 1857)` (sleep 2s).
   - Tap Menu 3 gạch góc trên bên phải: `(1005, 150)` (sleep 2s).
   - Tap mục 'Cài đặt và quyền riêng tư' (Settings & Privacy): `(540, 1248)` (sleep 3s).

6. **Cuộn xuống đáy trang Cài đặt**:
   - Thực hiện vuốt 5 lần để đảm bảo chạm đáy:
     ```bash
     adb -s <SERIAL> shell input swipe 540 1600 540 300 250
     ```
     Mỗi lần sleep 1s.

7. **Bấm nút Đăng xuất (Log out)**:
   - Tọa độ nút Đăng xuất ở chân trang: `(540, 1750)` hoặc `(540, 1668)`.
   - Sleep 2s.

8. **Xác nhận Đăng xuất trên Dialog**:
   - Chụp ảnh dialog xác nhận để nhận diện nút màu đỏ.
   - Tọa độ nút Đăng xuất xác nhận: `(540, 1662)` (hoặc `(750, 1100)` tùy modal dạng popup hay bottom sheet).
   - Sleep 5s.

9. **Nghiệm thu (Verification Gate)**:
   - Mở lại TikTok -> vào Profile (`972, 1857`) -> mở Switcher (`539, 140`).
   - Screencap lưu vào `D:/Taadaa/reports/<device>_verified_logout.png`.
   - OCR đọc lại switcher: BẮT BUỘC KHÔNG còn nick ký sinh.
   - Dọn dẹp: Force-stop TikTok và về Home (`am force-stop com.ss.android.ugc.trill && input keyevent 3`).
