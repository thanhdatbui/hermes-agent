# Khắc Phục Lỗi Treo CLI Advisor & Chuẩn Hóa Transport HTTP Song Song Cho Hội Đồng 3 Cố Vấn (2026-10-31)

## 1. Bản Chất Sự Cố Kẹt Khi Triệu Hồi Advisor
- **Hiện tượng:** Khi User ra lệnh triệu hồi Hội đồng Cố vấn ("gọi advisor", "hỏi advisor"), Coordinator chỉ trả về mỗi kết quả của Sol hoặc tiến trình bị ngắt/treo 60 giây.
- **Nguyên nhân gốc rễ 1 (Windows Shell Mangling):**
  - Trong `D:/Taadaa/tools/consult_advisor.py`, hàm `_consult_claude_inner` gọi CLI qua `subprocess.run(..., shell=True)`.
  - Trên Windows, `cmd.exe` tự động cắt cụt chuỗi prompt nhiều dòng tại dấu xuống dòng (`\n`) đầu tiên. Binary `claude` chỉ nhận được dòng system prompt chào hỏi mà không thấy nội dung câu hỏi nghiệp vụ phía sau, dẫn đến việc Claude chỉ trả về câu chào template rỗng.
- **Nguyên nhân gốc rễ 2 (Catalog Mismatch & Interactive Hang):**
  - Claude Code CLI version 2.1.281 trên máy mặc định dùng alias `claude-sonnet-5-5` (chưa có trong catalog), kích hoạt warning `Advisor disabled` và kẹt ngậm luồng stdin/stdout chờ timeout.
- **Nguyên nhân gốc rễ 3 (Hành vi Coordinator làm tắt):**
  - Coordinator vì sợ lệnh CLI treo nên tự ý cúp bớt cờ thành `-a sol`, vi phạm nguyên tắc Hội đồng Cố vấn 3 thành viên (Sol + Gemini + Claude).

## 2. Bản Vá Kiến Trúc Tối Ưu (HTTP Stream Transport)
- **Chuyển dịch sang HTTP trên Port 20129:**
  - Cả 3 cố vấn đều có endpoint trực tiếp trên `:20129`:
    1. 🟢 **Sol Advisor:** `review` hoặc `gpt-web-sol`
    2. 🔵 **Gemini Advisor:** `gemini-web-argon-pool`
    3. 🟣 **Claude Advisor:** `ag-sonnet` hoặc `auto/claude-sonnet`
  - Nâng cấp `_consult_claude_inner` trong `consult_advisor.py`: Ưu tiên gọi HTTP stream qua `:20129` bằng `_call_stream_chat` (first_token_timeout=30s, max_total_timeout=60s).
- **Thực thi song song thực sự (Zero Extra Latency):**
  - Chạy đồng thời 3 cố vấn qua `concurrent.futures.ThreadPoolExecutor(max_workers=3)`.
  - Toàn bộ 3 câu trả lời phản biện độc lập trả về đồng thời chỉ trong **3 - 5 giây**, triệt tiêu vĩnh viễn rủi ro deadlock hay timeout CLI.
- **Fallback CLI an toàn:**
  - Nếu HTTP không sẵn sàng, fallback sang CLI binary bắt buộc dùng `shell=False` và ép cờ `--model sonnet` để tránh lỗi catalog mismatch.
