# LLM Benchmark Integrity & Ground-Truth Verification Contract

## 1. Nguyên Tắc Cốt Lõi: Chống Ảo Giác và Fabricated Benchmark
- **CẤM TUYỆT ĐỐI ỷ lại vào exit code / `code_valid`:** Việc `ast.parse()` chạy qua hoặc `returncode == 0` chỉ chứng minh output là cú pháp Python hợp lệ, KHÔNG chứng minh model đã giải đúng đề bài.
- **CẤM bịa đặt nhận xét chuyên môn:** Tuyệt đối không tự suy diễn lời bình ("tách ma trận 2D", "phòng thủ PermissionError") từ đề bài nếu chưa đọc tận mắt nội dung output thực tế.
- **Ground-Truth Verification:** Mọi bảng so sánh benchmark bắt buộc phải đính kèm trích đoạn mã nguồn thực tế (Head/Tail + hàm nghiệp vụ cốt lõi) được dump từ file log hoặc response artifact.

## 2. Web UI CDP Daemon & Context Isolation
Khi bọc Web UI (Gemini Web, ChatGPT Web) thành API qua Playwright CDP:
- **Tử huyệt nhai lại DOM cũ (Stale Turn Contamination):**
  - Nếu không reset cuộc trò chuyện (New Chat / Temporary Chat), các khối code (`pre`, `code-block`, `.code-container`) của câu hỏi trước sẽ nằm nguyên trong DOM.
  - Khi prompt mới gửi đi, nếu selector quét toàn trang (`page.locator('pre code').all()`), script sẽ bốc nhầm khối code của lượt trước và trả về ngay sau vài giây -> Gây ra hiện tượng "thời gian phản hồi siêu tốc giả mạo" (15s-18s) và "bài này cắm cằm bà kia".
- **Giải pháp bắt buộc:**
  1. **Fresh Session per Turn:** Bắt buộc bấm `New Chat` (hoặc mở URL gốc `/app`) trước mỗi prompt để DOM luôn ở trạng thái 0 lượt phản hồi.
  2. **Turn Isolation Selector:** Bắt buộc đếm số lượng turn trước khi gửi (`turns_before`), đợi turn mới render xong (`turns_after == turns_before + 1`), và CHỈ trích xuất dữ liệu trong turn mới nhất (`turns.last`).
  3. **Angular/Custom Component Selector:** Trên Gemini Web hiện đại, Google tách text dẫn nhập (`.model-response-text`) ra khỏi khối code thật (`<code-block>` / `pre.code-container`). Bắt buộc trích xuất trực tiếp từ `<code-block>` hoặc container chứa code.

## 3. Cấu Hình Timeout & Model cho AGY CLI (Antigravity Pool)
- **Model chuẩn hóa:**
  - AGY CLI mặc định dùng `gemini-3.8-flash-medium` để cân bằng giữa tốc độ và độ sâu logic.
  - Tránh ép lên `gemini-3.8-flash-high` cho các task sinh mã lớn (>150 dòng) qua proxy 4G vì thời gian stream Deep Think có thể vượt quá 120s gây timeout giả mạo.
- **Ngưỡng Timeout tối thiểu:**
  - `ask` (phân tích/hỏi đáp code): Tối thiểu **300s (5 phút)**.
  - `fix` (sửa mã/refactor module): Tối thiểu **600s (10 phút)**.
  - `dispatch_worker.py`: Tối thiểu **180s (3 phút)**.
- **Failover khi Timeout:**
  - Khi một profile dính `subprocess.TimeoutExpired`, bắt buộc đặt cooldown (300s) cho profile đó, cập nhật `last_used` để đẩy xuống cuối hàng đợi, và kích hoạt `continue` để tự động rotate sang profile tiếp theo trong 22 profile, cấm văng chết tiến trình điều phối.
