# Android App Bundle (Split APKs) Standardization & Absolute Prohibition of `pm clear`

## 1. Bản chất sự cố Split APKs (Android App Bundle - AAB)
- Các phiên bản TikTok hiện đại từ CH Play (v46.x+) không còn là 1 file APK đơn lẻ (Monolithic APK) mà là tập hợp **Split APKs (50+ files)** gồm:
  - `base.apk`: Mã nguồn core ứng dụng.
  - `split_config.<arch>.apk` (ví dụ: `arm64_v8a`): Native binaries (.so).
  - `split_config.<density>.apk` (ví dụ: `xxhdpi`): Tài nguyên đồ họa màn hình S7 (density 640/480).
  - Các split tính năng: `split_df_player.apk` (trình phát video), `split_df_camera.apk`, `split_df_im_bootfinish.apk`...
- **Hiện tượng lỗi khi cài thiếu:**
  - Nếu chỉ kéo hoặc cài `base.apk` và 1-2 split cơ bản, app sẽ bị kẹt vĩnh viễn ở màn hình đen `SplashActivity` (`com.ss.android.ugc.aweme.splash.SplashActivity`), không thể khởi tạo layout hay player.
  - Tiến trình ngầm cố nạp tài nguyên Gecko/Resource CDN bị fail liên tục (`disable gecko update and no file exists`, `cdnError: CDN Url Blank`), dẫn đến tràn RAM, đơ máy và crash.

## 2. Lệnh nâng cấp và bổ sung Split APKs chuẩn (Giữ nguyên 100% Login)
- Để nâng cấp hoặc bù đắp split APKs thiếu mà **giữ nguyên 100% tài khoản đăng nhập**:
  ```bash
  adb -s <serial> install-multiple -r -d base.apk split_config.*.apk split_df_*.apk
  ```
  - Cờ `-r` (reinstall / replace existing): Giữ nguyên toàn bộ thư mục `/data/data` chứa token và phiên đăng nhập.
  - Cờ `-d` (allow downgrade): Cho phép hạ/sắp xếp lại version code nếu cần.
- Sau khi cài xong: CHỈ dùng `am force-stop` và gửi phím `HOME`:
  ```bash
  adb -s <serial> shell "am force-stop com.ss.android.ugc.trill && input keyevent 3"
  ```

## 3. CẤM TUYỆT ĐỐI `pm clear` trên thiết bị Farm
- **Quy tắc bất biến:** `pm clear <package>` là lệnh xóa sạch thư mục `/data/data/<package>` (toàn bộ cookies, tokens, SQLite databases, shared preferences).
- Hậu quả: Làm **văng toàn bộ tài khoản TikTok đang nuôi** trên máy về màn hình New User Journey, gây thiệt hại nghiêm trọng cho farm.
- Khi app bị kẹt splash, đơ hoặc lag:
  - CHỈ ĐƯỢC PHÉP: `am force-stop`, reboot máy, hoặc dùng cơ chế dọn cache an toàn (`rm -rf /data/data/<package>/cache/*`).
  - TUYỆT ĐỐI CẤM dùng `pm clear` làm bước phục hồi hay cứu app.

## 4. Kiến trúc phân tán Farm: USB trực tiếp vs Remote ADB qua mạng LAN
- Khi cần cài đặt/nâng cấp đồng loạt file nặng (như bộ 55 Split APKs nặng ~263 MB) cho cụm máy từ xa (ví dụ Admin 200+):
  - **CẤM** dùng script từ máy Kibe bắn qua ADB Remote LAN (`adb -H <admin_ip>:5037`) vì 20 luồng kéo 263 MB sẽ làm nghẽn socket và crash ADB server trên máy Admin (`adb: failed to write`).
  - **CHUẨN:** Đồng bộ bộ file APK lên thư mục chung OneDrive (`Taadaa_Sync_Shared/tools/`), sau đó thực thi script cục bộ ngay trên máy Admin bằng Python đa luồng (`ThreadPoolExecutor(max_workers=20)`). Dữ liệu được đẩy thẳng từ ổ cứng cục bộ qua cáp USB trực tiếp, đạt tốc độ tối đa và ổn định 100%.
