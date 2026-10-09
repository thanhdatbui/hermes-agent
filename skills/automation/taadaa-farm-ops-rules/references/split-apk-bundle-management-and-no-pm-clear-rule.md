# Quản lý Split APKs & CẤM TUYỆT ĐỐI `pm clear` trên Farm

## 1. Bản chất Split APKs (Android App Bundle) của TikTok
- TikTok hiện đại (v46+) trên Android không phải là một file APK đơn lẻ mà gồm `base.apk` và hàng chục split APKs (hơn 50 files: ABI `arm64_v8a`, density `xxhdpi`, dynamic features `split_df_*` như player, camera, search, fonts...).
- Nếu copy thiếu split APK (ví dụ chỉ lấy `base.apk` và 1-2 split cơ bản):
  + App sẽ không thể load layout, thiếu bộ giải mã video, tài nguyên đồ họa màn hình (density).
  + App sẽ bị kẹt vĩnh viễn ở `SplashActivity` (màn hình đen) và liên tục bắn lỗi ngầm `disable gecko update and no file exists`, `cdnError: CDN Url Blank`, gây giật lag và tràn RAM.
- **Cách cài đặt/nâng cấp chuẩn:**
  Phải dùng `adb install-multiple -r -d base.apk split_1.apk split_2.apk ...` trích xuất đầy đủ toàn bộ thư mục `/data/app/.../` từ máy chuẩn.

## 2. CẤM TUYỆT ĐỐI `pm clear` trên thiết bị Farm
- **Hậu quả thảm khốc:** `pm clear <package>` không phải là "xóa cache", mà nó **xóa sạch toàn bộ thư mục `/data/data/<package>`**, xóa sạch database token đăng nhập, làm văng 100% tài khoản trên thiết bị!
- **Quy tắc bất di bất dịch:**
  1. TUYỆT ĐỐI CẤM dùng `pm clear` để giải quyết app lag, crash, hoặc splash-stuck.
  2. Để cứu app kẹt splash hoặc lag, CHỈ ĐƯỢC dùng:
     - `am force-stop <package>`
     - Bấm phím Home (`input keyevent 3`)
     - Khởi động lại thiết bị (`adb reboot`)
     - Cài đè bổ sung split APK bằng `install-multiple -r -d` (cờ `-r` giữ nguyên data).

## 3. Quản lý tải mạng LAN vs Chạy cục bộ qua USB khi cài đặt hàng loạt
- Khi nâng cấp đồng loạt hàng chục thiết bị (70-80 máy) với bộ Split APK nặng (>250 MB):
  + CẤM chạy nhiều worker từ máy Kibe bắn qua cổng Remote ADB của máy Admin (`-H <admin_ip>:5037`). Băng thông mạng LAN và socket của ADB server sẽ bị nghẽn (`adb: failed to write: ...`), gây rớt kết nối diện rộng.
  + **Quy tắc:** Đẩy bộ APK lên thư mục dùng chung (OneDrive `Taadaa_Sync_Shared`), sau đó kích hoạt script chạy cục bộ trực tiếp trên máy Admin. Tốc độ USB trực tiếp cho phép chạy 20-40 worker song song mà không tốn 1 byte băng thông mạng LAN.
