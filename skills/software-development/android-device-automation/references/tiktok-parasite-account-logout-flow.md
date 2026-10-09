# TikTok Parasite Account Logout & Verification Flow

## Context & Objectives
Khi một thiết bị Android (Samsung S7 / tương đương) trong phone farm bị dính nick ký sinh (parasite account) không thuộc manifest hoặc cần giải phóng slot tài khoản TikTok, quy trình đăng xuất dứt điểm đòi hỏi phải tương tác UI chính xác vì TikTok không hỗ trợ intent logout qua ADB shell mà phải đi qua UI Settings & Privacy.

## Chuẩn quy trình thực thi (Tested & Verified trên M40/M42/M76/M32)

### 1. Kỷ luật an toàn thực thi
- Mọi lệnh ADB gọi từ Python qua `subprocess.run` **BẮT BUỘC** có `timeout=15` để chống treo khi USB renegotiate hoặc ADB daemon lag.
- Xử lý tuần tự từng thiết bị, không chạy song song làm nghẽn I/O USB hoặc ADB bus.

### 2. Trình tự thao tác (UI Sequences & Key Coordinates)
1. **Wake & Unlock màn hình:**
   ```bash
   adb -s <SERIAL> shell input keyevent 224 && adb -s <SERIAL> shell input keyevent 82
   ```
2. **Khởi chạy TikTok qua Launcher Intent:**
   ```bash
   adb -s <SERIAL> shell am force-stop com.ss.android.ugc.trill
   adb -s <SERIAL> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
   # sleep 5s để app render xong feed
   ```
3. **Chuyển sang tab Profile:**
   - Tap nút Profile góc dưới cùng bên phải: `input tap 972 1857` (sleep 3s).
4. **Mở Account Switcher (Bottom sheet chuyển đổi tài khoản):**
   - Vuốt nhẹ xuống trước để reset vị trí header: `input swipe 540 1200 540 800 250` (sleep 1s).
   - Tap dropdown Switcher ở giữa header: `input tap 540 140` (sleep 3s).
5. **Định vị & Switch sang nick ký sinh:**
   - Screencap và dùng WinRT OCR trích xuất BoundingRect Y của nick ký sinh.
   - Nick ký sinh (dòng thứ 6–8) thường nằm ở tọa độ Y từ `1450` đến `1550`.
   - Tap vào dòng chứa nick mục tiêu: `input tap 400 <target_y>` (sleep 6s để TikTok reload state).
6. **Vào Cài đặt và quyền riêng tư (Settings and Privacy):**
   - Đảm bảo đang ở tab Profile: `input tap 972 1857` (sleep 3s).
   - Mở Drawer menu 3 gạch ở góc trên cùng bên phải: `input tap 1005 150` (sleep 3s).
   - Tap mục "Cài đặt và quyền riêng tư" ở đáy Drawer: `input tap 540 1250` (sleep 4s).
7. **Cuộn xuống đáy trang Cài đặt:**
   - Lặp 6 lần vuốt nhanh từ dưới lên trên:
     `input swipe 540 1600 540 300 250` (mỗi lần sleep 1s).
8. **Thực hiện Đăng xuất:**
   - Nút "Đăng xuất" ở đáy màn hình: `input tap 300 1640` (sleep 3s).
   - Popup xác nhận màu đỏ xuất hiện ("Bạn có chắc chắn muốn đăng xuất?"): tap nút đỏ xác nhận `input tap 540 1640` (sleep 6s để hoàn tất invalidate session).
9. **Nghiệm thu dứt điểm (Verification Gate):**
   - Vào lại Profile (`input tap 972 1857`) -> vuốt nhẹ -> mở Switcher (`input tap 540 140`).
   - Chụp screencap kéo về `D:/Taadaa/reports/<device>_verified_logout.png`.
   - Chạy OCR nghiệm thu:
     - **Điều kiện PASS:** Nick ký sinh ĐÃ HOÀN TOÀN BIẾN MẤT khỏi Switcher và xuất hiện nút "Thêm tài khoản" ("Add account").
   - Trả về đường dẫn `MEDIA:<path_to_png>` cho người dùng.
10. **Đưa thiết bị về trạng thái sạch:**
    ```bash
    adb -s <SERIAL> shell am force-stop com.ss.android.ugc.trill && adb -s <SERIAL> shell input keyevent 3
    ```

## Pitfalls & Lessons Learned
- **WinRT OCR Path Formats:** API `Windows.Storage.StorageFile::GetFileFromPathAsync` trong PowerShell yêu cầu tuyệt đối đường dẫn kiểu Windows native với backslash (`D:\Taadaa\...`). Nếu truyền forward slash (`D:/Taadaa/...`), WinRT sẽ quăng ngoại lệ `AggregateException` / NullReferenceException.
- **Tọa độ popup xác nhận:** Đừng tap nhầm nút "Chuyển đổi tài khoản" ở Y=1477. Nút Đăng xuất màu đỏ luôn nằm ở khoảng Y=1640, X=540.
