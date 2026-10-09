# Case UI-69: Kỹ Thuật Nạp Bytecode Split Dex `split_df_a_dex` Khi Cài Đè TikTok 47.0.3 Toàn Dàn

## 1. Bối cảnh & Hiện tượng
- **Triệu chứng:** Khi cập nhật TikTok lên phiên bản `47.0.3` bằng lệnh cài đặt split cơ bản:
  ```bash
  adb install-multiple -r -d base.apk split_config.arm64_v8a.apk split_config.vi.apk split_config.xxhdpi.apk
  ```
  Lệnh trả về `Success`, `versionName=47.0.3`, nhưng khi khởi động ứng dụng:
  - App lập tức bị văng / crash ngay tại màn hình Splash.
  - Logcat báo lỗi chí mạng:
    `Caused by: java.lang.ClassNotFoundException: Didn't find class "X.0gEx"` hoặc `LooperProtectEnhanceSettingAppDiffProtocol`.
  - Kiểm tra splits: `dumpsys package com.ss.android.ugc.trill | grep splits=` chỉ hiển thị 4 split cơ bản, thiếu hoàn toàn các split tính năng.

## 2. Nguyên nhân kỹ thuật (Root Cause)
- Trên TikTok 47.0.3, ByteDance đã chia nhỏ cấu trúc bytecode DEX:
  - Toàn bộ class thực thi nghiệp vụ cốt lõi nằm trong file **`split_df_a_dex.apk` (nặng ~80MB)**.
  - Nếu thiếu file này, Android Runtime (ART) không thể load được các class cơ sở và buộc phải kill tiến trình ứng dụng.
- **Tại sao không thể dùng `adb install-multiple` trực tiếp với `split_df_a_dex.apk`?**
  - File nặng 80MB truyền qua USB ADB đồng thời với 4 file split khác thường bị timeout socket trên Samsung S7 (vượt quá 180s-300s).
  - Lệnh `adb install-multiple` đẩy toàn bộ file qua stream một lần, nếu bị rớt giữa chừng sẽ gây hỏng session cài đặt (`Files still open` hoặc `INSTALL_PARSE_FAILED_UNEXPECTED_EXCEPTION`).

## 3. Quy trình nạp chuẩn xác (Two-Stage Push + Install Session)
Để nạp `split_df_a_dex.apk` vào thiết bị Samsung S7 an toàn 100% không bị timeout:

### Bước 1: Push file APK độc lập vào bộ nhớ tạm của thiết bị
```bash
adb -s <SERIAL> push "D:/Taadaa/apks/tiktok_47_0_3/split_df_a_dex.apk" /data/local/tmp/split_df_a_dex.apk
```
*Lợi thế:* `adb push` có buffer riêng, truyền ổn định không phụ thuộc vào tiến trình package manager của Android.

### Bước 2: Tạo Install Session ghép nối gói ứng dụng hiện có
```bash
adb -s <SERIAL> shell "
# Lấy session ID với cờ -p (ghép vào package đang có) và -i com.android.vending (giữ cờ cài đặt từ Google Play Store)
sid=\$(pm install-create -r -d -i com.android.vending -p com.ss.android.ugc.trill | cut -d'[' -f2 | cut -d']' -f1)

# Ghi stream file split_df_a_dex từ /data/local/tmp vào session
pm install-write -S 83814343 \$sid split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk

# Hoàn tất cài đặt và dọn file tạm
pm install-commit \$sid
rm -f /data/local/tmp/split_df_a_dex.apk
"
```

### Bước 3: Nghiệm thu kết quả
1. Kiểm tra danh sách splits:
   ```bash
   adb -s <SERIAL> shell "dumpsys package com.ss.android.ugc.trill | grep splits="
   # Kỳ vọng: splits=[base, config.arm64_v8a, config.vi, config.xxhdpi, df_a_dex]
   ```
2. Mở thử ứng dụng:
   ```bash
   adb -s <SERIAL> shell "am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity"
   # Sau 3-4s kiểm tra dumpsys window | grep mCurrentFocus -> Phải hiển thị SplashActivity / MainActivity, KHÔNG được crash về Launcher.
   ```
3. Đưa máy về HOME an toàn:
   ```bash
   adb -s <SERIAL> shell "input keyevent 3"
   ```

## 4. Kỷ luật vận hành Farm
- **Giới hạn số worker song song:** Khi chạy batch nạp `split_df_a_dex.apk` trên dàn lớn, chỉ chạy tối đa **4 workers song song** (`max_workers=4`) để bảo toàn băng thông USB Hub và nguồn điện thoại, cấm đẩy lên 10-20 workers gây nghẽn USB bus làm rớt thiết bị.
