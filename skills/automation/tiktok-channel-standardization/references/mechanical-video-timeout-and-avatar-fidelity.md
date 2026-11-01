# Kỷ Luật Cơ Học Chống Treo Video & Bắt Buộc Soi Mắt Đọc Ảnh Thật

## 1. Bản Chất Bẫy Treo 60 Phút Khi Quét Video (OpenCV VideoCapture Hang)
- **Cơ chế lỗi:** Khi script Python gọi `cv2.VideoCapture` đồng bộ trong terminal foreground để mở nhiều file `.mp4` (đặc biệt trên Windows qua DirectShow/Media Foundation), một video bị lỗi codec, lock tranh chấp hoặc stream dở dang có thể gây deadlock cấp C++/OS.
- **Hậu quả:** Deadlock ngậm chặt luồng stdout/stderr, chặn GIL, không bao giờ nhả exit code. Sau 3.600s (60 phút), Hermes Gateway phát hiện không có tool activity và tự động ngắt kết nối session (`Agent inactive for 60 min — no tool calls or API responses`).
- **Giải pháp tầng cơ học (Mechanical Hard-Timeout):**
  - CẤM TUYỆT ĐỐI gọi vòng lặp `cv2.VideoCapture` đồng bộ không kiểm soát thời gian trong main thread.
  - CẤM DÙNG THREAD TIMEOUT (theo Advisor Sol): Python không thể cưỡng chế kill an toàn một thread đang kẹt bên trong native OpenCV/FFmpeg C++ code. Đặt `CAP_PROP_READ_TIMEOUT_MSEC` hay ThreadPool timeout vẫn bị ngậm luồng OS.
  - BẮT BUỘC PROCESS ISOLATION: Sử dụng hàm chuẩn hóa `safe_extract_video_frame()` trong `anti_hang_guard.py` (spawn `subprocess.run(..., stdin=subprocess.DEVNULL, timeout=10.0)`).
  - Quá 10 giây: Subprocess bị cưỡng chế terminate/kill ở cấp OS, trả về `None`, không bao giờ kéo sập hay ngậm terminal của Coordinator quá 10s.

## 2. Kỷ Luật LLM Vision Soi Mắt Đọc Ảnh Thật Trước Khi Suy Luận
- **CẤM KỶ LUẬT MÕM / SUY LUẬN MÒ:**
  - Không được dựa vào tên file, số thứ tự hay phỏng đoán nội dung từ text cũ.
  - Trước khi kết luận chủ thể kênh (Người vs Thú cưng / Nữ vs Nam), BẮT BUỘC gọi `browser_vision` mở ảnh chụp màn hình kênh (Profile/Switcher) và video thumbnail ra soi mắt thật.
- **Tiêu Chuẩn Đồng Bộ 100% Giữa Preview Vòng Tròn Và Mô Tả Text:**
  - Bẫy kinh điển ("Nhãn cún, ruột ngũ cốc / mặt người"): Text nhãn ghi "PA 1: Cún nghiêng đầu", "PA 2: Cận mặt cún", "PA 3: Cún múa bụng" nhưng bên trong vòng tròn preview thực tế lại chứa hộp ngũ cốc Froot Loops, selfie mặt người chu môi, hoặc ảnh vòi nước Kangen Water do crop nhầm video hoặc file rác chưa được kiểm tra bằng mắt.
  - BẮT BUỘC gọi `browser_vision` soi lại chính Proposal Canvas sau khi render: Yêu cầu LLM mô tả cụ thể từng vòng tròn 1, 2, 3, 4 để xác nhận 100% là chủ thể thật (cún cưng), không dính bất kỳ tạp vật, mặt người lạ hay hộp ngũ cốc nào trước khi gửi cho User.
