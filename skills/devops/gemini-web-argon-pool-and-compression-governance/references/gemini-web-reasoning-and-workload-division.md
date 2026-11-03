# Invariant: Gemini-Web Reasoning High Configuration & Workload Division

## 1. Bản chất Reasoning của Gemini Web trên OmniRoute (:20129)
- **Tầng Backend (`open-sse/executors/gemini-web.ts`):**
  - OmniRoute chuyển đổi tham số `reasoning_effort: "high"` sang slot 17 của protobuf StreamGenerate gửi lên Google:
    `resolveThinkingSlot("high") => [[0]]`
  - Các giá trị khác: `"low" => [[4]]`, `"none" => null`, default => `[[2]]`.
  - Phản hồi từ Google không trả thẻ `reasoning_content` riêng mà nhả luồng suy luận ngầm rồi kết xuất text hoàn chỉnh.
  - Cần cẩn trọng: Nếu gửi `reasoning_effort` không nằm trong danh sách hỗ trợ hoặc cố tình ép tham số unsupported, executor sẽ reject với mã `unsupported_control_for_provider`.

## 2. Phân tách rạch ròi 2 luồng công việc (Workload Division)
Mặc dù đều chạy trên cùng một dàn 20 tài khoản Pro Web (`Google_Live_Ready`), cấu hình payload của 2 bên bắt buộc phải khác nhau:

| Tiêu chí | Luồng Advisor & Planner | Luồng Nén Context (Hermes Compression) |
| :--- | :--- | :--- |
| **Combo đích** | `gemini-web-argon-pool` (hoặc `gemini-web`) | `gemini-web` |
| **Reasoning Effort** | **BẮT BUỘC `"high"`** (`reasoning_effort: "high"`). | **TUYỆT ĐỐI `"none"` hoặc bỏ trống**. |
| **Lý do kỹ thuật** | Cần suy luận logic sâu để đánh giá rủi ro hệ thống hoặc tính toán anchor code diff O(1) chính xác. | Nén ngữ cảnh chỉ tóm tắt văn bản một chiều. Bật high sẽ làm kéo dài latency thêm 20-40s, gây nghẽn proxy 4G và kích hoạt timeout lỗi 503. |
| **Giao thức gọi** | **SSE Streaming (`stream: True`)** tránh idle socket timeout. | **Non-streaming (Sync)** hoặc timeout dài 300s. |

## 3. Quy chuẩn code gọi tại Taadaa Tools
1. **`gate_b_planner.py` (ask_gemini_web):**
   ```python
   body = {
       "model": "gemini-web",
       "messages": [...],
       "temperature": 0.1,
       "reasoning_effort": "high",  # Ép thinking sâu
   }
   ```
2. **`consult_advisor.py` (_consult_gemini_inner):**
   ```python
   payload = {
       "model": "gemini-web-argon-pool",
       "messages": messages,
       "reasoning_effort": "high",  # Ép thinking sâu
       "stream": True,
   }
   ```
