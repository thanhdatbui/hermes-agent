# Quy tắc Xử lý Giao diện, Nhận diện Màn hình & Tương tác Farm (21/08/2026)

## 1. Popup 'Follow bạn bè của bạn' (Follow friends suggestion)
- Khi xuất hiện popup gợi ý bạn bè trên TikTok (`Follow bạn bè của bạn` / `Follow your friends`):
  - Script **ưu tiên tự động quét và bấm toàn bộ nút 'Follow lại' / 'Follow back'** xuất hiện trên danh sách để tăng follow chéo tự nhiên cho tài khoản farm.
  - Sau khi tap follow lại, script mới thực hiện bấm nút đóng (X) hoặc gửi phím Back để giải phóng popup và tiếp tục lướt Feed.

## 2. Tránh bấm nhầm nút Tạo video (+) ở đáy màn hình
- **Vị trí thanh Bottom Navigation TikTok**: Nút `(+)` nằm chính giữa ở đáy màn hình từ `Y=1794` đến `Y=1920`, tâm là `(540, 1857)`.
- **Quy tắc vuốt (Swipe) / Đóng Notification Shade**:
  - Toàn bộ lệnh vuốt lên phải bắt đầu từ `Y <= 1600` (chuẩn an toàn: `(540, 1540)` hoặc `(540, 1600)` kéo lên `(540, 400)`).
  - TUYỆT ĐỐI CẤM vuốt bắt đầu từ `Y >= 1800` (như lỗi cũ `input swipe 540 1800 ...`) vì khi cảm ứng lag sẽ biến thành cú tap kích hoạt nút `(+)` làm nhảy vào màn hình Camera quay video.
- **Quy tắc Fallback Tap**:
  - Toàn bộ tọa độ fallback khi không đọc được XML phải đặt ở giữa màn hình (`Y=1200`), cấm đặt ở vùng cận đáy `Y=1700~1715`.

## 3. Nhận diện chuẩn xác màn hình Camera / Creation Mode (`classifier.py`)
- **Vấn đề nhận diện sai (False Positive)**:
  - Video feed thông thường có thể chứa caption định dạng *"Ảnh"* hoặc nhãn cảnh báo *"Có chứa nội dung do AI tạo"*.
  - Nếu dùng `substring in text` cho các từ đơn `"ảnh"`, `"tạo"`, `"đăng"` thì video feed thông thường sẽ bị nhận nhầm thành màn hình quay video, gây dừng phiên oan.
- **Quy tắc nhận diện chính xác**:
  - Bắt buộc phải quét các element ở vùng nửa dưới màn hình (`Y >= 1000`) nơi thanh chọn chế độ quay thực sự xuất hiện.
  - Phải so khớp chính xác từ đơn (`exact match`) với danh sách chế độ quay: `{"10 phút", "60s", "15s", "văn bản", "10m", "templates", "photo", "camera"}`.
  - Phải có **ít nhất 2 chế độ quay khác nhau (`distinct modes >= 2`)** trong cùng màn hình thì mới được phân loại là màn hình Camera/Creation Mode.
  - Luôn bọc `try/except` an toàn khi gọi `parse_bounds` để chống crash khi gặp XML dị dạng.

## 4. Quy trình Code Review & Commit qua 9Router Model `plan-review`
- Mọi thay đổi logic hoặc vá lỗi code BẮT BUỘC phải qua 3 bước nghiệm thu:
  1. Chạy đầy đủ suite `pytest` đạt 100% pass.
  2. Xuất `git diff` và gọi model `plan-review` qua 9Router HTTP API (`http://127.0.0.1:20128/v1/chat/completions`) để audit độc lập.
  3. Chỉ khi reviewer trả về `{"passed": true, "verdict": "APPROVED"}` mới được tiến hành `git commit` và `git push`. Không được tự ý commit/push khi chưa có verdict APPROVED.
