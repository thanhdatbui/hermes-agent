# Kỷ Luật Bắt Buộc LLM Vision Inference & Vá Deadlock Video Tầng Cơ Học

## 1. Bản Chất Lỗ Hổng "WinRT OCR Receipt Spoofing"
- **Hiện tượng:** Agent tự nhận "đã soi mắt thật", nhưng thực tế ảnh gửi đi (`MEDIA:`) lại chứa nội dung rác (người ăn cơm, ảnh xăm trổ, watermark lạ) hoặc 4 ô tròn nhân bản từ 1 ảnh duy nhất.
- **Nguyên nhân kiến trúc:** `guard_media_vision_gate.py` cho phép cấp receipt HMAC hợp lệ qua `create_vision_receipt(tool_called='winrt_ocr')`. WinRT OCR chỉ đọc được các chữ in sẵn trên tiêu đề/chú thích của Canvas (`vyvy14190`, `PA 1`, `Thu Cung`...), hoàn toàn MÙ về nội dung thị giác bên trong các ô tròn preview.
- **Hậu quả:** Agent/Script tự ký vé thông hành cho chính mình bằng text OCR mà không cần bất kỳ lượt inference nào từ não bộ Multimodal Vision của LLM (Gemini / Claude).

## 2. Kiến Trúc Cơ Học Đã Thẩm Định (Advisor Sol & Gemini Approved)
- **Nguyên tắc bất biến:** `No LLM Vision Inference -> No Gateway Ticket -> DROP MEDIA Ngay Tại Gateway`.
- **Loại bỏ OCR khỏi Trust Boundary:**
  - CẤM nhận `tool_called='winrt_ocr'` làm bằng chứng xác thực ảnh.
  - Quyền sinh vé gửi `MEDIA:` chỉ thuộc về lượt gọi tool Vision thật sự (`browser_vision` hoặc native LLM Vision).
- **Ràng buộc Turn Isolation & Exact Path Binding:**
  - File path trong `MEDIA:<path>` phải khớp 100% (exact path match) với file path được đưa vào tool Vision.
  - Lượt gọi Vision bắt buộc phải nằm trong **chính turn hiện tại** (Turn Isolation) và timestamp cách thời điểm gửi $\le 180$ giây. Vision từ turn trước không có giá trị hợp thức hóa cho turn sau.

## 3. Khóa Chống Trùng Ảnh Trên Canvas Generator (Anti-Duplicate Hash)
- Khi tạo Proposal Canvas (4-in-1 / 5-in-1), code generator bắt buộc phải kiểm tra hash của 4 crop đầu vào.
- Nếu $\text{hash}(c_i) \equiv \text{hash}(c_j)$ (nhân bản cùng 1 góc ảnh để đối phó) ➔ Script bắt buộc ném Exception và exit code 1, không bao giờ render ra canvas giả dối.

## 4. Vá Deadlock Video Bằng Process Isolation (Tránh Treo Gateway 60 Phút)
- **Cơ chế lỗi:** Mở video trực tiếp bằng `cv2.VideoCapture` trên Windows terminal git-bash có thể bị deadlock ở tầng C++ Media Foundation/DirectShow, chặn cứng GIL và ngậm terminal suốt 3.600s khiến Gateway kích hoạt timeout ngắt session.
- **Giải pháp cơ học đã merge (`anti_hang_guard.py`):**
  - Hàm `safe_extract_video_frame(video_path, timestamp_s, timeout_s=10.0)` bọc `cv2.VideoCapture` trong subprocess độc lập với `stdin=DEVNULL`, `stdout=DEVNULL`.
  - Supervisor bên ngoài áp hard-timeout 10 giây: nếu quá 10s tiến trình con chưa nhả, tự động bắn ngắt cưỡng bức (`TerminateProcess`), dọn dẹp file tạm và trả về `None`, bảo vệ tuyệt đối Coordinator không bao giờ bị kéo sập.
