# Reasoning Model Stream Timeout & Idle Discipline (2026-10-15)

## 1. Bản chất vấn đề: Sự khác biệt giữa Chat Model vs Reasoning Model
- **Chat Models (Haiku, GPT-4o-mini):** Time To First Token (TTFT) rất nhanh (1s - 3s).
- **Reasoning Models (Sol Web / `gpt-web-sol`, Codex Terra High, Claude Opus Thinking):** Cần từ **15s – 40s** hoàn toàn im lặng để sinh các thinking/reasoning tokens ngầm trước khi bắt đầu nhả chữ đầu tiên của câu trả lời.
- Sau khi thinking xong, việc streaming câu trả lời chi tiết (400 - 600 từ) qua Server-Sent Events (SSE) tốn thêm **15s – 30s** nữa.

## 2. Bẫy Hard Wall-Clock Timeout (`consult_advisor.py`)
- **Lỗi cũ:** Code sử dụng trần cứng tổng thời gian:
  ```python
  start = time.monotonic()
  for raw_line in resp:
      if time.monotonic() - start > timeout_sec: # 35s hoặc 45s
          raise AdvisorUnavailable("TIMEOUT", ...)
  ```
- **Hậu quả:** Dù model suy luận xong sau 25s và đang tích cực stream từng từ ra màn hình, đến giây thứ 35/45 script vẫn thẳng tay ném lỗi `TIMEOUT >45s` và chém ngang lưng kết nối.
- **Nút thắt trong Hermes Core (`tools/advisor_tool.py`):** `DEFAULT_TIMEOUT` bị kẹp cứng ở mức 15s (`DEFAULT_TIMEOUT = 15`), khiến mọi yêu cầu tư vấn cần suy luận đều bị Hermes cắt ngang trước.

## 3. Kiến trúc Timeout 3 Tầng Chuẩn Xác
Đã triển khai trong `D:/Taadaa/tools/consult_advisor.py` và `D:/Taadaa/Hermes/tools/advisor_tool.py`:
1. **`FIRST_TOKEN_TIMEOUT = 75s` (Thinking Allowance):** Cho phép Sol Web / Terra High tối đa 75 giây để suy luận ngầm và nhả token đầu tiên.
2. **`IDLE_TOKEN_TIMEOUT = 25s` (Stream Keepalive):** Một khi token đầu tiên đã xuất hiện, chuyển sang đo khoảng cách giữa 2 chunk liên tiếp. Chỉ ngắt nếu kết nối bị đơ mạng quá 25s không có chunk mới.
3. **`TOTAL_MAX_TIMEOUT = 120s`:** Trần an toàn tối đa cho toàn bộ phiên tư vấn dài.
4. **Hermes Core Gateway:** Nâng `DEFAULT_TIMEOUT` lên **55s** để không bóp nghẹt tầng upstream.
