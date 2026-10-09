# Quy chuẩn Màn hình Farm Android S7: Độ sáng min & Tự động tắt màn hình (2026-09-13)

## 1. Bối cảnh & Nguyên nhân màn hình không bao giờ tắt
- **Triệu chứng:** Farm S7 cài đặt màn hình tắt sau một thời gian không dùng, nhưng khi chạy batch xong màn hình vẫn sáng liên tục cả ngày đêm.
- **Nguyên nhân gốc rễ:** 
  - Trong `automation-core/src/automation_core/device.py` (`configure_stay_on`) và `tiktok-luot nuoi acc/python_runner/flows/device_prepare.py` (`configure_device_screen_stay_on`) đều có lệnh cưỡng bức:
    - `svc power stayon true`
    - `settings put global stay_on_while_plugged_in 7` (ép màn hình sáng vĩnh viễn khi cắm cáp USB/sạc).
    - `settings put system screen_off_timeout 1800000` (timeout 30 phút).
  - Khi script chạy, các lệnh này tự động ghi đè cài đặt người dùng.

## 2. Giải pháp Chuẩn hóa (Production Standard)
- **Bỏ ép sáng vĩnh viễn khi cắm sạc:**
  - `svc power stayon false`
  - `settings put global stay_on_while_plugged_in 0`
- **Thời gian chờ tắt màn hình khi rảnh (Idle Timeout):**
  - Đặt về 10 phút: `settings put system screen_off_timeout 600000`
- **Cơ chế hoạt động:**
  - Trong lúc chạy task: ADB tap/swipe liên tục reset timer Android -> màn hình duy trì sáng, view remote qua tool con gấu (AnLink) bình thường.
  - Khi hoàn thành task về HOME: Không còn lệnh ADB tương tác -> sau đúng 10 phút màn hình tự động tắt để hạ nhiệt máy và bảo vệ màn hình.

## 3. Hạ độ sáng vật lý về 0 (Tiết kiệm điện, chống ám màn AMOLED)
- **Thiết lập:**
  - `settings put system screen_brightness_mode 0` (tắt tự động điều chỉnh độ sáng).
  - `settings put system screen_brightness 0` (kéo thanh sáng về 0).
- **Đặc tính tương thích với Remote Viewer (AnLink / Scrcpy):**
  - `screen_brightness 0` chỉ giảm đèn nền phần cứng trên màn hình vật lý.
  - Bộ đệm khung hình (Framebuffer) và chip đồ họa vẫn render 100% bình thường.
  - Trên tool AnLink (tool con gấu) vẫn xem và tương tác hình ảnh sáng rõ, mượt mà bình thường.
  - CẤM tắt màn hình bằng Sleep `keyevent 223` trong lúc đang chạy vì sẽ ngắt render và khiến AnLink bị đen màn hình.
