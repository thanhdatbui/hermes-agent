# Chẩn đoán lỗi hàng loạt "failed to focus TikTok after launch" do thiếu split_df_a_dex (TikTok 47.x)

## Hiện tượng lỗi
- Alert hàng loạt: `focus-device-issue:prepare-tiktok failed to focus TikTok after launch` (tỷ lệ lỗi 50% - 80% fleet).
- Người vận hành thường nghi ngờ có commit git / bản sửa code gần nhất làm hỏng luồng mở app.
- Khi inspect máy bằng `inspect_machine.py <N>`, `mCurrentFocus` vẫn giữ nguyên ở màn hình Launcher (`com.sec.android.app.launcher/...LauncherActivity`).

## Quy trình chẩn đoán O(1) xác định nguyên nhân gốc

### Bước 1: Khởi động app thủ công và bắt logcat crash
Chạy lệnh trực tiếp trên máy canary:
```bash
adb -s <SERIAL> logcat -c
adb -s <SERIAL> shell am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity
sleep 2
adb -s <SERIAL> logcat -d | grep -iE "trill|crash|fatal|ClassNotFoundException"
```

Nếu logcat xuất hiện:
```text
Caused by: java.lang.ClassNotFoundException: Didn't find class "X.0zu2" on path: DexPathList[[zip file ".../base.apk", zip file ".../split_config.arm64_v8a.apk", ...]
```
👉 TikTok bị crash ngay lập tức (instant crash) trong lúc nạp lớp dex ban đầu và Android đẩy trả về màn hình Launcher.

### Bước 2: Kiểm tra danh sách split APK đã nạp
```bash
adb -s <SERIAL> shell dumpsys package com.ss.android.ugc.trill | grep "splits="
```

- **Máy chuẩn (hoạt động tốt):**
  `splits=[base, config.arm64_v8a, config.vi, config.xxhdpi, df_a_dex]`
- **Máy lỗi (crash):**
  `splits=[base, config.arm64_v8a, config.vi, config.xxhdpi]`
  *(Thiếu hoàn toàn phân vùng split `df_a_dex` dung lượng ~80MB chứa code thực thi chính).*

## Nguyên nhân
Trong đợt update TikTok lên 47.0.3, quy trình cài đặt split APK bị gián đoạn, timeout hoặc script cài đặt chỉ nạp 4 file split cấu hình cơ bản mà chưa hoàn tất nạp `split_df_a_dex.apk` qua 2-stage push + install session.

## Cách khắc phục & Recovery
Nạp bổ sung `split_df_a_dex.apk` qua install session mà không làm mất dữ liệu / session tài khoản:
```bash
# Tạo install session bổ sung
SESSION_ID=$(adb -s <SERIAL> shell pm install-create -r -p com.ss.android.ugc.trill | grep -oE '[0-9]+')

# Push và nạp split_df_a_dex.apk vào session
adb -s <SERIAL> push D:/Taadaa/apks/tiktok_47_0_3/split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk
adb -s <SERIAL> shell pm install-write -S $(stat -c%s D:/Taadaa/apks/tiktok_47_0_3/split_df_a_dex.apk) $SESSION_ID split_df_a_dex /data/local/tmp/split_df_a_dex.apk

# Commit session
adb -s <SERIAL> shell pm install-commit $SESSION_ID
adb -s <SERIAL> shell rm -f /data/local/tmp/split_df_a_dex.apk

# Khóa auto-update Play Store chống drift phiên bản ngầm
adb -s <SERIAL> shell settings put global auto_update_apps 0
```
Sau khi nạp xong, kiểm tra lại `dumpsys package com.ss.android.ugc.trill | grep "splits="` đảm bảo có `df_a_dex`, sau đó khởi chạy lại app TikTok.

## Script Tự Động Hóa & Kho Lưu Trữ Chuẩn (21/09/2026)
- **Kho APK chuẩn:** `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\v47.0.3\` (chứa đủ 65 split APKs, base.apk 68MB, split_df_a_dex.apk 83.8MB, signature chính chủ ByteDance `2606a464`).
- **Script cài đặt chuẩn 1 lệnh:**
  ```bash
  python D:/Taadaa/apks/install_tiktok_47_0_3.py <SERIAL>
  ```

## Cảnh báo đặc thù tiến trình `dex2oat` trên Samsung S7 (Android 8)
- Khi gọi `pm install-commit`, Android kích hoạt tiến trình biên dịch `dex2oat` (ngốn ~900MB RAM, CPU 100%) để tối ưu hóa 83.8MB bytecode của `split_df_a_dex.apk`.
- Quá trình này mất từ **30s đến 90s**. Trong thời gian này, `splits=` vẫn chưa hiện `df_a_dex` và app chưa mở được.
- **CẤM TUYỆT ĐỐI:** Không force reboot hay kill session giữa chừng. Kiểm tra bằng `adb -s <SERIAL> shell "ps -A | grep -i dex2oat"`. Khi tiến trình `dex2oat` hoàn tất và biến mất khỏi process list, `dumpsys package ... | grep splits=` sẽ tự động cập nhật `df_a_dex`.

## Đánh giá an toàn Anti-Fraud (Sol High Verdict)
- Việc nạp APK split qua session ADB (`pm install-create/write/commit`) sử dụng bộ file trích xuất trực tiếp từ máy S7 có Google Play Store:
  - **Chứng thư số (Signatures):** Khớp 100% bản gốc ByteDance (`[2606a464]`).
  - **Installer flag:** `installerPackageName` có thể là `null` thay vì `com.android.vending`, nhưng TikTok server không quét cơ sở dữ liệu `PackageManager` để kill acc. Server TikTok tập trung vào chữ ký số (Signature), tính toàn vẹn client, và hành vi tương tác tự nhiên.
  - **Kết luận:** Nạp split dex sạch không phải nguyên nhân gây DIE nick. Sau khi nạp, bắt buộc khóa `auto_update_apps 0` trên toàn dàn để cố định môi trường và ngăn Google Play tự động cập nhật ngầm.

