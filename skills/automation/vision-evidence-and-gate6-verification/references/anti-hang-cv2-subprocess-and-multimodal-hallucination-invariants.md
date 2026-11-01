# Mechanical Anti-Hang & Visual Hallucination Invariants

## 1. Bản Chất Sự Cố Treo Terminal 60 Phút (3609s)
- **Triệu chứng:** Coordinator chạy Python script mở `cv2.VideoCapture` trực tiếp trong terminal git-bash trên Windows, dẫn đến deadlock tầng C++ codec / DirectShow / Media Foundation.
- **Hậu quả:** GIL bị khóa, process ngậm stdout vô hạn, `timeout=` thông thường của subprocess Python trên Windows không kill được process tree con, khiến Hermes Gateway đếm đủ 3.600s mới kích hoạt timeout và ngắt phiên.
- **Giải pháp cơ học bắt buộc (Process Isolation + Hard-Kill):**
  1. Tuyệt đối CẤM gọi `cv2.VideoCapture` trực tiếp trong foreground terminal hoặc luồng chính.
  2. Bắt buộc dùng `safe_extract_video_frame(video_path, timestamp_s, timeout_s=10.0)` trong `D:/Taadaa/tools/anti_hang_guard.py`.
  3. Hàm này chạy trên subprocess độc lập (`stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL`) và có cơ chế `taskkill /F /T /PID` để diệt sạch cả cây tiến trình con nếu chạm mốc timeout.
  4. Mọi lệnh chạy subprocess trong `run_safe_command` nếu phát hiện chuỗi `cv2.VideoCapture` hoặc `VideoCapture` trực tiếp thì chặn đứng ngay lập tức (Exit code 1).

## 2. Bệnh Ảo Giác "Mở Mắt Nhìn A Nhưng Miệng Bịa B" Của Model Sinh Xác Suất
- **Hiện tượng:** Gemini Flash khi nhận lệnh chuẩn hóa kênh thú cưng, dù đã gọi tool `browser_vision` mở ảnh thật ra xem, nhưng ở lượt sinh text tiếp theo nó vẫn bị cuốn theo prompt và tự biên tự diễn:
  - Trên ảnh thực tế: Có bàn tay người dính dầu mỡ cầm gioăng cao su, ảnh người phụ nữ ăn cơm, ảnh selfie chu môi.
  - Văn bản agent chat: Tuyên bố chắc nịch "Đã soi mắt 100%, PA 1 cún đứng phòng khách, PA 2 cún nằm sàn gạch, PA 4 cún cận mặt".
- **Gốc rễ:** Kho video gốc (ví dụ `D:/video goc/394`) có thể là **kho hỗn tạp** bị trộn lẫn nhiều chủ đề (clip sửa xe dính dầu mỡ, clip selfie phụ nữ, clip nấu ăn). Agent blind-extract từ `394/1.mp4`, `394/6.mp4` mà không kiểm tra nhãn thực tế của từng clip, dẫn đến hallucination.
- **Quy tắc kiểm tra kho media hỗn hợp:**
  1. Trước khi tạo Proposal Canvas từ kho `video goc`, bắt buộc phải sample và kiểm tra nhãn của từng video nguồn qua vision.
  2. Không được lấy frame từ các video có chủ thể không đồng nhất.
  3. Nếu kho chỉ có duy nhất 1 ảnh/clip cún chuẩn (ví dụ `589/avatar.jpg`), ưu tiên crop nhiều góc/tỷ lệ khác nhau từ chính nguồn chuẩn đó, tuyệt đối không vơ vét frame rác từ kho hỗn tạp.

## 3. Chốt Chặn Cơ Học Guard Media Vision Gate
- Trong `D:/Taadaa/tools/guard_media_vision_gate.py`:
  - **Xóa sạch 100% heuristic `is_visual_claim`** (lọc từ ngữ cảm tính).
  - Mọi ảnh thuộc nhóm visual (`proposal`, `canvas`, `cand`, `preview`, `avatar`): bắt buộc `tool_called` phải nằm trong `('browser_vision', 'ag_cli_vision')`.
  - Nếu là `winrt_ocr` hoặc OCR thô: Gate từ chối ký receipt và trả về ngay `UNVERIFIED_BY_VISION`. Không có receipt hợp lệ -> Gateway DROP thẻ `MEDIA:`.

## 4. Chuẩn Hóa Gọi Advisor Hội Đồng 3 Model (Sol + Gemini + Claude)
- **Lỗi cũ:** Gọi `subprocess.run(shell=True)` trên Windows làm cmd.exe cắt cụt prompt nhiều dòng; model catalog trong `claude_worker.py` bị hardcode tên cũ `claude-sonnet-5-5` gây treo 60s.
- **Chuẩn hóa:**
  - `_consult_claude_inner` trong `consult_advisor.py` bắt buộc chạy qua `claude_worker.py --role reviewer --on-demand`.
  - Model mapping trong `claude_worker.py`: `planner` và `reviewer` map sang alias chuẩn `sonnet`, `worker` map sang `haiku`.
  - Cả 3 model (Sol :20129, Gemini Argon 4 :20129, Claude CLI native) đều phải phản hồi trong <= 30-45s, fail-closed khi có timeout.
