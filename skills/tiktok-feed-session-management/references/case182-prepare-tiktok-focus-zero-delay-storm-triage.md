# Case 182: Triage Lỗi Hàng Loạt "prepare-tiktok failed to focus TikTok after launch" (Đốt Cạn Polling Attempts)

## 1. Hiện tượng thực tế (Ca 3, Phiên 1, Row 6)
Báo cáo Watchdog ghi nhận:
```text
• Tổng máy xử lý: 80 máy
• Lướt Feed:
  + Success (20): 5, 11, 13, 18, 23, 26, 28, 37, 38, 41, 43, 44, 48, 51, 54, 55, 58, 59, 60, 65
  + Fail (60): M1, M2, M3, M4, M6, M7, M8, M9, M10, M12, M14...
```
Người vận hành phát hiện tỉ lệ Success tụt giảm bất thường (chỉ đạt 20/80 máy).

## 2. Dữ liệu trích xuất hiện trường (O(1))
Soi trực tiếp file log chi tiết:
`D:\Taadaa\runtime\kibe\live\2026-09-20\row-6-180005\20260920-180247\log.jsonl` và `run_manifest.json`:
- **53 / 60 máy Fail** đều mang cùng một signature lỗi duy nhất:
  `failed -> prepare-tiktok failed to focus TikTok after launch`
- **3 máy**: `blocked-proxy-vpn` (M4, M10, M19: thiết bị mất kết nối ADB/USB).
- **1 máy**: `config-error` (M30: serial không tìm thấy trong danh sách thiết bị ADB).
- **3 máy**: `manual-needed` (M31 vướng popup kiểm tra, M45 vướng mismatch username switcher, M71 kẹt kết nối ATX).

## 3. Nguyên nhân cốt lõi (Root Cause)
Khi khởi động ứng dụng TikTok cho phiên nuôi:
1. Runner chạy `am force-stop com.ss.android.ugc.trill` -> thành công.
2. Runner kích hoạt mở app qua `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` -> trả về returncode 0 (`launch_tiktok success`).
3. Ngay sau đó, bước `verify_tiktok_focus` được gọi để polling kiểm tra xem TikTok đã lên foreground hay chưa qua vòng lặp tối đa 10 attempts (`max_attempts=10`, `retry_delay_seconds=1.5`).

### Điểm bất thường (Zero-Delay Polling Storm):
Trên **toàn bộ 53 máy bị fail**, toàn bộ **10 attempts kiểm tra bị thực thi dồn dập trong khoảng thời gian siêu ngắn từ 3 mili-giây đến 50 mili-giây** (dưới 0.1 giây):
```json
{"timestamp": "2026-09-20T11:03:41.782465+00:00", "action": "verify_tiktok_focus", "attempt": 1, "result": "failed", "focused_package": "com.android.systemui"}
{"timestamp": "2026-09-20T11:03:41.786719+00:00", "action": "verify_tiktok_focus", "attempt": 2, "result": "failed", "focused_package": "com.sec.android.app.launcher"}
...
{"timestamp": "2026-09-20T11:03:41.812728+00:00", "action": "verify_tiktok_focus", "attempt": 10, "result": "failed", "focused_package": "com.sec.android.app.launcher"}
```
- Trên máy Samsung Galaxy S7 thật, sau lệnh mở app, hệ điều hành Android cần từ **1.5 giây đến 3.5 giây** để nạp process và hiển thị giao diện TikTok.
- Việc 10 lần kiểm tra bị quét sạch trong 30ms khiến hệ thống kết luận app không mở được và fail-closed dừng toàn bộ phiên nuôi của máy ngay lập tức!
- **Tại sao 20 máy kia lại thành công?** Ở 20 máy đó, hệ điều hành Samsung trả về focus trúng TikTok sớm hơn một chút ở Attempt 2 hoặc 3 (trong tích tắc vài mili-giây đầu) nên may mắn vượt qua được cửa ải khởi động.

### So sánh đối soát với ca bình thường (Ca 14:00 - Row 4: 66 máy Success):
- **Khác biệt trạng thái màn hình (Screen OFF vs Screen ON)**:
  - Ở Ca 14:00: Các máy đang ở trạng thái Màn hình TẮT (`screen_on: False`), luồng chạy qua `wake_screen` (`keyevent 224`), reset trạng thái Surface của WindowManager. Khi `monkey launch` bắn ra, TikTok được cấp foreground ưu tiên ngay tức thì.
  - Ở Ca 18:00: Các máy đang Màn hình BẬT sẵn (`screen_on: True`), và giao diện đang dừng ở TouchWiz Launcher.
- **Nghẽn tiến trình đóng Recent Apps (30s - 50s)**:
  - Bước `close_all_apps_start` gọi `keyevent 187` rồi `keyevent 3` (Home) bị nghẽn 30s-50s do 80 máy chạy đồng loạt. Sau khi bấm Home, TouchWiz Launcher đang bận chu kỳ animation vẽ lại trang chủ.
  - Lệnh `monkey` chỉ giả lập 1 sự kiện chạm vào icon, dễ bị hệ điều hành bỏ qua khi Launcher đang bận animation, khiến TikTok không thực sự được bật lên.
- **Hiện tượng Log Timestamp**:
  - `close_all_apps_start` được ghi log lúc bắt đầu chạy, `force_stop_tiktok` ghi log sau khi dọn xong (sau 30s).
  - Vòng lặp `verify_tiktok_focus` trong `prepare_app_for_automation` ghi log các step với timestamp thời điểm flush/log, khiến các attempts hiển thị dồn cục trong cùng 1 tích tắc.

## 4. Giải pháp khắc phục chuẩn (Fix & Prevention)
- Khi thực thi kiểm tra focus sau khi mở app trong `prepare_app_for_automation` (`automation-core/src/automation_core/startup.py`) và `python_runner/flows/device_prepare.py`:
  - Thêm nhịp settle `1.0s` sau khi gửi phím Home dọn Recent Apps trước khi bắn lệnh khởi động TikTok để Launcher kịp ổn định.
  - Bổ sung cơ chế fallback dùng intent tường minh (`am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`) thay vì chỉ phụ thuộc vào `monkey` đơn thuần khi launcher đang bận.
  - Đảm bảo nhịp polling retry kiểm tra focus có độ trễ thực tế `1.5s` và re-launch app nếu sau 3 lần vẫn chưa thấy app lên foreground.
