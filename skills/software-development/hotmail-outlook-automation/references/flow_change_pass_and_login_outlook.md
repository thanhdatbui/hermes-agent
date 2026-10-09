# Hotmail End-to-End Change Info & Outlook App Login Flow

## 1. Quy tắc bắt buộc: Khóa màn hình Portrait
- **TUYỆT ĐỐI CẤM XOAY NGANG MÀN HÌNH** trên thiết bị farm trong suốt quá trình chạy flow Hotmail / Outlook.
- Nếu màn hình bị xoay hoặc trước khi chạy flow, luôn enforce portrait qua ADB:
  ```bash
  adb -s <serial> shell "settings put system accelerometer_rotation 0 && settings put system user_rotation 0"
  ```

## 2. Canonical Orchestrator Script
File: `D:\Taadaa\Hotmail\scripts\flow_change_pass_and_login_outlook.py`

### Các bước script tự động thực hiện:
1. **Đổi mật khẩu Hotmail trên Chrome** (qua Proxy máy farm):
   - Sử dụng `flows.hotmail_security.task_change_password`.
2. **Kiểm tra & Gỡ email khôi phục không tin cậy của bên bán**:
   - Sử dụng `flows.hotmail_security.task_remove_untrusted_recovery_emails`.
   - Đã tích hợp sẵn nhận diện domain rác (như `@fviainboxes.com`, `getnada`, `mailnesia`, v.v.).
3. **Đăng xuất khỏi mọi thiết bị (Sign out everywhere)**:
   - Sử dụng `flows.hotmail_security.task_logout_devices`.
   - Đá văng toàn bộ phiên đăng nhập cũ của bên bán.
4. **Cập nhật PASS MỚI vào Excel**:
   - Ghi mật khẩu mới vào Cột G (Cột 7 - `PASS_MAIL`) của workbook `taikhoan_dat_v2_updated .xlsx` tại đúng target row.
5. **Mở App Outlook & Đăng nhập bằng pass mới**:
   - Sử dụng `flows.hotmail_login.login_outlook_app`.
   - Giữ phiên làm việc chính chủ, ổn định.

### Cú pháp gọi chuẩn:
```bash
python D:/Taadaa/Hotmail/scripts/flow_change_pass_and_login_outlook.py \
  --device <device_serial> \
  --machine <machine_number> \
  --row <excel_row> \
  --email <hotmail_address> \
  --current-password "<old_password>" \
  --new-password "<new_password>" \
  --workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
  --live
```

### Chụp ảnh nghiệm thu:
```bash
adb -s <device_serial> exec-out screencap -p > D:\Taadaa\m<machine_number>_hotmail_changed_done.png
```
