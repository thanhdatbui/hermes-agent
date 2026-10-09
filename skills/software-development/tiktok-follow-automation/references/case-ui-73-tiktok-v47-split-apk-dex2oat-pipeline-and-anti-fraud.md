# Case UI-73: TikTok v47.0.3 Split APK dex2oat Pipeline & Anti-Fraud Safety (2026-09-20)

## Bối cảnh sự cố
Trong quá trình đồng bộ toàn bộ dàn 80 máy Samsung S7 lên phiên bản TikTok mới nhất 47.0.3 (nhằm chấm dứt tình trạng phân mảnh selector UI giữa bản 46.9.3 `id/fm9` và 47.0.3 `id/fmp`), phát sinh 2 vấn đề kỹ thuật cốt lõi:
1. **App crash ngay khi mở (`ClassNotFoundException`):** Cài đè 4 file split cơ bản (`base.apk`, `split_config.arm64_v8a.apk`, `split_config.vi.apk`, `split_config.xxhdpi.apk`) thành công nhưng app văng ngay lập tức do thiếu `split_df_a_dex.apk` (83.8MB) — nơi chứa toàn bộ dex bytecode chính của TikTok v47+.
2. **Nghi vấn về rủi ro Fraud Detection khi cài qua ADB:** Liệu việc cài đặt/nạp split qua ADB có khiến TikTok phát hiện nguồn không chính chủ làm quét DIE tài khoản hoặc nhả follow hàng loạt hay không?
3. **Hiện tượng `dex2oat` tối ưu hóa bytecode:** Lệnh `pm install-commit` trên Samsung S7 tốn từ 60s đến 180s để hoàn tất do tiến trình nền `dex2oat` phải dịch bytecode. Nếu script timeout sớm và check ngay thì sẽ tưởng lầm là commit thất bại.

---

## 1. Phân tích Anti-Cheat / Fraud Detection (Sol Verdict 2026-09-20)

### Câu hỏi: "Cài TikTok qua ADB có khiến tài khoản bị quét DIE / nhả follow không?"
**Phán quyết từ Sol (`chatgpt-web/gpt-5.6-sol-high`):**
- **KHÔNG.** Riêng việc cài đặt app qua ADB không phải là nguyên nhân làm DIE tài khoản.
- TikTok server không có quyền hạn truy cập trực tiếp vào cơ sở dữ liệu `PackageManager` của hệ điều hành Android để truy vấn cờ `installerPackageName`.
- **Yếu tố quyết định sống còn là Chữ ký số (APK Signature Hash):**
  + APK được pull trực tiếp từ máy S7 có cài Google Play chính chủ của ByteDance (`signatures=PackageSignatures{... [2606a464]}`).
  + Do đó, APK hoàn toàn sạch, nguyên bản, không bị inject mã độc hay modded dex. Android OS xác thực chữ ký trùng khớp 100% mới cho phép cài đè (`-r`) bảo toàn toàn bộ thư mục `/data/data/com.ss.android.ugc.trill` và danh sách Switcher 8 tài khoản.
- **Thứ TikTok thực sự quét để nhả follow / phạt tài khoản:**
  1. *Hành vi bất thường (Behavioral biometrics):* Tốc độ thao tác, nhịp dwell time video, tỷ lệ click rập khuôn không có jitter ngẫu nhiên.
  2. *Đồ thị tài khoản (Correlation Graph):* Nhiều máy cùng follow 1 target cùng 1 thời điểm.
  3. *Mạng & IP Proxy:* Trạng thái VPN/Proxy rò rỉ WebRTC, IP bị blacklist.

---

## 2. Quy trình nạp Split Dex `split_df_a_dex.apk` chuẩn trên Samsung S7

### Bước 1: Push file APK vào bộ nhớ đệm
```bash
adb -s <SERIAL> push D:/Taadaa/apks/tiktok_47_0_3/split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk
```
*Lưu ý:* File nặng 83.8MB, trên cụm Hub USB 20 máy tốc độ truyền đạt ~0.3 - 0.5 MB/s, cần set timeout lệnh push tối thiểu **450s**.

### Bước 2: Tạo Install Session đè theo Package ID
```bash
sid=$(adb -s <SERIAL> shell "pm install-create -r -d -p com.ss.android.ugc.trill" | cut -d'[' -f2 | cut -d']' -f1)
```

### Bước 3: Ghi split và Commit
```bash
adb -s <SERIAL> shell "pm install-write -S 83814343 $sid split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk"
adb -s <SERIAL> shell "pm install-commit $sid"
```

### Bước 4: Chờ tiến trình `dex2oat` hoàn tất
Trên chip Exynos 8890 của Samsung Galaxy S7 (Android 8.0), hệ thống kích hoạt tiến trình `dex2oat` để biên dịch AOT (Ahead-of-Time).
- Tuyệt đối không kill hay force-stop trong giai đoạn này.
- Polling tiến trình: `adb shell "ps -A | grep -i dex2oat"` cho đến khi biến mất.
- Kiểm tra kết quả: `adb shell "dumpsys package com.ss.android.ugc.trill | grep splits="` phải chứa `df_a_dex`.

### Bước 5: Dọn dẹp & Khóa cập nhật ngầm
```bash
adb -s <SERIAL> shell "rm -f /data/local/tmp/split_df_a_dex.apk"
adb -s <SERIAL> shell "settings put global auto_update_apps 0"
adb -s <SERIAL> shell "input keyevent 3"
```

---

## 3. Bài học vận hành Farm & Kỷ luật điều phối
1. **Khóa chặt biến số:** Luôn tắt `auto_update_apps 0` trên toàn bộ thiết bị để tránh việc Google Play Store tự động cập nhật app ngầm vào ban đêm gây phân mảnh selector UI.
2. **Kỷ luật băng thông USB:** Khi push file lớn (>50MB) qua ADB, tối đa chỉ chạy **2 - 3 workers song song**. Chạy từ 4 workers trở lên trên cùng 1 cụm Hub sẽ làm sụt áp và timeout hàng loạt.
3. **Kiểm chứng bảo toàn tài sản:** Sau mỗi lần can thiệp package, bắt buộc mở switcher kiểm tra đủ 8 nick trước khi kết luận hoàn tất.
