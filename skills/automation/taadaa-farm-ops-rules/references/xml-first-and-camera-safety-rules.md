# Quy Tắc Bắt Buộc: XML-First Runtime & Chống Tap Tọa Độ Mù (AI Auto-Recovery & Phone Farm)

## 1. ÉP XML-FIRST Ở CẢ 2 TẦNG (PROMPT & RUNTIME EXECUTOR)
- **Tầng LLM / Vision (Gemini 3.7 Flash / GPT-5.6)**:
  - Luôn dump UI XML thực tế và tóm tắt gửi kèm ảnh màn hình.
  - Prompt bắt buộc chỉ được lấy tọa độ `[x, y]` từ `bounds` của Node UI XML thật. Tuyệt đối cấm đoán tọa độ pixel mù theo cảm tính.
- **Tầng Runtime Executor (`_execute_adb` / Action Runner)**:
  - Khi nhận lệnh `tap`, BẮT BUỘC phải đối soát tọa độ `(tx, ty)` có nằm trong bounds của một node hợp lệ trong UI XML thật vừa dump hay không.
  - Nếu KHÔNG nằm trong bất kỳ node UI nào (hoặc không có XML hợp lệ) -> **TỪ CHỐI TAP MÙ**, tự động fallback an toàn (phím `BACK` hoặc vuốt lướt qua), tuyệt đối không gửi `input tap` bừa bãi.

## 2. TRÁNH KHU VỰC CẬN ĐÁY (BOTTOM BAR NÚT QUAY CAMERA +)
- **Vị trí nút Tạo/Quay video (+)**:
  - Nằm chính giữa thanh Bottom Navigation của TikTok: bounds `[432, 1794][648, 1920]` (tâm là `X: 540, Y: 1857`).
- **Quy tắc vuốt an toàn**:
  - Tuyệt đối CẤM gửi lệnh `input swipe 540 1800 ...` (vuốt bắt đầu từ Y=1800) vì độ trễ cảm ứng hoặc lag sẽ biến thành click trúng nút `(+)` và bật Camera làm kẹt hàng loạt máy.
  - Tọa độ vuốt an toàn bắt buộc phải bắt đầu từ `Y <= 1540` (ví dụ: `540 1540 540 300` hoặc `450 1540 450 620`).
- **Quy tắc Fallback Tap**:
  - Các điểm fallback tap khi đóng popup tuyệt đối không đặt ở vùng `Y >= 1700` mà phải đặt ở giữa màn hình `(540, 1200)` hoặc gửi phím `BACK` (`keyevent 4`).

## 3. NHẬN DIỆN CAMERA MODE CHÍNH XÁC (TRÁNH FALSE-POSITIVE DO CAPTION FEED)
- **Lỗ hổng cũ**:
  - Substring matching trên từ đơn phổ biến như `"ảnh"` hay `"tạo"` khiến các video feed bình thường có caption (ví dụ: *"Có chứa nội dung do AI tạo"*, *"Ảnh"*) bị classifier nhận nhầm là màn hình Camera quay video, dẫn đến dừng phiên oan.
- **Quy chuẩn nhận diện**:
  - Bắt buộc kiểm tra exact match ở vùng nửa dưới màn hình (`Y >= 1000`) và yêu cầu ít nhất 2 chế độ quay khác nhau (`distinct modes >= 2` trong tập hợp `{"15s", "60s", "10 phút", "văn bản", "10m", "templates", "photo", "camera"}`).
  - Bọc an toàn `try/except` cho `parse_bounds` để chống crash khi gặp XML dị dạng.
