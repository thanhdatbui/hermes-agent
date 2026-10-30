# Bẫy UiAutomator Nuốt Node Trong GMS WebView & Fallback Tọa Độ Bước [05_create]

## 1. Hiện Tượng & Root Cause
- **Bối cảnh:** Khi đăng ký Gmail trên thiết bị Android (Samsung S7 / GMS WebView), ở bước `[05_create]`, WebView load trang Đăng nhập Google (`identifierId`).
- **Triệu chứng lỗi:**
  - Script báo lỗi: `[05_create] Không tìm thấy Tạo tài khoản/Create account`.
  - Cây UI XML trích xuất qua ATX/UiAutomator hoàn toàn không có node chứa chữ "Tạo tài khoản" (chỉ có từ `identifierId` trở lên và nút `TIẾP THEO` ở bounds `[716,1740][1020,1884]`).
  - Hàm fallback `find_clickable_button_by_region(xml, ...)` duyệt trên XML cũng tịt ngòi vì node không tồn tại trong cây XML.
- **Sự thật hiện trường (Kiểm chứng bằng WinRT OCR trên ảnh chụp màn hình):**
  - Chữ "Tạo tài khoản" **THỰC TẾ CÓ HIỂN THỊ TRÊN MÀN HÌNH** tại tọa độ:
    `Tao tai khoan | Bounds: X=73, Y=1448, W=116, H=34` (center khoảng `(200, 1450)`).
  - Đây là bẫy kinh điển: Google WebView render phần tử web dạng text/link nhưng UiAutomator của Android 8.0 không tạo Accessibility Node tương ứng trong cây XML.

## 2. Quy Tắc Khắc Phục Dứt Điểm (O(1) Fallback Invariant)
1. **Không tin tuyệt đối vào XML dump của WebView:**
   - Khi UI XML đã xác nhận đang ở đúng màn hình Google Sign-in (có `identifierId` hoặc `Email hoặc số điện thoại`):
   - Nếu `find_text_tap` không thấy node VÀ `find_clickable_button_by_region` không tìm thấy button trong XML:
   - **BẮT BUỘC tap fallback trực tiếp vào tọa độ đã đo chuẩn:** `tap(device_id, 200, 1450, wait=D_MEDIUM)`.
2. **Kiểm tra trạng thái sau khi tap tọa độ:**
   - Sau khi tap `(200, 1450)`, thăm dò sự xuất hiện của menu cá nhân: `"Dành cho mục đích cá nhân"` / `"For my personal use"`.
   - Nếu menu xuất hiện -> tiếp tục luồng bình thường.
   - Tránh việc ném `RuntimeError` dừng máy mù quáng chỉ vì cây Accessibility Tree bị nuốt node.

## 3. Bài Học Điều Phối & Đọc Ảnh (Anti-Blindness Invariant)
- **Cấm phán đoán mù khi xem ảnh:** Không được chỉ nhìn lướt hoặc dựa vào việc XML thiếu node mà khẳng định trên ảnh không có nút. Bắt buộc dùng `winrt_ocr_util.py` quét toàn bộ bounding rect của chữ trên ảnh trước khi kết luận.
- **Cấm hứa hẹn suông rồi đứng im:** Turn kết thúc không được dừng lại ở tin nhắn hứa hẹn ("Em đang chuẩn bị đẩy bản patch...") mà phải kích hoạt pipeline / tool ngay trong cùng turn.
