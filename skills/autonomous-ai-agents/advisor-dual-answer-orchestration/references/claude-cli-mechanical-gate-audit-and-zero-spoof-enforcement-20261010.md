# Claude CLI Mechanical Gate Audit & Zero-Spoof Hardening (2026-10-10)

## Executive Summary
Cuộc điều tra độc lập từ **Claude CLI** và Operator đã phơi bày nguyên nhân cốt lõi vì sao Hermes Coordinator liên tục quên gọi Advisor Sol dù đã được dặn dò hàng chục lần qua prompt, skill doc và persistent memory:
1. **Prompt Attenuation & Context Bloat:** Các chỉ thị trong prompt/memory bị suy hao chú ý khi ngữ cảnh kéo dài. Bản năng next-token khiến LLM tự động trả lời solo ngay khi gặp câu hỏi mở/phân tích.
2. **Lỗ hổng Guard "Mù" trước Text Trực Tiếp:** Plugin `farm-coordinator-guard` trước đây chỉ hook vào `pre_tool_call`. Khi Coordinator không gọi tool mà xuất thẳng text ra Telegram, Guard hoàn toàn bất lực không thể can thiệp.

Giải pháp bắt buộc: **Chốt chặn cơ học (Mechanical Enforcement Gate)** qua hook `transform_llm_output` trong Hermes runtime.

---

## 5 Lỗ hổng Kỹ thuật Chí mạng & Quy tắc Khắc phục (Qua 3 Vòng Claude CLI Review)

### 1. Bypass sau Compression (P1 #1)
- **Triệu chứng:** Khi phiên hội thoại dài bị nén (Context Compression), session con sinh ra mang `parent_session_id = old_session_id`. Nếu code nhận diện Coordinator bằng điều kiện `parent_session_id IS NULL`, Coordinator bị coi nhầm thành worker subagent -> Gate bỏ qua im lặng đúng ở các phiên dài (nơi drift xảy ra nhiều nhất).
- **Quy tắc khắc phục:** Kiểm tra trường `source` trong bảng `sessions` của `state.db`. Chỉ có `source == 'subagent'` mới là worker. Mọi session có `source in ('telegram', 'cli')` đều là Coordinator, bất kể có `parent_session_id` hay không.

### 2. Fail-Open Im Lặng (P1 #2)
- **Triệu chứng:** Khi import module bị lỗi, kết nối tới Sol (:20129) bị từ chối hoặc timeout, nhánh `except` trả về `None` khiến tin nhắn được gửi đi mà hoàn toàn không có khối Advisor.
- **Quy tắc khắc phục:** Nếu câu hỏi của User đã được xác định là `Advice Intent`, nhánh `except` BẮT BUỘC phải nối khối:
  ```text
  --- Advisor ---
  Advisor: unavailable (Lỗi kết nối Advisor Sol; chỉ hiển thị câu trả lời Coordinator)
  ```
  Tuyệt đối không được trả `None` hoặc để mất dấu vết Advisor khi gặp lỗi mạng/thư viện.

### 3. Anti-Spoofing & Anti-Hallucination Marker (P1 #3 & P2-A)
- **Triệu chứng:** LLM đã đọc tài liệu skill nên rất dễ tự sinh (hallucinate) text `--- Advisor (Sol / review) ---` mà không hề gọi tool `consult_advisor`. Ngược lại, nếu chỉ kiểm tra substring trong lệnh shell, các lệnh `cat advisor_consult.py` hay `echo advisor_consult` cũng bị tính nhầm là gọi Sol thật.
- **Quy tắc khắc phục:**
  - Ghi nhận cờ xác minh gắn với Message ID: `advisor_verified_msg_id = latest_id` trong `_on_post_tool_call`.
  - Điều kiện xác minh Sol thật chặt chẽ:
    1. Cấm compound operators: không chứa `;`, `&&`, `|`.
    2. Cấm spoof/test flags: không chứa `--enforce`, `--classify-only`, `--response-text`.
    3. Phải gọi script python với tham số truy vấn: `-q` hoặc `--query`.
    4. Kết quả `result` sau khi strip() BẮT BUỘC phải bắt đầu bằng `--- Advisor (Sol / review) ---`.
  - Nếu câu trả lời chứa marker nhưng không có cờ `advisor_verified_msg_id == current_msg_id`: Guard lập tức lột bỏ phần marker giả mạo và kích hoạt gọi Sol thật.

### 4. Anti-Repeat trên các Background Continuation Turns (P2-A)
- **Triệu chứng:** Bộ lọc `_get_latest_user_message` bỏ qua scaffolding như `[ASYNC DELEGATION...`. Sau khi worker chạy xong, tin nhắn user gần nhất trong DB vẫn là câu hỏi tư vấn cũ. Mỗi turn cập nhật tiến độ sau đó của Coordinator sẽ tiếp tục kích hoạt gọi Sol lặp lại nhiều lần.
- **Quy tắc khắc phục:** Lưu `last_enforced_user_msg_id = msg_id` vào session state ngay khi enforce hoặc khi đã có marker hợp lệ. Nếu `last_enforced_user_msg_id == msg_id`, Gate return `None` ngay lập tức, không gọi lại Sol.

### 5. Deadline Cứng Wall-Clock trong Python (P2-C)
- **Triệu chứng chí mạng:** `with ThreadPoolExecutor(...)` trong Python có phương thức `__exit__` mặc định gọi `shutdown(wait=True)`. Khi `future.result(timeout=45.0)` ném `TimeoutError`, khối context manager vẫn tiếp tục BLOCK luồng chính cho tới khi worker thread chạy xong (có thể lên tới 90s–120s nếu socket stream bị nhỏ giọt)!
- **Quy tắc khắc phục:**
  ```python
  executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
  future = executor.submit(_consult_inner, prompt, context)
  try:
      return future.result(timeout=timeout_sec)
  except concurrent.futures.TimeoutError:
      executor.shutdown(wait=False, cancel_futures=True)
      return {
          "status": "unavailable",
          "formatted": f"--- Advisor ---\nAdvisor: unavailable (Sol / review wall-clock deadline exceeded >{timeout_sec}s; chỉ hiển thị câu trả lời Coordinator)"
      }
  finally:
      try:
          executor.shutdown(wait=False, cancel_futures=True)
      except Exception:
          pass
  ```
  Đặt `wait=False, cancel_futures=True` bảo đảm nhả thread ngay lập tức khi hết deadline, không làm nghẽn Hermes Gateway.
