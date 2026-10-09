# Bằng Chứng Hiện Trường Thật (Foreground Evidence) vs Cấm Gửi Ảnh Home / Screencap Màn Hình Đen (2026-09-19)

## 1. Bối cảnh & Phản hồi thực tế từ User
- **Phản hồi gắt từ User**: *"Gì tối đen v? Còn bên máy reg chatgpt sao k bấm chấp nhận cookies đi... Mấy máy khác gửi màn hình home làm đéo gì v t cài rule gửi ảnh hiện trường r mà"*
- **Vấn đề 1 (Ảnh tối đen / Black Screencap)**:
  - Khi thiết bị Samsung S7 ở trạng thái màn hình tắt (`Display Power: state=OFF` hoặc Dozing/Sleep), lệnh `adb exec-out screencap -p` sẽ trả về luồng framebuffer toàn màu đen (`0, 0, 0`).
  - **Quy tắc bắt buộc**: Trước khi chụp screencap trên Android, BẮT BUỘC gửi lệnh đánh thức: `adb shell input keyevent 224` (WAKEUP) và chụp trực tiếp qua file nội bộ: `adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png ...`. CẤM TUYỆT ĐỐI gửi ảnh đen kịt cho User.
- **Vấn đề 2 (Chụp màn hình Home thay vì hiện trường thao tác)**:
  - Các script/subagent thường có logic cleanup khi kết thúc hoặc gặp lỗi: tự động gửi `input keyevent 3` (HOME) hoặc `force-stop`.
  - Nếu chụp ảnh sau khi cleanup, ảnh chỉ ghi lại màn hình Launcher/Home vô nghĩa, vi phạm nghiêm trọng GATE 6 (MEDIA EVIDENCE GATE).
  - **Quy tắc bắt buộc**: BẮT BUỘC chụp ảnh hiện trường (Screenshot/Screencap) **NGAY TẠI THỜI ĐIỂM XẢY RA HÀNH ĐỘNG / LỖI / STEP TRONG FOREGROUND APP**, trước khi thực hiện bất kỳ lệnh `keyevent 3` hay thoát app nào.

## 2. Kỹ thuật WebView Mù DOM & Cookie Popup trên Chrome Android
- **Hiện tượng**:
  - Chrome trên Android render trang web (đặc biệt là `chatgpt.com`, các trang SPA) dưới dạng WebView nguyên khối (`content-desc="Lượt xem trên web"`).
  - `uiautomator dump` không bóc tách được các thẻ text DOM bên trong web (`find_node_in_xml` không thấy text *"Chấp nhận tất cả"* hay *"Cookie"*).
  - Hệ quả: Script bị kẹt timeout vĩnh viễn ở banner Cookie.
- **Giải pháp chuẩn hóa**:
  - Khi phát hiện đang ở Chrome/WebView mà XML không có node text DOM, BẮT BUỘC có cơ chế **Fallback Tap theo tọa độ chuẩn màn hình S7 (1080x1920)**:
    - Nút `[Chấp nhận tất cả]` của Cookie popup: `X=540, Y=1780`.
    - Ô input `[Email / Text]`: `X=540, Y=1315` hoặc `X=540, Y=1150`.
    - Nút `[Tiếp tục / Submit]`: `X=540, Y=1500` hoặc `X=540, Y=1485`.

## 3. Popup "Phê duyệt trình xác thực này" của Google Authenticator
- **Hiện tượng**:
  - Sau khi kích hoạt Google Authenticator thành công (điền xong mã 6 số), Google web hiện popup: *"Phê duyệt trình xác thực này? ... Để đẩy nhanh quá trình này, bạn có thể phê duyệt trình xác thực mới... [Xóa] [Phê duyệt]"*.
  - Thông báo này chỉ xuất hiện **1 lần duy nhất ngay sau khi thêm**. Nếu đóng tab hoặc bỏ qua thì sẽ không bao giờ hiện lại.
- **Quy tắc xử lý**:
  - Trong luồng Add 2FA, ngay sau bước click `verify_btn`, BẮT BUỘC có bước `8b` tự động tìm và click ngay nút `[Phê duyệt]` (`button:has-text("Phê duyệt"), button:has-text("Approve")`) để kích hoạt sử dụng ngay lập tức.
