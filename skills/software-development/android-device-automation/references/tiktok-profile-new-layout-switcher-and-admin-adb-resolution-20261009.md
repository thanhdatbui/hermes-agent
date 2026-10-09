# Android Device Automation: TikTok Account Switcher vs One-tap Login & Admin Remote ADB STT Resolution

## 1. Remote ADB Server Resolution cho cụm Admin (STT >= 201)
- Khi điều phối thiết bị cụm Admin (`192.168.110.119:5037`), script cần resolve serial từ file safe inventory (`taikhoan_run_safe.xlsx`) thay vì mảng hardcode `ACCOUNTS` của dàn Kibe (1..80).
- Biến môi trường bắt buộc:
  ```bash
  export ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"
  export TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"
  ```
- Cần fallback tự động trong hàm `resolve_device(stt)`:
  ```python
  from project_paths import TARGET_INVENTORY_WORKBOOK
  from scripts.target_inventory import load_machine_devices
  dev = load_machine_devices(TARGET_INVENTORY_WORKBOOK).get(stt)
  ```

---

## 2. Giao diện Profile TikTok mới (v46.x): Switcher vs One-tap Login
### Triệu chứng & Bẫy ngộ nhận
- Người vận hành thắc mắc: "Tại sao đăng nhập cả 2 acc rồi mà bấm vào tên không bung Account Switcher mà lại về màn Chào mừng bạn trở lại?"
- Bấm vào tên hiển thị ở góc trái Profile không mở Switcher mà mở widget "Thêm vị trí/sở thích".

### Bản chất kỹ thuật
1. **Thiếu nút Chevron ▼ trên Header**:
   - Layout mới đặt tên hiển thị ở góc trái (`bounds=[36, 256][397, 340]`), không có icon mũi tên dropdown bên cạnh.
   - Bấm trực tiếp vào tên khi chưa cuộn là vô tác dụng (text tĩnh hoặc mở subpage profile).
2. **Quy tắc bung Switcher chuẩn**:
   - Phải **cuộn nhẹ Profile lên** (swipe từ dưới lên khoảng 600px) để thanh tiêu đề dính cố định (`pmf` / `pmi`) xuất hiện trên cùng chính giữa màn hình header.
   - Bấm vào thanh tiêu đề dính cố định `pmf` trên header mới kích hoạt bung Account Switcher.
3. **Menu Cài đặt khi có 1 session active**:
   - Dưới đáy Cài đặt chỉ có nút duy nhất là "Đăng xuất", hoàn toàn không có mục "Chuyển đổi tài khoản".
4. **Màn hình One-tap Login ("Chào mừng bạn trở lại")**:
   - Là nơi TikTok lưu giữ danh sách session của các tài khoản đã đăng nhập trên máy.
   - Chạm vào bất kỳ tài khoản nào trong danh sách One-tap sẽ kích hoạt ngay tài khoản đó vào Profile trong 1 giây mà không cần OTP hay password.
   - Để thêm tài khoản mới khi máy ở trạng thái này: Bấm "Thêm tài khoản khác" trên màn hình One-tap -> Chọn "Dùng Email/Tên người dùng" để tiến hành đăng nhập/đăng ký.
