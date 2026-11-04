# Smart Action Mandate: Consultative Intent Decoupling & Anti-Spam (2026-11-04)

## 1. Bản Chất Vấn Đề (The Action Mandate Trap)
- **Cơ chế cũ (Lexical Regex)**: Trong `agent/conversation_loop.py`, hệ thống quét 300 ký tự cuối của `final_response` tìm các cụm từ đàm thoại (`'đang cho '`, `'đang kiểm tra'`, `'sẽ báo cáo'`, `'để em '`, `'em sẽ '`).
- **Hệ quả tiêu cực**:
  * Khi User hỏi tư vấn, chất vấn kỹ thuật hoặc thảo luận hướng làm (`Tại sao`, `Là sao`, `Khác gì`, `Có nên`), Coordinator trả lời bằng câu chữ giải thích. Nếu vô tình xuất hiện các từ `"em sẽ"`, `"để em"` ở cuối câu, Action Mandate lập tức giật cờ, hủy câu trả lời và ép phải gọi `tool_call`.
  * Coordinator bị dồn vào chân tường, sinh phản xạ đối phó: chạy lệnh đo kiểm rác (`probe_http`, `cat /proc/uptime`) để làm "vé qua cổng". Kết quả là câu trả lời tư vấn bị băm nát, gây bức xúc tột độ cho User.

## 2. Kiến Trúc Smart Action Mandate O(1)
- **Nguyên lý cốt lõi**: Tách bạch dứt khoát giữa **Execution Intent (Ý định thi công)** và **Consultative Intent (Ý định tư vấn/đối thoại)**:
  ```python
  EXECUTION_SIGNALS = {
      'đang tiến hành ', 'i will deploy', 'i will execute', 'i am deploying',
      'đang deploy', 'đang cài đặt', 'đang quét ', 'đang chạy ', 'đang xử lý',
  }
  CONSULTATIVE_MARKERS = {
      'sếp', 'anh', 'tùy', 'nếu', 'có nên', 'thế nào', 'sao', '?',
      'giải thích', 'tư vấn', 'nghĩ sao', 'thấy sao', 'đúng không',
  }
  
  _tail = (final_response or '').strip().lower()[-300:]
  _is_consultative = _tail.endswith('?') or any(k in _tail for k in CONSULTATIVE_MARKERS)
  _matched_action = None if _is_consultative else next((p for p in _action_phrases if p in _tail), None)
  ```
- **Kỷ luật hai chiều**:
  1. **Khi đối thoại/tư vấn**: Tự động BYPASS, cho phép trả lời trực diện bằng lý lẽ, cấm chạy lệnh rác làm màu.
  2. **Khi thi công thực tế**: Nếu chứa các cụm từ hành động cụ thể (`"đang deploy"`, `"đang cài đặt"`) mà không phát tool call $\rightarrow$ Chặn đứng 100%, bắt buộc phải xách tool ra làm thật.

## 3. Cấm Cắt Bỏ Toàn Bộ Guard
- Guard sinh ra là để ngăn chặn bot nói mồm, hứa hão và trốn việc. Việc gặp lỗi false positive mà đi cắt sạch toàn bộ Guard là hành vi **bại liệt, làm ẩu, phá vỡ an toàn hệ thống**.
- Giải pháp chuẩn mực luôn là: **Vá bộ lọc thông minh (Consultative Bypass) ở mức O(1)** để giữ vững kỷ luật thực thi mà không gây nghẽn đàm thoại.
