# Quy Tắc Xử Lý Nhả Follow Tự Động Về Home & Khóa Xoay Màn Hình Qua Content Provider (19/08)

## 1. Xử Lý Nhả Follow (Follow Released / Cooldown Isolated):
- **Phát hiện**: Sau khi tap Follow và thực hiện Pull-to-refresh kéo từ trên xuống (chờ $\ge 3.5$s), nút trạng thái chuyển ngược lại thành "Follow" đỏ hoặc TikTok không ghi nhận follow.
- **Hành động xử lý (User chốt 19/08)**:
  1. Ghi nhận `follow_failed = True` và `follow_failed_date = YYYY-MM-DD` cô lập theo **RIÊNG nick / row tài khoản** (`follow_state_<machine>_row_<row>.json`). Các nick khác trên cùng máy vẫn chạy follow bình thường.
  2. **Dọn dẹp hiện trường an toàn**: Ngay lập tức gọi `self.adapter.close_all_apps()` để:
     - Đóng hoàn toàn ứng dụng TikTok.
     - Xóa sạch danh sách ứng dụng gần đây (Clear Recent Apps).
     - Đưa máy về màn hình chính (Home) sạch sẽ, tuyệt đối không để ứng dụng treo ở màn hình follow.

## 2. Cơ Chế Khóa Xoay Màn Hình Kép (Dual-layer Rotation Lock - Samsung OneUI/TouchWiz):
- **Hiện tượng**: Mặc dù script đã chạy `settings put system accelerometer_rotation 0`, nhưng khi máy mở video TikTok định dạng ngang hoặc rung lắc cảm biến, Samsung OneUI tự ý ghi đè ngược lại giá trị `1` (Tự động xoay) vào hệ thống khiến máy bị xoay ngang màn hình.
- **Giải pháp triệt để**:
  - Bắt buộc thực hiện ghi đè kép qua **Android Content Provider** ở mọi hàm chuẩn bị máy (`device_prepare.py` và `startup.py`):
    ```bash
    settings put system accelerometer_rotation 0
    settings put system user_rotation 0
    content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
    content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
    ```
  - Lệnh này khóa trực tiếp vào tầng cơ sở dữ liệu `settings.db` của Samsung, ngăn chặn hoàn toàn OneUI tự ý bật lại chế độ tự xoay.

## 3. Khởi Động An Toàn Khi Danh Sách Recents Rỗng (`close_all_recent_apps`):
- Khi máy vừa mở khóa hoặc đã sạch hoàn toàn ứng dụng ngầm, màn hình Recent Apps không có nút "Đóng tất cả".
- Hàm `prepare_android_for_automation` và `prepare_app_for_automation` phải bỏ qua lỗi `clear_all button and empty-recents evidence not found`, gửi phím `Home` để đảm bảo về màn hình chính và tiếp tục mở TikTok chạy bình thường, không được ngắt phiên hay báo lỗi giả.
