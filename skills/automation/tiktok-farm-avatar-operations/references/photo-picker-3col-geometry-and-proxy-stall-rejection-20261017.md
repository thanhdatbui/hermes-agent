# TikTok Avatar: Photo Picker 3-Column Grid, Radio Coordinates, and Proxy Stall Rejection (2026-10-17)

## Bối cảnh & Sự cố Thực tế
Trong phiên xử lý avatar Máy 34 Slot 6 (`@yobi1965`), đã xảy ra chuỗi lỗi nghiêm trọng dẫn đến việc avatar trên profile không hề thay đổi dù runner báo `ExitCode: 0` và `Verified: True`:
1. **Photo Picker 3-Column Grid & Video Thumbnail Collision**:
   - Giao diện Photo Picker của TikTok (v47+) trên màn hình `1080x1920` chia làm **3 cột** (`w = 360px` mỗi ô), không phải 4 cột.
   - Hàng 0 gồm:
     - Ô 0 (cột 0, `x = 0..360, y = 200..560`): Thường là video hoặc thumbnail video gần nhất (`2.mp4` có sticker "20 lần").
     - Ô 1 (cột 1, `x = 360..720, y = 200..560`): File ảnh avatar mới push vào.
     - Ô 2 (cột 2, `x = 720..1080, y = 200..560`): Ảnh khác hoặc screenshot.
   - Nút radio tròn chọn ảnh (circle checkbox) nằm ở **góc trên bên phải của từng ô**, không phải ở giữa ô:
     - Checkbox Ô 0: `(300, 260)`
     - Checkbox Ô 1 (Ảnh mới): `(660, 260)`
     - Checkbox Ô 2: `(1020, 260)`
   - **Bẫy tap mù**: Nếu tap vào giữa ô `(405, 335)` hoặc `(140, 360)`, TikTok coi là tap xem trước hoặc chạm trúng ô khác, không kích hoạt radio chọn ảnh của Ô 1. Khi bấm nút Tiếp (`912, 1844`), picker sẽ lấy ô đang được chọn mặc định (Ô 0 - thumbnail video cây kim tiền / sticker "20 lần").

2. **Ảo giác bỏ qua WinRT OCR**:
   - Khi chạy OCR trên màn hình Cắt ảnh (Crop), kết quả trả về chữ `20)la` (từ sticker "20 lần" của video).
   - Agent không đọc kỹ OCR mà tự suy diễn ra mô tả "cô gái tập yoga", dẫn đến gửi ảnh sai hoàn toàn cho User.
   - **Quy tắc bất biến**: Nếu WinRT OCR xuất hiện bất kỳ từ khóa lạ (`20`, `lần`, `video`, `clip`, `thời lượng`) trên màn hình Crop -> **100% ĐÃ CHỌN NHẦM THUMBNAIL VIDEO**, cấm bấm Lưu và cấm báo cáo sai sự thật.

3. **Hiện tượng Proxy Socket Stall & Bấm Lưu Thất Bại Âm Thầm**:
   - Bấm nút Lưu (`792, 1794`) ở màn hình CropActivity, TikTok hiện toast *"Đang tải lên..."*, nhưng do proxy cục bộ (`192.168.110.2:200xx`) bị stall socket, request upload HTTP POST lên CDN TikTok thất bại âm thầm.
   - App tự đóng màn hình Crop về Profile hoặc Sửa hồ sơ mà **avatar vẫn giữ nguyên ảnh cũ**.
   - Runner auto thấy CropActivity đóng thì ngộ nhận là thành công (`avatar_status: FORCED_REPLACED_VERIFIED`), nhưng trên thực tế avatar trên máy không hề đổi.

---

## Quy trình Khắc phục Chuẩn hóa

### 1. Dọn sạch rác trước khi nạp
```bash
adb shell rm -rf /sdcard/DCIM/.thumbnails/*
adb shell rm -rf /sdcard/DCIM/Camera/*
adb shell rm -rf /sdcard/Pictures/*
adb push <local_avatar.jpg> /sdcard/DCIM/Camera/avatar_yoga.jpg
adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/avatar_yoga.jpg
```

### 2. Tọa độ Tap chuẩn trên Photo Picker (3 cột)
- Nếu Photo Picker hiển thị nhiều ô:
  - Chọn Ô 1 (nếu là ảnh mới đẩy vào): tap chính xác vào radio circle tại `(660, 260)`.
  - Tap nút **Tiếp** tại `(912, 1844)`.

### 3. Nghiệm thu kép bắt buộc (Double Verification Gate)
- **Gate 1 (Màn hình Crop)**:
  - Chụp màn hình Crop (`screencap`).
  - Chạy WinRT OCR: CẤM có các từ khóa video/rác (`20`, `lần`, `thời lượng`).
  - Dùng `browser_vision` soi trực tiếp: Xác nhận đúng chủ thể mới.
- **Gate 2 (Màn hình Profile thực tế sau khi Lưu)**:
  - Cắt vòng tròn avatar tại màn hình Profile:
    - Layout Top-Left Pencil: Avatar nằm ở góc trên bên phải `[756, 324][1044, 612]`.
    - Màn hình Sửa hồ sơ: Avatar nằm ở giữa `[400, 220][680, 500]`.
  - Tính Mean BGR của vòng tròn avatar trên máy và so sánh với ảnh cũ:
    - Nếu Mean BGR vẫn trùng hoặc gần giống avatar cũ (`diff < 15`) -> **CHẮC CHẮN UPLOAD THẤT BẠI DO LỖI MẠNG/PROXY**.
    - Phải force-stop TikTok (`am force-stop com.ss.android.ugc.trill`), làm mới proxy/kết nối rồi thực hiện lại.
    - TUYỆT ĐỐI CẤM báo DONE khi chưa so sánh Mean BGR xác nhận avatar trên Profile đã đổi thành công.
