# Pitfall: Bàn phím ảo gõ thêm ký tự 'g' và Gmail kẹt màn hình Search

## 1. Bẫy chạm nhầm phím 'g' trên bàn phím ảo Samsung S7 (Android 8)
- **Hiện tượng**: Sau khi gõ email vào WebView Chrome (OpenAI/ChatGPT signup), kịch bản gọi lệnh `tap(device_id, 540, 1504)` với dự tính bấm nút "Tiếp tục" / "Continue". Tuy nhiên, bàn phím ảo Samsung vẫn đang mở và che nửa dưới màn hình.
- **Hậu quả**: Tọa độ `(540, 1504)` nằm chính giữa hàng phím thứ 2 (phím **'g'**) trên bàn phím ảo Samsung. Kết quả email bị gõ thêm ký tự `g` ở đuôi (ví dụ: `user@gmail.comg`), gây lỗi "Email không hợp lệ" hoặc submit sai email.
- **Giải pháp chuẩn**:
  - Không tap tọa độ cứng trong vùng `y > 1400` khi bàn phím ảo đang active.
  - Sử dụng phím `Enter` (`input keyevent 66`) để trigger submit form trực tiếp từ bàn phím.
  - Nếu cần tap nút bấm trong DOM, chỉ tap sau khi đã đóng bàn phím hoặc khi tọa độ nút được xác định rõ ràng trên màn hình (ngoài vùng phủ của bàn phím).

## 2. Bẫy Gmail kẹt ở chế độ Tìm kiếm (Search Mode)
- **Hiện tượng**: Khi chuyển sang app Gmail (`com.google.android.gm`) để lấy mã OTP, ứng dụng có thể đang mở sẵn ở chế độ tìm kiếm thư (`SearchView`).
- **Dấu hiệu nhận biết trong UI XML**:
  - Chứa node hoặc text: `"Quay lại"`, `"Tìm kiếm trong thư"`, `"Bắt đầu tìm kiếm bằng giọng nói"`, `"Tệp đính kèm"`.
- **Hậu quả**: Danh sách email thông thường không hiển thị, swipe refresh không cập nhật inbox chính, dẫn đến timeout tìm mã OTP (90s).
- **Giải pháp chuẩn**:
  - Kiểm tra trước vòng lặp đọc thư hoặc trong từng nhịp polling:
    ```python
    if "Quay lại" in xml and any(k in xml for k in ["Tìm kiếm trong thư", "Bắt đầu tìm kiếm bằng giọng nói", "Tệp đính kèm"]):
        logger.info(f"[{device_id}] Gmail đang ở màn hình tìm kiếm, tap Quay lại để về Inbox...")
        tap(device_id, 72, 168, wait=1.5)
        xml = get_ui_xml(device_id) or ""
    ```
  - Tọa độ nút Quay lại (Back icon) ở góc trên bên trái thanh tìm kiếm Gmail trên màn hình 1080x1920: `(72, 168)`.
