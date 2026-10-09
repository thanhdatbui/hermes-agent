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
  - Dynamic Feature Modules (DF): `split_df_player.apk` (bộ giải mã video), `split_df_camera.apk`, `split_df_im_bootfinish.apk`, `split_df_search_biz.apk`, v.v. (tổng cộng 50+ splits trên v46.6.3).
- Nếu chỉ dùng `adb install base.apk` hoặc copy thiếu các split feature, app sẽ thiếu thư viện native và resource layout dẫn đến kẹt splash đen hoặc crash ngay khi runtime gọi component tương ứng.

## 🛑 NGUYÊN TẮC BẢO VỆ DỮ LIỆU: CẤM TUYỆT ĐỐI `pm clear`
- **CẤM TUYỆT ĐỐI dùng `pm clear` trên thiết bị farm** để giải quyết kẹt app hoặc sau khi cài đặt APK.
- `pm clear` xóa sạch toàn bộ thư mục `/data/data/com.ss.android.ugc.trill`, làm văng toàn bộ phiên đăng nhập của các tài khoản trên máy.
- **Để nâng cấp và giữ nguyên 100% login:** BẮT BUỘC dùng cờ `-r` (reinstall, keep data) và `-d` (allow version downgrade/re-alignment):
  ```bash
  adb -s <SERIAL> install-multiple -r -d base.apk [tất cả split APKs...]
  ```
- Sau khi cài xong: chỉ gọi `am force-stop` và gửi phím `HOME` (`input keyevent 3`). Tuyệt đối không xóa data.

## Quy trình Kiểm Tra O(1)
Kiểm tra số lượng và danh sách split file đang có trên thiết bị:
```bash
adb -s <SERIAL> shell pm path com.ss.android.ugc.trill
```
- **Máy chuẩn (Kibe v46.6.3):** Trả về 55 dòng path APK (`base.apk` + 54 `split_*.apk`).
- **Máy lỗi (thiếu split):** Chỉ trả về 1–3 dòng (`base.apk`, `split_config.arm64_v8a.apk`).

Kiểm tra trạng thái kẹt splash:
```bash
adb -s <SERIAL> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
# Nếu giữ mãi SplashActivity mà không chuyển sang MainActivity / Feed -> Kẹt splash do thiếu split/asset
```

## Quy trình Trích Xuất và Cài Đặt Chuẩn (Install-Multiple Giữ Login)

### Bước 1: Kéo toàn bộ split APK từ máy mẫu (Kibe)
```bash
# Lấy danh sách path và pull toàn bộ APK (khoảng 55 file ~263MB)
adb -s <SOURCE_SERIAL> shell "pm path com.ss.android.ugc.trill"
```

### Bước 2: Nâng cấp đồng bộ đa luồng giữ nguyên tài khoản
- Chạy cục bộ trực tiếp trên host quản lý thiết bị (qua USB), tránh đẩy 20 luồng đồng thời qua mạng LAN Remote ADB vì sẽ làm tràn socket buffer ADB server.
- Sử dụng `install-multiple -r -d`:
```python
cmd = ["adb", "-s", serial, "install-multiple", "-r", "-d", base_apk] + split_apks
subprocess.run(cmd)
# Sau khi cài thành công, chỉ force-stop và về Home
subprocess.run(["adb", "-s", serial, "shell", "am", "force-stop", "com.ss.android.ugc.trill"])
subprocess.run(["adb", "-s", serial, "shell", "input", "keyevent", "3"])
```
