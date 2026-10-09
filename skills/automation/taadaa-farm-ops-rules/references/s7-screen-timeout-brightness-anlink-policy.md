# Quy Tắc Cấu Hình Màn Hình S7 Farm: Tắt Màn Hình 10 Phút & Độ Sáng AnLink

## 1. Bản Chất Vấn Đề "Cài Tắt Màn Hình Nhưng Chạy Một Hồi Lại Sáng"
- Khi runner/script chạy, hàm `prepare_device()` trong `automation-core/src/automation_core/device.py` từng gọi `configure_stay_on()` với:
  - `svc power stayon true`
  - `settings put global stay_on_while_plugged_in 7` (ép sạc/cắm USB sáng vĩnh viễn)
  - `settings put system screen_off_timeout 1800000` (30 phút)
- Dù user có chỉnh tay trong Settings của máy là 10 phút tắt, hễ runner khởi động là bị ghi đè lại `stay_on_while_plugged_in = 7`.

## 2. Chuẩn Cấu Hình Tắt Màn Hình Farm S7
Để máy tự tắt màn hình sau khi chạy xong ca hoặc khi idle:
- **Tắt chế độ luôn sáng khi cắm cáp:**
  ```bash
  adb shell svc power stayon false
  adb shell settings put global stay_on_while_plugged_in 0
  ```
- **Đặt thời gian chờ tắt màn hình 10 phút (600,000 ms):**
  ```bash
  adb shell settings put system screen_off_timeout 600000
  ```
- **Hành vi thực tế:**
  - Trong lúc script đang chạy: ADB tap/swipe/dump XML liên tục kích hoạt tương tác, máy duy trì trạng thái hoạt động.
  - Sau khi kết thúc ca về HOME: Không còn lệnh ADB nào tác động, sau đúng 10 phút màn hình máy tự tắt ngủ.

## 3. Chế Độ Độ Sáng Bằng 0 (Xem Bằng Tool Con Gấu / AnLink)
- **AnLink / Scrcpy hoạt động qua ADB Framebuffer:**
  - Lệnh hạ độ sáng về 0:
    ```bash
    adb shell settings put system screen_brightness_mode 0
    adb shell settings put system screen_brightness 0
    ```
  - **Tác dụng:** Màn hình vật lý bên ngoài tối thui giúp giảm nhiệt độ máy đáng kể và chống ám/cháy màn hình AMOLED S7.
  - **Khả năng xem/điều khiển:** Tool con gấu (AnLink) vẫn lấy hình ảnh bình thường 100% từ chip xử lý đồ họa/framebuffer, không bị ảnh hưởng bởi độ sáng màn hình vật lý.
  - **Lưu ý:** Chỉ khi gửi phím tắt màn hình / Sleep cứng (`keyevent 223`) thì AnLink mới bị mất hiển thị (đen màn).
