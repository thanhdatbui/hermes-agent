# TikTok Split APK & Khắc phục Splash-Stuck Giữ Login

## 1. Triệu chứng Crash & Splash-Stuck do thiếu Split APKs
- TikTok v46+ phân rã dạng Android App Bundle (AAB).
- Nếu trích xuất thiếu split APK (ví dụ chỉ có `base.apk` và 2 split cơ bản):
  + Máy thiếu `split_config.xxhdpi` (tài nguyên đồ họa S7), `split_df_player` (bộ giải mã video).
  + Khi khởi động, app kẹt vô tận ở màn hình đen `SplashActivity`, các luồng ngầm liên tục bắn lỗi Gecko CDN fail, gây giật lag và tràn RAM.

## 2. Quy trình Bổ sung APK Giữ Nguyên Đăng Nhập
- **CẤM TUYỆT ĐỐI `pm clear`**: `pm clear` xóa sạch `/data/data` làm văng hết tài khoản.
- Lệnh chuẩn hóa:
  ```bash
  adb install-multiple -r -d base.apk [54 file split APKs...]
  adb shell am force-stop com.ss.android.ugc.trill
  adb shell input keyevent 3
  ```
  Cờ `-r` đảm bảo giữ nguyên 100% dữ liệu đăng nhập.

## 3. Chạy hàng loạt trên cụm máy Remote (Admin)
- Không đẩy đồng thời nhiều luồng qua Remote ADB LAN (`-H IP:5037`) vì socket ADB sẽ nghẽn và ngắt kết nối.
- Đồng bộ bộ APK lên OneDrive chia sẻ (`D:\OneDrive\Taadaa_Sync_Shared\tools\tiktok_full_apks_v46.6.3`).
- Kích hoạt script đa luồng (20 workers) chạy trực tiếp trên máy Admin qua USB nội bộ.
