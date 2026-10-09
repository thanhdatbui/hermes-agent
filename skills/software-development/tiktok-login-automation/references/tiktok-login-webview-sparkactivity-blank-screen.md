# TikTok Login Webview Blank Screen (SparkActivity & Old Android WebView v70)

## 1. Hiện Tượng (Symptoms)
- Khi thực hiện login TikTok trên điện thoại Android cũ (Samsung S7 Android 8.0), sau khi nhập email/pass hoặc sau khi submit mã OTP thành công, app chuyển sang một Activity mới và màn hình bị **TRẮNG XÓA HOÀN TOÀN** (`SparkActivity`).
- Kiểm tra focus:
  `mCurrentFocus=Window{... com.ss.android.ugc.trill/com.bytedance.hybrid.spark.page.SparkActivity}`
- Kiểm tra logcat phát hiện lỗi crash Javascript:
  `Uncaught SyntaxError: Unexpected token ?`
  tại file bundle: `.../tiktok_account/idv-inapp-webview/resource/js/vendor.e60f8a52.js`

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **TikTok Suspicious Login Challenge**: Khi đăng nhập trên thiết bị lạ / IP proxy mới, TikTok kích hoạt luồng xác minh thiết bị qua webview nội bộ (`ucenter_web/idv_inapp/verification?enter_from=suspicious_login`).
2. **Cú pháp JS hiện đại (ES2020+)**: Trang webview của TikTok sử dụng Optional Chaining (`?.`) hoặc Nullish Coalescing (`??`).
3. **Android System WebView / Chrome bị cũ (Outdated)**: Máy mới xuất xưởng hoặc chưa update WebView thường chạy phiên bản mặc định rất thấp (ví dụ Android 8.0 đi kèm Chrome/WebView v68 - v70). Nhân Chromium v70 (năm 2018) chưa hỗ trợ cú pháp `?` của ES2020 nên toàn bộ bundle JS bị parse error và chết ngay tại khởi tạo, khiến màn hình trắng tinh, không render được Captcha hay nút xác minh.

## 3. Quy Trình Khắc Phục Chuẩn (Remediation)
1. **Kiểm tra phiên bản WebView trên máy**:
   ```bash
   adb -s <serial> shell "dumpsys package com.google.android.webview | grep -E 'versionName|versionCode'"
   adb -s <serial> shell "dumpsys package com.android.chrome | grep -E 'versionName|versionCode'"
   ```
2. **Cập nhật Android System WebView / Chrome**:
   - Cài đặt APK `com.google.android.webview` hoặc `com.android.chrome` phiên bản mới hơn (tối thiểu Chrome/WebView v85+ hoặc bản tương thích tốt nhất với Android 8.0 armeabi-v7a).
3. **Cơ chế Hotmail OAuth Bypass (Graph API)**:
   - Với tài khoản có OAuth Token (`mail|pass|refresh_token|client_id`), trích xuất Magic Link từ mail:
     `hotmail_provider._graph_newest_magic_url(email, refresh_token, client_id)`
   - Mở Magic Link trực tiếp qua Chrome hoặc Intent TikTok để bypass xác minh thủ công khi webview bị lỗi.
