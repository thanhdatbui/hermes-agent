# TikTok 47.0.3 Split APK Installation & Bytecode Recovery

## 1. Bản chất kiến trúc APK TikTok 47.x
Từ bản TikTok 47.0.3, ByteDance đã tách toàn bộ bytecode thực thi chính vào file:
`split_df_a_dex.apk` (~80-84MB).

Nếu chỉ dùng lệnh ADB cài đặt 4 file APK cơ bản (`base.apk`, `split_config.arm64_v8a.apk`, `split_config.vi.apk`, `split_config.xxhdpi.apk`):
- Lệnh ADB vẫn báo `Success`.
- `dumpsys package com.ss.android.ugc.trill | grep versionName` vẫn hiện `47.0.3`.
- **NHƯNG khi bấm mở app sẽ bị crash văng ngay lập tức** do lỗi:
  `java.lang.ClassNotFoundException: Didn't find class "X.1OEX"` (hoặc class tương tự).

## 2. Quy trình nạp split dex chuẩn 100% không timeout
File `split_df_a_dex.apk` rất nặng (83.8MB), khi push qua cổng USB Hub của giàn máy sẽ mất từ 2-4 phút/máy.
Cài đặt trực tiếp qua `install-multiple` bằng 1 lệnh dài dễ bị timeout (180s).

### Quy trình 4 bước chuẩn hóa:
1. **Push file vào bộ nhớ tạm thiết bị:**
   ```bash
   adb -s <serial> push "D:/OneDrive/apk-bank/com_ss_android_ugc_trill/v47.0.3/split_df_a_dex.apk" /data/local/tmp/split_df_a_dex.apk
   ```
2. **Khởi tạo incremental package install session:**
   ```bash
   sid=$(pm install-create -r -d -p com.ss.android.ugc.trill | cut -d"[" -f2 | cut -d"]" -f1)
   ```
3. **Nạp và commit session:**
   ```bash
   pm install-write -S 83814343 $sid split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk
   pm install-commit $sid
   rm -f /data/local/tmp/split_df_a_dex.apk
   ```
4. **Xác minh splits đầy đủ:**
   ```bash
   dumpsys package com.ss.android.ugc.trill | grep splits=
   # Kết quả hợp lệ BẮT BUỘC phải có df_a_dex:
   # splits=[base, config.arm64_v8a, config.vi, config.xxhdpi, df_a_dex]
   ```

## 3. Khóa cập nhật Google Play toàn dàn
Ngay sau khi đồng bộ, bắt buộc chạy lệnh:
```bash
adb -s <serial> shell "settings put global auto_update_apps 0"
```
để cố định phiên bản, ngăn Google Play Store tự động update ngầm làm lệch selector của bot.
