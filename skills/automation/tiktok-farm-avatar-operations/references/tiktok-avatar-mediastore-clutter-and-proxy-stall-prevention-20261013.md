# TikTok Avatar Upload: MediaStore Clutter, Proxy Socket Stall, and True Visual Gate (2026-10-13)

## Bối cảnh & Hiện tượng (Root Cause Analysis)
Khi chạy quy trình thay đổi avatar tự động trên thiết bị Android farm (TikTok v47+), có thể xảy ra tình trạng:
1. **Báo cáo láo / False positive upload**: Tool/script báo cáo đã thực hiện đầy đủ các bước (tap avatar/sửa hồ sơ -> chọn ảnh -> crop -> bấm Lưu), nhưng trên thực tế avatar của tài khoản **hoàn toàn chưa được cập nhật** trên server TikTok và màn hình profile vẫn giữ ảnh cũ hoặc bị đổi thành ảnh placeholder rác.
2. **MediaStore Polling Clutter**: Khi chụp ảnh màn hình bằng `screencap -p /sdcard/xxx.png` lưu trực tiếp trên bộ nhớ chung (`/sdcard/` hoặc `/storage/emulated/0/`), hệ thống MediaStore của Android tự động index các file PNG này vào bảng `images/media`. Do đó, khi TikTok mở Photo Picker, danh sách ảnh bị tràn ngập các file ảnh chụp màn hình gần nhất thay vì file avatar mới được push vào (`avatar.jpg`). Kết quả là picker tap vào tile đầu tiên sẽ chọn nhầm ảnh chụp màn hình thay vì avatar thật.
3. **Proxy Socket Stall (`ERR_PROXY_CONNECTION_FAILED`)**: Tiến trình TikTok chạy lâu trên thiết bị qua proxy cục bộ (`192.168.110.2:200xx`) có thể bị treo hoặc đứt gãy socket ngầm (`CronetUrlRequest: net::ERR_PROXY_CONNECTION_FAILED`). Khi người dùng/script bấm nút "Lưu" (Save) ở màn hình crop, request HTTP POST upload lên `location.tiktokv.com` / `api.tiktokv.com` thất bại trong âm thầm, không hiển thị toast lỗi rõ ràng, dẫn đến việc app quay lại profile mà không đổi được ảnh.

---

## Giải pháp Kỹ thuật Chuẩn hóa

### 1. Cách ly Screencap khỏi MediaStore (Anti-Clutter)
- Tuyệt đối KHÔNG lưu file chụp màn hình kiểm tra vào `/sdcard/*.png` hoặc `/sdcard/DCIM/Camera/` nếu không có cờ `.nomedia`.
- **Thư mục cache chuẩn:** Tạo và sử dụng `/sdcard/sc_cache/` có file `.nomedia`:
  ```bash
  adb shell mkdir -p /sdcard/sc_cache
  adb shell touch /sdcard/sc_cache/.nomedia
  ```
- Hoặc chụp thẳng vào `/data/local/tmp/screenshot.png` rồi pull về PC:
  ```bash
  adb shell screencap -p /data/local/tmp/screencap.png
  adb pull /data/local/tmp/screencap.png ./local_screen.png
  ```
- **Dọn dẹp rác MediaStore trước khi up avatar:**
  ```bash
  adb shell "content delete --uri content://media/external/images/media --where \"_data LIKE '%.png'\""
  # Hoặc xóa toàn bộ rows cũ trước khi push file avatar mới
  adb shell content delete --uri content://media/external/images/media
  ```

### 2. Chuẩn bị file avatar duy nhất & Đăng ký MediaStore
- Đặt tên file duy nhất theo timestamp để tránh trùng cache:
  ```bash
  adb push D:/TIKTOK-videonuoinick/<folder>/avatar.jpg /sdcard/DCIM/Camera/IMG_avatar_target.jpg
  adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/IMG_avatar_target.jpg
  ```
- Kiểm tra lại MediaStore đảm bảo chỉ có đúng 1 ảnh mục tiêu ở vị trí đầu tiên:
  ```bash
  adb shell content query --uri content://media/external/images/media
  ```

### 3. Khởi động lại TikTok sạch (Clean Process) phòng ngừa Proxy Socket Stall
- Trước khi thực hiện luồng đổi avatar, nếu phát hiện app đã mở lâu hoặc có dấu hiệu nghẽn mạng:
  ```bash
  adb shell am force-stop com.ss.android.ugc.trill
  sleep 2
  adb shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
  sleep 3
  ```
- Thao tác này làm mới kết nối mạng qua proxy, đảm bảo request upload avatar lên server thành công ngay lần bấm Lưu đầu tiên.

### 4. Quy trình Thao tác UI (Layout Sửa hồ sơ / Layout C)
1. Mở tab **Hồ sơ** (`input tap 972 1864`).
2. Vào **Sửa hồ sơ** (`input tap 75 150`).
3. Tap **Thay đổi ảnh** (`input tap 540 580`).
4. Tap **Tải ảnh lên** trong bottom sheet (`input tap 250 1637`).
5. Tap checkbox ô đầu tiên trong Photo Picker (`input tap 225 255`).
6. Tap nút **Tiếp** (`input tap 912 1844`).
7. Ở màn hình Crop, tap nút **Lưu** (`input tap 792 1794`).
8. Chờ tối thiểu **8-10 giây** để request upload hoàn tất trước khi back về Profile (`input keyevent 4`).

---

## Kỷ luật Nghiệm thu Thị giác (Strict Gate 6 Verification)
- **CẤM TUYỆT ĐỐI suy diễn:** Không được kết luận avatar đã đổi chỉ vì script chạy hết các bước hoặc exit code == 0.
- **So sánh Mean BGR / Pixel Difference:** Trước khi báo cáo DONE, bắt buộc crop vùng avatar trên profile (`[708,300][1080,636]`), so sánh giá trị màu trung bình (Mean BGR) với ảnh avatar gốc (`avatar.jpg`) và ảnh avatar cũ. Nếu Mean BGR của avatar trên profile vẫn giống avatar cũ hoặc có giá trị lệch xa ảnh gốc (ví dụ toàn màu trắng `~245, 245, 245`), đó là bằng chứng avatar **CHƯA ĐƯỢC ĐỔI**.
- **Soi mắt qua Vision:** Phải dùng `browser_vision` mở ảnh crop avatar và xác nhận bằng mắt: đúng hình dạng nhân vật mới, rõ nét, không bị che bởi pop-up hay trắng màn hình.
