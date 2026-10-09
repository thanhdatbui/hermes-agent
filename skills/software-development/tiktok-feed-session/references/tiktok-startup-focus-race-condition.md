# Chẩn Đoán Lỗi Chuỗi Khởi Động TikTok (Startup Race Condition & Launcher Focus Occlusion)

## Hiện Tượng Lỗi (Sự Cố Hàng Loạt Ca 3 18:00 - Row 6)
- **Tỷ lệ thất bại đột biến**: 53/80 máy fail đồng loạt với lỗi:
  `prepare-tiktok failed to focus TikTok after launch`
- **Thời gian cháy attempts**: Toàn bộ 10 attempts của `verify_tiktok_focus` bị thiêu rụi chỉ trong 30ms – 100ms (zero-delay execution).
- **Trạng thái focus ghi nhận**: Bị kẹt ở `com.sec.android.app.launcher` hoặc `com.android.systemui`.

## Cơ Chế Kỹ Thuật & Root Cause

### 1. Sự khác biệt giữa Screen OFF (Sleep) và Screen ON (TouchWiz Launcher Settle)
- **Khi máy đang Sleep (`screen_on: False`)**:
  - `safe_wake_unlock_preflight` đánh thức màn hình bằng `keyevent 224` / dismiss keyguard.
  - WindowManager của Samsung được đưa về trạng thái sạch, khi lệnh khởi động app bắn ra, Android cấp quyền foreground trực tiếp cho TikTok ngay ở Attempt 2–3.
- **Khi máy đang ON (`screen_on: True`) và vừa chạy xong `close_all_recent_apps`**:
  - `close_all_apps_start` gọi `keyevent 187` (Recent Apps) rồi `keyevent 3` (Home).
  - Khi chạy 80 máy song song, I/O và CPU cao khiến quá trình dọn Recent Apps kéo dài 30s – 50s.
  - Sau khi Home được bấm, TouchWiz Launcher của Samsung (`com.sec.android.app.launcher`) đang bận trong chu kỳ animation vẽ lại trang chủ.

### 2. Hạn chế của lệnh khởi động bằng `monkey`
- Lệnh gọi mở TikTok mặc định:
  `adb shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
- `monkey` chỉ giả lập 1 sự kiện tap/touch vào icon ứng dụng. Khi Launcher đang bận render hoặc xử lý animation của Home, sự kiện monkey có thể bị hệ điều hành bỏ qua (drop event), khiến app TikTok không hề được kích hoạt mở lên màn hình.

### 3. Nguyên nhân 10 Attempts bị quét sạch trong 30ms (Zero Delay Polling)
- Trong `automation_core/src/automation_core/startup.py`, vòng lặp `verify_app_focus` gọi `focus_reader()`.
- Nếu `focus_reader` đọc qua ATX session hoặc cache UI nhanh mà không có nhịp `sleep` cưỡng bức thực tế khi đọc liên tiếp các giá trị fail, hoặc nếu biến delay không hoạt động đúng trong bối cảnh batch runner, 10 lần kiểm tra sẽ diễn ra ngay lập tức trước khi hệ điều hành kịp bung splash screen (vốn cần 1.5s - 3s trên Galaxy S7).

## Quy Tắc Phòng Ngừa & Chuẩn Hóa Khởi Động (Best Practices)
1. **Fallback Intent tường minh (`am start`)**:
   - Khi `monkey` không đưa được TikTok lên foreground sau nhịp đầu tiên, lập tức fallback sang lệnh khởi động tường minh:
     `adb shell am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`
2. **Nhịp Settle sau Close Recents**:
   - Bắt buộc có nhịp nghỉ tối thiểu `1.0s` sau khi gửi phím Home dọn Recent Apps trước khi bắn lệnh khởi động TikTok để Launcher kịp hoàn tất animation.
3. **Bảo toàn khoảng cách Polling (Guaranteed Sleep)**:
   - Trong mọi vòng lặp kiểm tra focus sau launch, mỗi attempt fail bắt buộc phải `time.sleep(1.0)` đến `1.5s` thực tế, tuyệt đối không được để vòng lặp quay tự do (busy-loop/spin-loop).
