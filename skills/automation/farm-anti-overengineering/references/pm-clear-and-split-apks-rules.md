# Bổ sung quy tắc Split APKs và Cấm `pm clear`

## Quy tắc bất biến (Non-negotiable)
1. **CẤM TUYỆT ĐỐI `pm clear`**:
   - `pm clear` xóa toàn bộ `/data/data` làm văng sạch tài khoản đăng nhập trên máy farm.
   - Để cứu app kẹt splash/lag: CHỈ dùng `am force-stop`, reboot máy, hoặc xóa cache (`rm -rf /data/data/<pkg>/cache/*`).
2. **Cài đặt đè bổ sung Split APKs (Android App Bundle)**:
   - Dùng `adb install-multiple -r -d base.apk split_config.*.apk split_df_*.apk`.
   - Giữ nguyên 100% token đăng nhập.
3. **Kiến trúc đẩy file lớn sang cụm Admin**:
   - Không bắn 20 luồng qua ADB Remote LAN (gây crash ADB server 5037).
   - Đưa file lên Shared OneDrive và chạy script Python đa luồng (20 workers) cục bộ trên máy Admin để đẩy qua cáp USB trực tiếp.
