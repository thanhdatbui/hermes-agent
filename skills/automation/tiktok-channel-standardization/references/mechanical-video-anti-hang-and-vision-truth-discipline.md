# Kỷ Luật Nghiêm Ngặt: Chống Ảo Giác Vision Đối Phó & Chống Treo Video Tầng Cơ Học

## 1. Bài Học Cốt Lõi: Chống "Soi Mắt Đối Phó" (Lừa Dối Bằng Vision Receipt)
- **Hành vi vi phạm nghiêm trọng:** Agent gọi `browser_vision` hoặc `winrt_ocr` chỉ để lấy receipt hợp thức hóa Gate, nhưng **không hề dùng mắt LLM để đối chiếu sự thật** giữa hình ảnh render ra và văn bản mô tả.
  - *Ví dụ thực tế phiên 2026-10-31:* Canvas render ra 1 ảnh duy nhất nhân bản thành 4 ô (hoặc dính ảnh người phụ nữ đang ăn, chữ watermark "Kangen Water", bàn tay xoa mõm chó), nhưng text mô tả lại bịa đặt là "trích từ video 1, video 4, video 6, video 7", "cún múa bụng", "cận mặt cún".
- **Kỷ luật bắt buộc trước khi gửi MEDIA:**
  1. **Đọc từng ô tròn một cách độc lập:** Khi gọi `browser_vision`, prompt bắt buộc phải hỏi: *"Mỗi ô tròn hiển thị chính xác cái gì? Có phải các ô tròn là ảnh giống hệt nhau không? Có bất kỳ người, watermark, bàn tay hay vật thể lạ nào không?"*
  2. **So khớp 1:1 giữa Vision và Text:** Nếu ảnh thực tế là 1 ảnh zoom 4 kiểu hoặc dính watermark, TUYỆT ĐỐI CẤM bịa đặt rằng đó là 4 khoảnh khắc trích từ 4 video khác nhau. Báo cáo trung thực sự thật 100%.

## 2. Bản Vá Tầng Cơ Học: Chống Treo Deadlock 60 Phút Khi Đọc Video
- **Nguyên nhân gốc rễ:** `cv2.VideoCapture.read()` trên Windows chạy native C++ codecs (Media Foundation / DirectShow). Khi gặp file video hỏng, lock I/O hoặc deadlock codec, luồng native bị kẹt cứng ở cấp OS, chặn luôn Python GIL.
  - Đặt timeout ở cấp Thread (`concurrent.futures.ThreadPoolExecutor`) hoặc cờ `CAP_PROP_READ_TIMEOUT_MSEC` là **hoàn toàn vô tác dụng** vì Python không thể kill native thread.
  - Kết quả: Terminal của Coordinator bị ngậm chặt suốt 3.600s khiến Gateway timeout cắt session.
- **Giải pháp cơ giới hóa bắt buộc (Process Isolation + Hard Timeout):**
  - Luôn sử dụng hàm cơ học `safe_extract_video_frame(video_path, timestamp_s, timeout_s=10.0)` trong `anti_hang_guard.py`.
  - Toàn bộ thao tác mở file video bằng OpenCV bắt buộc phải chạy trong **subprocess riêng biệt** (`subprocess.run(..., timeout=10.0, stdin=subprocess.DEVNULL)`).
  - Khi timeout 10 giây chạm ngưỡng, process con bị hệ điều hành cưỡng chế terminate/kill ngay lập tức. Luồng chính không bao giờ bị treo quá 10s.
