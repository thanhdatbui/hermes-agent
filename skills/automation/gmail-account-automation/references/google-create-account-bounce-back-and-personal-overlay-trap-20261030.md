# Bẫy Bounce-back Ảo Popup Cá Nhân [05_personal] do ATX XML Nuốt Node Overlay

## 1. Hiện Tượng Thực Tế (Phát Hiện 30/10/2026 trên Cụm Admin)
- Khi chạy đăng ký Gmail trên Samsung Galaxy S7 (Android 7/8), tại màn hình Google Sign-in:
  - Nút **"Tạo tài khoản" (Create account)** nằm ở góc dưới bên trái (Bounds: `X=[73, 329], Y=[1446, 1486]`, Center: `(201, 1466)`).
  - Cây UI XML trích xuất qua `atx-agent` (port 7912) hoặc `uiautomator dump` bị thiếu/nuốt mất node này trong WebView.
  - Sau khi script tap tọa độ calibrated `(201, 1466)`, Google bật popup menu overlay gồm 2 tùy chọn:
    1. *"Dành cho mục đích cá nhân của tôi"* (For my personal use)
    2. *"Để quản lý doanh nghiệp của tôi"* (To manage my business)
- **Tử huyệt logic script:**
  - Hàm `_poll_personal` trong `gmail_reg_v10.py` liên tục gọi `get_ui_xml(device_id)`.
  - Do popup là một overlay trôi nổi (floating popup) đè lên form đăng nhập phía dưới, cây Accessibility XML của Android vẫn lưu giữ node trường nhập email `identifierId`.
  - Mặt khác, text tiếng Việt *"Dành cho mục đích cá nhân"* trên popup không được WebView phản ánh kịp vào cây XML hoặc bị lỗi render node.
  - Script kiểm tra điều kiện:
    ```python
    if "identifierId" in _xml:
        if _bounce_since is None:
            _bounce_since = time.time()
        elif time.time() - _bounce_since >= 4.0:
            return "bounce", _xml
    ```
  - Kết quả: Sau 4 giây, script tưởng nhầm là màn hình bị "bật ngược (bounce-back)" về lại trang đăng nhập, tự động raise `RuntimeError("GOOGLE_CREATE_ACCOUNT_BOUNCE_BACK")` làm hủy đồng loạt 15/15 máy đang chạy!

## 2. Bản Chất Kỹ Thuật (Root Cause)
1. **Lệch pha giữa Framebuffer (Thực tế) và Accessibility Service (ATX XML):**
   - Mắt thật (Vision / WinRT OCR) đọc được 100% dòng chữ *"Tạo tài khoản"* và popup menu cá nhân trên ảnh chụp màn hình (`screencap`).
   - Cây XML của `uiautomator` trên Android 7 bị đóng băng ở tầng WebView cha, không bóc tách được các phần tử động của popup HTML5/WebView.
2. **Quy chụp sai lầm `identifierId == bounce`:**
   - Sự hiện diện của `identifierId` không đồng nghĩa với việc popup chưa mở hay đã đóng, vì WebView vẫn giữ nguyên DOM nền bên dưới overlay.
   - Grace period 4.0s quá ngắn so với độ trễ phản hồi của chip Exynos 8890 trên Samsung S7.

## 3. Quy Tắc & Giải Pháp Bắt Buộc (Mandatory Rules)
- **Triệt tiêu cào XML mù:**
  - CẤM TUYỆT ĐỐI chỉ dựa vào `find_node_in_xml` để kết luận popup đã đóng hoặc chưa hiện trên WebView Google Sign-in.
  - BẮT BUỘC dùng **WinRT OCR screencap (`automation_core.ui_extract.extract_ui`)** để tìm chuỗi `"cá nhân"` / `"personal"` trực tiếp từ ảnh chụp thực tế.
- **Calibrated Tap Fallback cho Menu Cá Nhân:**
  - Nếu sau 1.5s - 2.0s kể từ khi tap *"Tạo tài khoản"* mà XML không có node text nhưng màn hình vẫn ở sign-in flow, cho phép tap trực tiếp tọa độ menu cá nhân chuẩn trên màn hình 1080x1920:
    ```python
    # Menu item 'Dành cho mục đích cá nhân của tôi' luôn hiển thị ngay phía trên nút Tạo tài khoản
    tap(device_id, 350, 1180, wait=D_MEDIUM)
    ```
- **Loại bỏ phán đoán `bounce-back` tức thời:**
  - Nâng timeout hoặc chỉ xác nhận bounce-back khi WinRT OCR khẳng định 100% không có menu cá nhân và màn hình đã quay lại trạng thái focus vào ô nhập email.
