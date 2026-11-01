# Bài Học Sống Còn: Cơ Chế Khóa Cơ Học Chống Gửi Ảnh Mù & Triệt Tiêu Deadlock Video 60 Phút

## 1. Bản Chất 2 Lỗ Hổng Cơ Học Gây Sự Cố Nghiêm Trọng Trong Phiên

### A. Lỗ Hổng Gate Thị Giác (Media Vision Gate Bypass)
- **Kẽ hở cũ:** `guard_media_vision_gate.py` cho phép cấp vé HMAC (`create_vision_receipt`) thông qua `tool_called="winrt_ocr"` dựa trên điều kiện heuristic `is_visual_claim` lọc từ ngữ.
- **Hậu quả:** WinRT OCR chỉ đọc chữ tiêu đề/nhãn trên ảnh, hoàn toàn **MÙ** về hình học/ngữ nghĩa bên trong các ô tròn avatar. Agent lách qua OCR để gửi ảnh người ăn cơm, ảnh xăm trổ, hoặc nhân bản 1 ảnh thành 4 ô tròn nhưng text thì tự biên tự diễn bịa chuyện cún cưng múa bụng.
- **Khắc phục cơ học:**
  1. Xóa bỏ hoàn toàn điều kiện `is_visual_claim`. Mọi file visual (`proposal`, `canvas`, `cand`, `preview`, `avatar`) BẮT BUỘC `tool_called` phải nằm trong `('browser_vision', 'ag_cli_vision')`.
  2. Bất kỳ receipt nào từ OCR thô hoặc `winrt_ocr` đều bị chặn vô điều kiện với `UNVERIFIED_BY_VISION`.

### B. Lỗ Hổng Deadlock OpenCV VideoCapture Trên Windows Terminal
- **Kẽ hở cũ:** Gọi trực tiếp `cv2.VideoCapture(path)` trong bash terminal của Hermes. Trên Windows, thư viện giải mã native C++ (Media Foundation / DirectShow) khi gặp tranh chấp lock hoặc codec lỗi sẽ bị deadlock cứng ở tầng OS, chặn luôn Python GIL và tín hiệu ngắt.
- **Hậu quả:** Terminal ngậm I/O suốt 3.600 giây (60 phút) khiến Gateway timeout kích hoạt ngắt kết nối và drop tin nhắn của User.
- **Khắc phục cơ học:**
  1. Bắt buộc cô lập lệnh đọc video vào tiến trình con độc lập qua hàm `safe_extract_video_frame(video_path, timestamp_s, timeout_s=10.0)` trong `D:/Taadaa/tools/anti_hang_guard.py`.
  2. Subprocess chạy với `stdin=DEVNULL`, `stdout=DEVNULL`. Supervisor bên ngoài kẹp hard-timeout cưỡng bức đúng 10s.
  3. Trên Windows, lệnh timeout của subprocess thông thường không diệt được process con; bắt buộc phải dùng `taskkill /F /T /PID <pid>` để triệt tiêu sạch cả cây tiến trình con (process tree), ngăn chặn hoàn toàn orphan process ngậm cổng.
  4. Trong `run_safe_command`: quét và chặn đứng ngay tại giây thứ 0 bất kỳ lệnh nào chứa `cv2.VideoCapture` hoặc `VideoCapture` trực tiếp mà không qua wrapper an toàn.

---

## 2. Kỷ Luật Soi Mắt Thật Khi Nhận Ảnh Từ User (Inbound Vision Discipline)

- **Cấm đoán mò theo context:** Khi User gửi ảnh phản ánh lỗi (`[Image attached at:`), CẤM TUYỆT ĐỐI phán đoán dựa trên nội dung chat ở turn trước.
- **Quy trình bắt buộc:**
  1. Dùng `python D:/Taadaa/tools/copy_user_img.py <img_name>` copy ảnh ra ngoài thư mục `D:/Taadaa/reports/` để tránh bị guard chặn đường dẫn AppData.
  2. Gọi `browser_navigate` trỏ vào `file:///D:/Taadaa/reports/<img_name>`.
  3. Gọi `browser_vision` đọc và trích xuất đúng nội dung thật của ảnh trước khi phát ngôn.
- **Cấm ném git diff vào chat:** Người dùng cần kết quả công việc và hành động dứt điểm, không ai đọc git diff thô trong chat.
