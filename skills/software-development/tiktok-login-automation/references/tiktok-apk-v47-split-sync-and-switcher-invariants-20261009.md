# TikTok APK v47.0.3 Sync & Split Module Invariants (2026-10-09)

## 1. Bối cảnh & Hiện tượng
- Farm Taadaa có 2 cụm: Cụm Kibe (Máy 1..80) và Cụm Admin (Máy 201..280).
- Phiên bản chuẩn toàn farm: **TikTok v47.0.3** (`versionCode=470003`, targetSdk=36).
- Kho Split APK chuẩn: `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\v47.0.3` (gồm **65 file split APK**).
- **CẤM cài thiếu split modules**: Bản v47.0.3 chia nhỏ thành 65 dynamic feature modules (`split_df_*`). Nếu chỉ cài 5 file cốt lõi (base + arm64 + vi + xxhdpi + a_dex), app cài thành công nhưng **CRASH NGAY LẬP TỨC** khi khởi động:
  ```
  java.lang.NoClassDefFoundError: Failed resolution of: Lcom/ss/android/ugc/aweme/settings/LooperProtectEnhanceSettingAppDiffProtocol;
  Caused by: java.lang.ClassNotFoundException: Didn't find class "com.ss.android.ugc.aweme.settings.LooperProtectEnhanceSettingAppDiffProtocol"
  ```
  hoặc crash `NoClassDefFoundError: Failed resolution of: LX/0fLw;`.

## 2. Quy trình cài đặt / cập nhật đồng bộ v47.0.3 an toàn (bảo toàn 100% login data)
Khi máy bị lỗi Account Switcher hoặc lệch phiên bản, quy trình đồng bộ chuẩn:
1. Đẩy toàn bộ 65 file APK split từ `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\v47.0.3` vào thư mục tạm trên máy:
   ```bash
   adb -s <serial> shell "mkdir -p /data/local/tmp/trill_v47"
   # Push tất cả 65 file .apk vào /data/local/tmp/trill_v47/
   ```
2. Thực hiện lệnh cài đặt đè bảo toàn phiên và dữ liệu:
   ```bash
   adb -s <serial> shell pm install -r -d /data/local/tmp/trill_v47/*.apk
   ```
3. Xác minh:
   - Output trả về `Success`.
   - `adb -s <serial> shell dumpsys package com.ss.android.ugc.trill | grep versionName` hiển thị đúng `versionName=47.0.3`.

## 3. Invariant mở Account Switcher trên layout TikTok mới
- **Kỳ vọng của User**: Tuyệt đối KHÔNG bắt user hoặc runner phải đăng xuất để chuyển tài khoản.
- **Quy trình chuẩn**:
  1. Vào tab Hồ sơ (`[864,1794][1080,1920]`).
  2. **Vuốt nhẹ trang Profile lên trên**: `adb shell input swipe 540 1200 540 600 300`.
  3. Thanh sticky header bar (`pmi` / `pmf`) sẽ dính cố định ở **chính giữa trên cùng** (`bounds=[385,72][696,228]`).
  4. Bấm vào nút chính giữa này (`adb shell input tap 540 150`), menu Account Switcher sẽ bung trượt từ đáy lên (`_wait_account_dropdown_open`).
