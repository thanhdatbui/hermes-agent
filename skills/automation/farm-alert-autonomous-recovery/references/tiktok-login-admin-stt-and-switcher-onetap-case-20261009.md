# Bổ sung Case 09/10/2026: Triage TikTok Login STT >= 201 trên cụm Admin, Cơ chế Switcher vs One-tap Login

## 1. Lỗi Resolve Device trên cụm Admin (`tiktok_login_v1.py`)
- **Triệu chứng**: Chạy `tiktok_login_v1.py 266 --email letam2502` văng lỗi:
  ```text
  STOPPED: Khong co STT 266 trong ACCOUNTS
  ```
- **Nguyên nhân**: Mảng cứng `ACCOUNTS` chỉ chứa máy Kibe (1..80), không có máy Admin (201..280).
- **Cách fix chuẩn O(1)**: Trong `resolve_device(stt)`, bổ sung fallback:
  ```python
  acc = next((item for item in ACCOUNTS if item["stt"] == stt), None)
  if acc and acc.get("device"):
      return acc["device"]
  from project_paths import TARGET_INVENTORY_WORKBOOK
  from scripts.target_inventory import load_machine_devices
  dev = load_machine_devices(TARGET_INVENTORY_WORKBOOK).get(stt)
  if dev:
      return dev
  raise RuntimeError(f"Khong co STT {stt} trong ACCOUNTS")
  ```
- **Môi trường bắt buộc khi chạy trên máy Admin**:
  - `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"`
  - `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"`

## 2. Cơ chế Account Switcher vs One-tap Login ("Chào mừng bạn trở lại")
- **Thắc mắc**: Đã đăng nhập cả 2 acc nhưng bấm vào tên trên Profile không bung Account Switcher mà lại về màn Chào mừng bạn trở lại.
- **Thực tế giao diện**:
  1. Trên TikTok bản v46.x (Android 8), tên hiển thị nằm ở góc trái (`bounds=[36, 256][397, 340]`), không có nút mũi tên ▼ dropdown. Bấm vào tâm tên chỉ là text tĩnh hoặc mở widget sửa vị trí.
  2. Muốn mở Account Switcher ở layout này: **Bắt buộc phải cuộn nhẹ Profile lên** để thanh tiêu đề dính cố định (`pmf` / `pmi`) xuất hiện trên cùng chính giữa header, sau đó bấm vào thanh này mới bung menu Switcher từ đáy lên.
  3. Khi chỉ có 1 session active độc lập, ở đáy Settings không có mục "Chuyển đổi tài khoản" mà chỉ có "Đăng xuất".
  4. Các tài khoản phụ được lưu giữ session an toàn trong màn hình One-tap Login ("Chào mừng bạn trở lại"). Chạm vào tài khoản nào là chuyển active ngay lập tức mà không cần OTP/password.
