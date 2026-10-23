# Strictly On-Demand Advisor Gate & Heuristic Removal (2026-10-24)

## 1. Bản Chất Bẫy Phán Đoán Mù (Heuristic Guessing Trap)
- **Hiện tượng:** Operator đã nhiều lần yêu cầu tắt Advisor Sol tự động, nhưng hệ thống vẫn tự động kích hoạt Sol chen ngang vào Telegram khi Operator hỏi các câu chat bình thường như:
  `"Ý là canary xem cron có fix đc k ?"`
- **Nguyên nhân cốt lõi trong code:** Hàm `_is_advice_request()` trong `agent/conversation_loop.py` trước đây cài đặt cơ chế đoán ý tự động dựa trên:
  1. Danh sách từ suy đoán: `"tư vấn"`, `"lời khuyên"`, `"có nên"`, `"theo mày"`, `"đánh giá"`, `"phân tích giúp"`, `"what should"`, `"should i"`, `"advise me"`.
  2. Nhánh logic kiểm tra từ khóa: `if has_phrase("nên"): return "?" in text or "？" in text ...`.
- **Hậu quả:** Bất kỳ câu hỏi nào có chứa từ ngữ thông thường hoặc dấu hỏi `?` đều kích hoạt ngầm `advisor_consult`, gây nghẽn kết nối, làm chậm thời gian phản hồi (15s–35s) và làm loãng mạch hội thoại với những câu trả lời thiếu ngữ cảnh ("ngáo ngơ") từ Sol stateless.

## 2. Quy Chuẩn Cơ Học On-Demand Tuyệt Đối (Zero Heuristics)
- **Quy tắc bất biến:** CẤM TUYỆT ĐỐI đoán ý người dùng bằng từ khóa chung chung hay dấu hỏi `?`.
- **Danh sách kích hoạt duy nhất (Explicit Command Only):**
  Hàm `_is_advice_request()` CHỈ được phép trả về `True` khi message chứa đích danh tên Sol / Advisor:
  ```python
  _ADVISOR_EXPLICIT_TRIGGERS = (
      "gọi advisor",
      "hỏi sol",
      "gọi sol",
      "sol thấy sao",
      "nhờ sol review",
      "sol lên plan",
  )
  ```
- **Hành vi khi không có trigger đích danh:**
  - `_is_advice_request` trả về `False` ngay lập tức.
  - Cổng điều phối bỏ qua (skip) 100% cuộc gọi tới Advisor Sol.
  - Coordinator trả lời trực tiếp trong 0ms delay mà không chạm tới `:20129`.
