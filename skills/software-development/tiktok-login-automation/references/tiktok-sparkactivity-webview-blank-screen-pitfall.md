# Cạm Bẫy: Trắng Màn Hình WebView SparkActivity Khi Xác Minh Thiết Bị TikTok Trên Máy Farm Mới

## 1. Hiện Tượng (Symptoms)
- Khi đăng nhập tài khoản TikTok trên máy mới (hoặc thiết bị lạ), sau khi điền email, mật khẩu hoặc mã OTP xác minh qua mail, TikTok kích hoạt cơ chế `suspicious_login`:
  ```text
  Activity: com.ss.android.ugc.trill/com.bytedance.hybrid.spark.page.SparkActivity
  Prefetch URL: https://inapp.tiktokv.com/ucenter_web/idv_inapp/verification?enter_from=suspicious_login&page=suspicious_login
  ```
- **Màn hình điện thoại bị TRẮNG XÓA HOÀN TOÀN** (`m30_man_hinh_trang_webview_loi.png`). Không có DOM XML native (chỉ có FrameLayout trống), không render nút xác nhận hay Captcha kéo hình.
- Phím cứng / Back bị chặn hoặc không có tác dụng. Script automation rơi vào timeout 180s - 300s.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
Kiểm tra `logcat -d -s chromium` thấy lỗi JavaScript:
```javascript
Uncaught SyntaxError: Unexpected token ?
source: https://sf16-website-login.neutral.ttwstatic.com/obj/tiktok_web_login_static/tiktok_account/idv-inapp-webview/resource/js/vendor.e60f8a52.js (1)
```

- **Nguyên nhân:**
  1. Trang web xác minh bảo mật của TikTok (`idv-inapp-webview`) sử dụng các cú pháp JavaScript hiện đại (ECMAScript 2020+ như Optional Chaining `?.` hoặc Nullish Coalescing `??`).
  2. Máy Samsung S7 mới xuất xưởng hoặc ROM gốc Android 8.0 chỉ đi kèm bản `com.google.android.webview` / `com.android.chrome` mặc định phiên bản cũ (ví dụ **v70.0.3538.110** hoặc v68).
  3. Nhân V8 của Chromium v70 chưa hỗ trợ cú pháp toán tử `?` ➔ Toàn bộ bundle JavaScript của TikTok crash ngay ở dòng đầu tiên của file `vendor.*.js`.
  4. Webview bị treo ở màn hình trắng, không bao giờ load xong UI xác minh để người dùng hoặc bot thao tác tiếp.

## 3. Quy Trình Khắc Phục Chuẩn
1. **Kiểm tra phiên bản WebView hiện tại qua ADB:**
   ```bash
   adb -s <SERIAL> shell "dumpsys package com.google.android.webview | grep -E 'versionName|versionCode'"
   adb -s <SERIAL> shell "dumpsys package com.android.chrome | grep -E 'versionName|versionCode'"
   ```
   Nếu `versionName` < 80 (đặc biệt các bản 68-70 mặc định của Android 8), WebView chắc chắn sẽ bị crash khi gặp trang webview hiện đại của TikTok.

2. **Nâng cấp Android System WebView / Chrome APK:**
   - Cài đặt bản WebView/Chrome APK tương thích tối thiểu từ version **85+** trở lên (hỗ trợ đầy đủ ES2020 syntax):
     ```bash
     adb -s <SERIAL> install -r -d -g "D:/OneDrive/apk-bank/com_google_android_webview/webview_v100+.apk"
     ```
   - Xác nhận WebView Provider đã chuyển sang bản mới:
     ```bash
     adb -s <SERIAL> shell "dumpsys webviewupdate"
     ```

## 4. Bằng Chứng Báo Cáo Nghiệm Thu & Tránh Phản Cảm Với User
- **Quy tắc Gate 6 & Giao tiếp:** Khi báo cáo lỗi cho User, **TUYỆT ĐỐI KHÔNG** gửi ảnh chụp màn hình HOME (đã dọn dẹp teardown) rồi nói là đang lỗi. Phải gửi **ĐÚNG ẢNH MÀN HÌNH LỖI THỰC TẾ** (`MEDIA:<path_loi>`), ví dụ màn hình trắng WebView hoặc màn hình OTP báo đỏ `Nhập đúng mã PIN`.
