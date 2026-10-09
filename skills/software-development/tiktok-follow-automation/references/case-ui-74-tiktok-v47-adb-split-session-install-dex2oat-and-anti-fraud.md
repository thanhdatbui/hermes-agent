# Case UI-74: TikTok v47.0.3 ADB Split Session Install Pipeline, dex2oat Optimization & Anti-Fraud Signature Preservation (2026-09-20)

## 1. Bối cảnh & Hiện trường sự cố
Khi tiến hành nâng cấp toàn bộ dàn máy Samsung Galaxy S7 (Android 8.0) lên phiên bản TikTok 47.0.3 nhằm thống nhất selector (`id/fmp`), phát sinh các vấn đề kỹ thuật nghiêm trọng:
1. **Thiếu Split Bytecode (`split_df_a_dex.apk`):** Nếu chỉ cài 4 file APK cơ bản (`base.apk`, `split_config.arm64_v8a.apk`, `split_config.vi.apk`, `split_config.xxhdpi.apk`), TikTok 47.0.3 sẽ crash ngay lập tức khi khởi động với ngoại lệ `ClassNotFoundException: Didn't find class "X.0gEx"` / `LooperProtectEnhanceSettingAppDiffProtocol` vì toàn bộ mã dex chính nằm trong file `split_df_a_dex.apk` (83.8 MB).
2. **Timeout và Nghẽn USB Bus:** Lệnh `adb install-multiple` trực tiếp với file nặng 83.8MB trên nhiều máy song song qua Hub USB 20 cổng bị nghẽn băng thông, tốc độ truyền giảm xuống ~0.3 MB/s dẫn đến timeout 180s-300s và đứt kết nối.
3. **Tiến trình `dex2oat` của Android 8:** Sau khi nạp APK, lệnh `pm install-commit` kích hoạt tiến trình biên dịch AOT `dex2oat` ngốn 100% CPU và 1GB+ RAM trên Samsung S7, kéo dài từ 40s–90s. Nếu kiểm tra trạng thái package ngay lập tức sẽ thấy thiếu split hoặc crash do chưa hoàn tất tối ưu hóa.

---

## 2. Quy trình nạp Split Dex Session chuẩn xác (Khắc phục triệt để)
Để nạp `split_df_a_dex.apk` mà không làm crash app, không mất nick và không timeout:

```bash
# 1. Push file APK vào bộ nhớ đệm thiết bị trước (tách rời bước truyền file khỏi session install)
adb -s <SERIAL> push "D:/Taadaa/apks/tiktok_47_0_3/split_df_a_dex.apk" /data/local/tmp/split_df_a_dex.apk

# 2. Tạo Session Install cho package com.ss.android.ugc.trill
sid=$(adb -s <SERIAL> shell "pm install-create -r -d -p com.ss.android.ugc.trill" | cut -d"[" -f2 | cut -d"]" -f1)

# 3. Stream write split từ file cục bộ trong /data/local/tmp
adb -s <SERIAL> shell "pm install-write -S 83814343 $sid split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk"

# 4. Commit session
adb -s <SERIAL> shell "pm install-commit $sid"

# 5. Chờ tiến trình dex2oat hoàn tất tối ưu hóa (polling kiểm tra 'ps -A | grep -i dex2oat')
# 6. Dọn dẹp file tạm và đưa máy về HOME
adb -s <SERIAL> shell "rm -f /data/local/tmp/split_df_a_dex.apk && input keyevent 3"
```

---

## 3. Thẩm định Kiến trúc Anti-Fraud & An toàn tài khoản (Sol Verdict)
* **Câu hỏi của Operator:** *Cài đặt TikTok bằng ADB `pm install` như vậy có khiến tài khoản bị TikTok quét die không?*
* **Phán quyết chính thức từ Sol (`chatgpt-web/gpt-5.6-sol-high`):**
  1. **Khớp Chữ Ký Số (Signature Hash 100%):** Do toàn bộ bộ file APK 47.0.3 được trích xuất trực tiếp từ máy S7 có Google Play Store chính chủ, chứng thư số `PackageSignatures{... [2606a464]}` hoàn toàn trùng khớp với chứng thư của ByteDance. TikTok Integrity Check coi đây là app nguyên bản, không bị mod/inject.
  2. **Installer Flag (`installerPackageName`):** Cài qua ADB khiến cờ này mang giá trị `null` thay vì `com.android.vending`. Tuy nhiên đây chỉ là một tín hiệu phụ (weak signal), hệ thống chống gian lận của TikTok chỉ phạt nặng khi phát hiện hành vi bot đồng loạt (Behavior Graph), clone device fingerprint hoặc modified dex.
  3. **Khóa chặt cập nhật tự động:** Bắt buộc chạy `settings put global auto_update_apps 0` trên toàn bộ dàn máy để tránh việc Play Store cập nhật ngầm không đồng đều giữa các máy trong farm.
