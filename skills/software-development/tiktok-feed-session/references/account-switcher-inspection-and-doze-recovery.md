# Account Switcher Inspection, Doze Screen Wakeup & Missing Account Diagnostics

## 1. Doze Screen Wakeup on Samsung S7 / Android 7 & 8
### Triệu chứng (Symptoms):
- Thiết bị ở trạng thái ngủ sâu ban đêm (`mWakefulness=Dozing`, `Display Power: state=OFF`).
- Gửi lệnh thông thường `input keyevent KEYCODE_WAKEUP` (224) hoặc `wm dismiss-keyguard` không làm sáng màn hình (`Display Power` vẫn là `OFF`).
- Ảnh `screencap` chụp ra bị đen tuyền 100% (RGB: 0, 0, 0, 255; dung lượng file xấp xỉ 12.491 bytes).
- Lệnh `uiautomator dump` bị văng lỗi: `ERROR: null root node returned by UiTestAutomationBridge`, khiến `atx-agent` trả HTTP 500 (`open /sdcard/window_dump.xml: no such file or directory`).

### Giải pháp chuẩn (Prescription):
```bash
# 1. Bật nguồn màn hình bằng KEYCODE_POWER (26)
adb -s <SERIAL> shell "input keyevent 26"

# 2. Xác thực màn hình đã thực sự bật sáng trước khi dump UI / screencap
adb -s <SERIAL> shell "dumpsys power | grep -iE 'Display Power|mWakefulness'"
# Kỳ vọng: Display Power: state=ON, mWakefulness=Awake

# 3. Mở khóa keyguard
adb -s <SERIAL> shell "wm dismiss-keyguard"
```

---

## 2. Phục Hồi Treo Splash Screen Khi Mở TikTok Từ Nền
### Triệu chứng (Symptoms):
- Mở `com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity` nhưng ứng dụng kẹt ở Splash Screen (chỉ thấy chữ "TikTok" giữa màn hình, `mCurrentFocus=null`).

### Giải pháp chuẩn (Prescription):
- Sử dụng Deep Link intent đánh thức trực tiếp Feed hoặc Profile thay vì khởi động lại activity splash:
```bash
# Force feed navigation
adb -s <SERIAL> shell "am start -a android.intent.action.VIEW -d 'snssdk1180://feed' com.ss.android.ugc.trill"
# Hoặc profile navigation
adb -s <SERIAL> shell "am start -a android.intent.action.VIEW -d 'snssdk1180://user/profile' com.ss.android.ugc.trill"
```

---

## 3. Tọa Độ Mở Account Switcher Trên Profile TikTok Mới
### Vấn đề:
- Tọa độ cũ `(539, 140)` giả định thanh header sticky đã cuộn lên trên cùng. Nếu màn hình Profile chưa cuộn, nút tên hiển thị/tài khoản nằm ở khu vực giữa trên:
  - Tọa độ click chuẩn mở Switcher: `(540, 550)` hoặc `(285, 328)`.
  - Hoặc vuốt nhẹ màn hình lên (`swipe 540 1100 540 600 250`) để bung sticky header rồi tap `(500, 140)`.

---

## 4. Chẩn Đoán Lỗi P0 `account-switcher-missing-expected`
Khi nhận cảnh báo `manual-needed:account-switcher-missing-expected`:
1. **Không vội kết luận nick bị mất/văng:**
   - Dùng script WinRT OCR (`windows-native-ocr`) quét ảnh chụp switcher (`mN_switcher.png`) để bóc tách toàn bộ danh sách username hiển thị.
2. **Đối chiếu 3 nguồn dữ liệu:**
   - App Switcher thực tế trên máy (thường có 7-8 nick).
   - Workbook ca chạy `taikhoan_run_safe.xlsx`.
   - File gốc `taikhoan_dat_v2_updated .xlsx` và `tiktok_tracker.db` (`farm_account_info`).
3. **Phân biệt 2 tình huống:**
   - Nick ca hiện tại **VẪN CÒN** trong app, nhưng máy bị thiếu nick ở một slot khác (ví dụ thiếu slot 3 do đã từng dọn nick ký sinh), dẫn đến danh sách hiển thị chỉ có 7 nick và script gặp timeout/animation delay khi tìm row.
   - Nick ca hiện tại thực sự bị văng: Lúc này mới kích hoạt luồng login bổ sung qua `tiktok-log-in`.
