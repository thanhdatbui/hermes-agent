# Triển Khai & Đồng Bộ TikTok Split APKs (App Bundle / Android App Bundle)

## Hiện tượng / Triệu chứng
- Copy file APK TikTok từ máy mẫu sang máy khác, cài đặt báo thành công (`Success`) nhưng app mở lên:
  - Bị kẹt cứng màn hình đen ở `SplashActivity` (splash-stuck vô tận).
  - Văng / Crash liên tục hoặc cực kỳ giật lag.
  - Logcat báo lỗi dạng:
    - `disable gecko update and no file exists`
    - `fetchAsync error: 300 / 60300`
    - `cdnError: CDN Url Blank`
- Dễ bị chẩn đoán sai sang: lỗi mạng proxy, IPv6, lỗi máy treo, hoặc lỗi ATX agent.

## Bản chất kỹ thuật (Root Cause)
TikTok hiện đại trên Google Play Store là dạng **Android App Bundle (Split APKs)**:
- Không chỉ có 1 file `base.apk`.
- Đi kèm hàng chục file split APK phụ thuộc:
  - Cấu hình kiến trúc: `split_config.arm64_v8a.apk`
  - Mật độ hiển thị / Resource ảnh: `split_config.xxhdpi.apk` (nếu thiếu, S7 density 640 không load được asset UI).
  - Ngôn ngữ: `split_config.vi.apk`, `split_config.en.apk`.
  - Dynamic Feature Modules (DF): `split_df_player.apk` (bộ giải mã video), `split_df_camera.apk`, `split_df_im_bootfinish.apk`, `split_df_search_biz.apk`, v.v. (tổng cộng 30+ splits).
- Nếu chỉ dùng `adb install base.apk` hoặc copy thiếu các split feature, app sẽ thiếu thư viện native và resource layout dẫn đến kẹt splash đen hoặc crash ngay khi runtime gọi component tương ứng.

## Quy trình Kiểm Tra O(1)
Kiểm tra số lượng và danh sách split file đang có trên thiết bị:
```bash
adb -s <SERIAL> shell pm path com.ss.android.ugc.trill
```
- **Máy chuẩn (Kibe):** Trả về >30 dòng path APK (`base.apk` + đủ các `split_df_*.apk`).
- **Máy lỗi (thiếu split):** Chỉ trả về 1–3 dòng (`base.apk`, `split_config.arm64_v8a.apk`).

Kiểm tra trạng thái kẹt splash:
```bash
adb -s <SERIAL> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
# Nếu giữ mãi SplashActivity mà không chuyển sang MainActivity / Feed -> Kẹt splash do thiếu split/asset
```

## Quy trình Trích Xuất và Cài Đặt Chuẩn (Install-Multiple)

### Bước 1: Kéo toàn bộ split APK từ máy mẫu (Kibe)
```bash
# Tạo thư mục tạm
mkdir -p /tmp/tiktok_bundle
# Lấy đường dẫn thư mục cài đặt
APK_DIR=$(adb -s <SOURCE_SERIAL> shell "pm path com.ss.android.ugc.trill | head -n 1 | cut -d: -f2 | xargs dirname")
# Kéo toàn bộ file apk về
adb -s <SOURCE_SERIAL> pull "$APK_DIR" /tmp/tiktok_bundle/
```

### Bước 2: Cài đặt đồng bộ sang máy đích bằng `install-multiple`
CẤM cài đơn lẻ từng file. Phải dùng `install-multiple` để Android Package Manager link các split lại với nhau:
```bash
adb -s <TARGET_SERIAL> install-multiple -r -d base.apk split_1.apk split_2.apk ...
```
*Lưu ý quan trọng:*
- Luôn đặt `base.apk` ở đầu danh sách.
- Thêm cờ `-r` (reinstall / giữ data) và `-d` (allow version downgrade nếu có lệch build).
- Nếu cài qua mạng LAN (ví dụ sang cụm Admin qua `-H <IP>`), dung lượng bundle ~260MB có thể mất 3-5 phút nạp dữ liệu. Không kill tiến trình giữa chừng.

### Bước 3: Xử lý sau khi nạp đủ APK nếu vẫn kẹt SplashActivity
Khi đã nạp đủ 50+ file APK mà app vẫn kẹt ở màn hình đen `SplashActivity`:
- Do cache dữ liệu bị corrupt từ phiên bản thiếu split trước đó (data/data của app bị ghi đè cấu hình lỗi).
- Cần xóa cache hoặc chạy `adb -s <SERIAL> shell pm clear com.ss.android.ugc.trill` (lưu ý: `pm clear` sẽ xóa phiên login, chỉ dùng khi acc chưa login hoặc có thể login lại).

