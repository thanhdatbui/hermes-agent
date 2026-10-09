# Android Screencap Black Screen Pitfall & Mobile Chrome WebView Cookie Blindness (2026-09-19)

## 1. Bẫy Screencap Màn Hình Đen (Black Screen / Pitch-Black Screencap)

### Triệu chứng:
File ảnh chụp qua lệnh ADB `adb exec-out screencap -p > screen.png` có kích thước bình thường nhưng mở ra đen kịt 100% (`#000000`), không có bất kỳ điểm ảnh hay nội dung nào. User phản ánh: *"Gì tối đen v?"*.

### Nguyên nhân kỹ thuật:
- Thiết bị Android (Samsung Galaxy S7) đang ở chế độ **Sleep / Tắt màn hình (Display Power: state=OFF, mWakefulness=Asleep/Dozing)**.
- Khi màn hình tắt, GPU/SurfaceFlinger không render ra framebuffer hiển thị, dẫn đến `screencap` chụp đúng vùng đệm đen.

### Cách phòng ngừa & Khắc phục chuẩn:
1. **Luôn đánh thức thiết bị trước khi screencap**:
   ```bash
   adb -s <SERIAL> shell input keyevent 224   # WAKEUP màn hình
   # Hoặc đánh thức qua power:
   adb -s <SERIAL> shell "dumpsys power | grep -q 'state=OFF' && input keyevent 26"
   ```
2. **Kiểm tra trạng thái Display Power trước khi chụp**:
   ```python
   res = subprocess.run([ADB_EXE, "-s", serial, "shell", "dumpsys", "power"], capture_output=True, text=True)
   if "state=OFF" in res.stdout or "mWakefulness=Asleep" in res.stdout:
       subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "224"])
       time.sleep(0.5)
   ```
3. **Chụp vào thẻ nhớ nội bộ trước khi kéo ra (tránh lỗi ngắt pipe trên Windows MSYS)**:
   ```bash
   adb -s <SERIAL> shell screencap -p /sdcard/screen_temp.png
   adb -s <SERIAL> pull /sdcard/screen_temp.png /path/to/local.png
   ```

---

## 2. Điểm Mù UI Automator XML trong Chrome Android WebView (ChatGPT Cookie Popup)

### Triệu chứng:
- Script mở `https://chatgpt.com/auth/login?screen_hint=signup` trên Chrome Android.
- Màn hình thực tế hiện popup *"Chúng tôi sử dụng cookie... Chấp nhận tất cả"*.
- Script chạy `uiautomator dump` nhưng không tìm thấy nút Cookie, timeout sau 120s và văng lỗi `FAILED_AT_EMAIL_SUBMIT`.

### Nguyên nhân kỹ thuật:
- Trình duyệt Chrome trên Android đóng gói toàn bộ nội dung web bên trong một container WebView nguyên khối:
  ```xml
  <node class="android.widget.FrameLayout" content-desc="Lượt xem trên web" bounds="[0,72][1080,1920]" />
  ```
- Các thẻ HTML/DOM bên trong trang web **hoàn toàn không được xuất ra cây UI Accessibility XML của Android**, khiến các hàm `find_node_in_xml` bị mù 100%.

### Giải pháp chuẩn:
1. **Fallback tọa độ chuẩn màn hình S7 (1080x1920)** khi cây XML bị rỗng / chỉ có `Lượt xem trên web`:
   - Nút **"Chấp nhận tất cả" (Accept all cookies)**: Tọa độ trung tâm `(540, 1780)`.
   - Nút **"Đóng" (Close cookie popup)**: Tọa độ `(972, 1266)`.
   - Ô input **"Email address"**: Tọa độ `(540, 1150)`.
   - Nút **"Tiếp tục" (Continue)**: Tọa độ `(540, 1320)`.
2. **Xác thực bằng WinRT OCR**: Khi không chắc chắn, dùng tool `winrt_ocr.py` quét nhanh ảnh screencap thật để lấy tọa độ bounds của text thay vì dựa hoàn toàn vào `uiautomator dump`.
