# Closeout Gate Payload Stream: False & Cases Rebase Reorder Protocol (2026-09-14)

## 1. Bẫy JSONDecodeError / Extra Data Khi Gọi Reviewer Qua Proxy OpenAI-Compatible (:20128 / :20129)
- **Hiện tượng:**
  Khi `closeout_gate.py` gửi diff lên 9Router (:20128) hoặc OmniRoute (:20129) với endpoint `/v1/chat/completions`, client bị crash với lỗi:
  `[OmniRouteClient] Attempt 1/3 failed: Extra data: line 1 column 8764 (char 8763)` hoặc `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.
- **Nguyên nhân:**
  Trong payload mặc định của `OmniRouteClient._build_payload()`, nếu không khai báo rõ ràng `"stream": False`, một số proxy LLM (như 9Router / OmniRoute hoặc các model reasoning như Claude Opus Thinking / Nemotron Ultra) mặc định trả về Server-Sent Events (SSE chunked stream với prefix `data: {"id": ...}`).
  Khi `requests.post()` nhận phản hồi SSE nhưng lại gọi `resp.json()`, parser JSON của Python chỉ đọc được chunk đầu tiên và quăng ngoại lệ `Extra data` do còn nhiều chunk `data: ...` phía sau.
- **Quy chuẩn bắt buộc:**
  Trong `_build_payload()` của client review, BẮT BUỘC phải truyền rõ ràng:
  ```python
  def _build_payload(self, messages: list[dict], model: str = "review") -> dict:
      return {
          "model": model,
          "messages": messages,
          "temperature": 0.0,
          "max_tokens": 4096,
          "stream": False,  # BẮT BUỘC: Ngăn proxy trả về SSE chunked stream
      }
  ```

---

## 2. Quy Trình Xử Lý Xung Đột Số Case (Rebase Reorder) Trong `docs/farm-automation-cases.md`
- **Hiện tượng:**
  Khi cả local và upstream remote cùng thêm một Case mới độc lập với cùng số thứ tự (ví dụ: remote đã merge commit thêm `Case REG-16` từ máy khác, trong khi local của phiên hiện tại cũng vừa ghi nhận `Case REG-16`).
  Khi chạy `git pull --rebase origin <branch>`, Git báo conflict:
  `CONFLICT (content): Merge conflict in docs/farm-automation-cases.md`.
- **Quy trình giải quyết chuẩn:**
  1. Mở diff xung đột, giữ nguyên toàn bộ nội dung của Case phía remote (HEAD upstream).
  2. Tịnh tiến số Case của local lên +1 (ví dụ đổi local từ `Case REG-16` thành `Case REG-17`).
  3. Cập nhật separator `---` và checklist ở cuối file cho đồng nhất.
  4. Đánh dấu resolved bằng `git add docs/farm-automation-cases.md`.
  5. Tiếp tục rebase bằng lệnh có cờ chống interactive freeze:
     `GIT_EDITOR=true git rebase --continue`
  6. Sau khi rebase hoàn tất, chạy lại syntax check (`python -m py_compile`) và verify `git log -n 3` để đảm bảo thứ tự Case tăng dần liên tục, không bị nhảy cóc hoặc trùng số.
