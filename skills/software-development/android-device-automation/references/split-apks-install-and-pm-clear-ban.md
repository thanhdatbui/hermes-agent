# TikTok App Bundle Split APKs Installation & Absolute Prohibition of `pm clear`

## 1. Split APKs (Android App Bundle) Architecture on S7 Farm
- TikTok v46+ phân phối dạng Split APKs gồm 50+ file (base + architecture + density + dynamic features).
- Cài thiếu split sẽ khiến app bị splash-stuck màn hình đen (`SplashActivity`) và crash vòng lặp CDN/Gecko.
- **Lệnh chuẩn hóa giữ nguyên 100% tài khoản đăng nhập:**
  ```bash
  adb -s <serial> install-multiple -r -d base.apk split_config.*.apk split_df_*.apk
  ```
- Sau khi cài: CHỈ dùng `am force-stop` + phím `HOME`.

## 2. CẤM TUYỆT ĐỐI `pm clear`
- `pm clear` xóa toàn bộ `/data/data/<package>`, làm văng sạch tài khoản đang nuôi trên farm về New User Journey.
- CẤM dùng `pm clear` để cứu app kẹt splash/lag.
- Khắc phục kẹt app an toàn: `am force-stop`, reboot máy, hoặc xóa thư mục cache (`rm -rf /data/data/<package>/cache/*`).

## 3. Kiến trúc nạp file lớn cho cụm máy phụ (Admin)
- Không bắn script đẩy hàng trăm MB qua ADB Remote LAN (`adb -H <remote_ip>:5037`) vì sẽ làm nghẽn socket và crash ADB server.
- Đưa file lên Shared OneDrive, thực thi script Python đa luồng (20 workers) cục bộ trên máy Admin để đẩy file trực tiếp qua cáp USB.
