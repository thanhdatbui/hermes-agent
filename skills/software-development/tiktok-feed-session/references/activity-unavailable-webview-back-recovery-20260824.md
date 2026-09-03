# Activity Unavailable ("Hoạt động không có sẵn") Overlay & Webview Escape

## Bối cảnh và Dấu hiệu
Khi tài khoản TikTok đang chạy feed session gặp phải trang sự kiện/hoạt động hoặc popup cảnh báo:
- **Tiêu đề:** `Hoạt động không có sẵn` / `Activity not available`
- **Nội dung:** `Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này.` / `To continue participating in activities, switch to the original account you used on this device.`
- **Nút:** `OK` (hoặc `Đồng ý`) và mũi tên Back `←` trên thanh header.

Nếu không được phân loại, classifier sẽ rơi vào fallback `unknown TikTok state` và dừng phiên (`manual-needed`).

## Quy tắc xử lý: Bắt buộc dùng `press_back` (KEYCODE_BACK)
Tuyệt đối **KHÔNG** dùng action tap nút `OK`:
1. **Lý do kỹ thuật:** Bấm `OK` chỉ dismiss modal thông báo nhỏ bên trong một container Webview/trang sự kiện. Màn hình sau khi bấm `OK` vẫn bị giữ lại tại trang Webview sự kiện trống (có header bar chứa mũi tên `←`), khiến bot tiếp tục không nhận diện được Feed video và kẹt phiên.
2. **Action chuẩn:** Gửi tín hiệu `press_back` (`KEYCODE_BACK` / `input keyevent 4` hoặc `send_device_back_key(ctx)`). Lệnh `BACK` sẽ đóng toàn bộ Webview sự kiện và đưa ứng dụng quay về ngay màn hình Feed video (`Trang chủ` / `Đề xuất`).

## Cấu trúc Detector & Registry
1. **Core Detector (`core/benign_popup.py`):**
   - `detect_activity_unavailable_popup`: phát hiện cặp từ khóa tiêu đề + nội dung chuyển tài khoản ban đầu.
   - `_dismiss_action("activity_unavailable")` trả về `"press_back"`.
2. **Registry Handler (`flows/benign_popup_registry.py`):**
   - `_detect_activity_unavailable`: kiểm tra tiêu đề + nội dung trong XML / OCR.
   - `_dismiss_activity_unavailable`: gọi `send_device_back_key(ctx)`.
   - Đăng ký vào registry với priority cao (Priority 95).
