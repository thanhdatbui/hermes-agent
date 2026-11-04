# Smart Action Mandate vs Heuristic Regex Trap

## 1. Bản Chất Sự Cố
- **Hiện tượng:** Bộ kiểm tra `Action Mandate` trong vòng lặp đàm thoại (`conversation_loop.py`) quét chuỗi tự nhiên thô ở 300 ký tự cuối response:
  ```python
  _action_phrases = ('đang cho ', 'đang kiểm tra', 'sẽ báo cáo', 'để em ', 'em sẽ ', 'đang chạy ', ...)
  ```
- **Hậu quả:** Khi Operator hỏi câu hỏi tư vấn, thảo luận, đối thoại hoặc chất vấn kiến trúc mạng, nếu Model lỡ dùng từ xưng hô đàm thoại tự nhiên (`"để em..."`, `"em sẽ..."`), Mandate giật cờ chặn đứng câu trả lời, hủy `final_response` và ép bot phải gọi tool call đo kiểm vô nghĩa làm "vé qua cổng".
- **Bại liệt hành vi:** Khiến câu trả lời tư vấn thực sự của bot bị mất sạch, thay vào đó là những dòng log đo kiểm nhảm nhí, gây ức chế cực độ cho Operator.

## 2. Kiến Trúc Khắc Phục Chuẩn O(1) (Không Over-Engineer)
- **Tách bạch dứt khoát 2 Intent:**
  1. `EXECUTION_SIGNALS`: Chỉ bắt các cụm từ thi công hệ thống rõ ràng:
     `{'đang tiến hành ', 'i will deploy', 'đang cài đặt', 'đang deploy'}`.
     -> Xóa bỏ vĩnh viễn các từ đàm thoại thông thường: `'em sẽ '`, `'để em '`, `'sẽ báo cáo'`.
  2. `CONSULTATIVE_MARKERS`: Nhận diện lượt đối thoại/tư vấn:
     `{'sếp', 'anh', 'tùy', 'nếu', 'có nên', 'thế nào', 'sao', '?'}`.
- **Cơ chế vận hành:**
  ```python
  is_consultative = tail.endswith('?') or any(k in tail for k in CONSULTATIVE_MARKERS)
  if is_consultative:
      _matched_action = None  # Bypass 100% Mandate, cho phép trả lời lý lẽ tự nhiên
  ```
- **Unit Test chống hồi quy:** Duy trì test case `test_smart_action_mandate_logic()` trong `tests/test_action_mandate_loop.py`.
