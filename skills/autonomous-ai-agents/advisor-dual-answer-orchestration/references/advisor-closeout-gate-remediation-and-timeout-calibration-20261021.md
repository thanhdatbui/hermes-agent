# Hiệu Chuẩn Timeout & Schema Remediation Cho Advisor Sol Khi Chốt Phiên (2026-10-21)

## 1. Bối cảnh & Hiện trường
Trong phiên làm việc ngày 21/10/2026, Operator yêu cầu khắc phục triệt để lỗi Advisor Sol bị timeout ảo 45s và chuyển sang On-Demand. Sau khi triển khai, bước Closeout Gate (`closeout_gate.py`) liên tục trượt với điểm 65 -> 77 -> 78/100 (Threshold 85, Grace 80) do Sol Reviewer khắt khe ở các khía cạnh:
1. Tăng `DEFAULT_TIMEOUT` từ 55s lên 140s trong `advisor_tool.py`.
2. Thiếu deadline validation sau khi `resp.read()` đọc toàn bộ buffer.
3. Schema validation của Advisor response quá lỏng hoặc quá cứng.
4. Test trong repo phụ thuộc vào đường dẫn tuyệt đối ngoài repo (`D:/Taadaa/tools`).

---

## 2. Các Bài Học & Giải Pháp Đã Nghiệm Thu (APPROVED 82/100)

### Bài học 1: Phân định ranh giới timeout giữa Core Tool (`advisor_tool.py`) vs CLI (`consult_advisor.py`)
- **Sai lầm:** Nâng đồng loạt `DEFAULT_TIMEOUT = 140s` trong cả `advisor_tool.py`. Sol Reviewer phạt nặng vì tăng nguy cơ conversation loop bị treo cứng 2.5 phút nếu upstream rớt mạng, gây nghẽn phiên chat.
- **Giải pháp đúng:**
  * `consult_advisor.py` (CLI / On-Demand độc lập): Cho phép `first_token_timeout = 80s`, `idle_token_timeout = 20s`, `max_total_timeout = 140s`, và ThreadPool deadline 150s.
  * `advisor_tool.py` (gọi bên trong luồng conversation loop): Giữ nguyên trần `DEFAULT_TIMEOUT = 55s` để bảo vệ độ trễ hội thoại.
  * Khi hạ lại `DEFAULT_TIMEOUT = 55s`, điểm reviewer tăng vọt vì chứng minh được tính an toàn tài nguyên.

### Bài học 2: Kiểm tra Deadline 2 Tầng Trong `_read_content`
- **Vấn đề:** Khi dùng `resp.read()`, socket timeout chỉ giới hạn thời gian chờ dữ liệu đầu, không giới hạn tổng thời gian đọc nếu server nhả từng byte cực chậm.
- **Giải pháp:**
  ```python
  def _read_content(resp, t0, total_timeout):
      if hasattr(resp, "read"):
          raw = resp.read()
          # Bắt buộc kiểm tra deadline ngay sau khi đọc buffer
          if time.monotonic() - t0 >= total_timeout:
              raise TimeoutError("Advisor stream timeout exceeded")
          ...
  ```

### Bài học 3: Schema Validation Linh Hoạt Với Fallback Keys
- **Vấn đề:** Ép Sol phải trả về chính xác key `recommendation`. Nếu Sol trả về `advice`, `plan` hay `review`, hệ thống ném `ValueError` làm gãy response. Ngược lại, nếu không validate thì dễ lọt response rỗng.
- **Giải pháp:**
  ```python
  rec = advice.get("recommendation")
  if not isinstance(rec, str) or not rec.strip():
      for alt in ("advice", "plan", "review"):
          if isinstance(advice.get(alt), str) and advice[alt].strip():
              rec = advice[alt]
              break
  if not isinstance(rec, str) or not rec.strip():
      raise ValueError("advisor response is missing non-empty recommendation")
  advice["recommendation"] = rec.strip()
  if "reasoning" in advice and not isinstance(advice["reasoning"], str):
      advice["reasoning"] = str(advice["reasoning"])
  if "plan" in advice and not isinstance(advice["plan"], list):
      advice["plan"] = [str(advice["plan"])]
  ```

### Bài học 4: Độc Lập Môi Trường Cho Test Suite (Anti-Hardcoded Path)
- **Vấn đề:** Test `test_advanced_review_checks` chèn `sys.path.insert(0, "D:/Taadaa/tools")` để import `consult_advisor`. Reviewer đánh giá đây là "code smell" làm giảm tính tái lập trên CI/Linux và làm ô nhiễm `sys.path` toàn cục.
- **Giải pháp:** Bỏ import chéo; test trực tiếp các hàm nội tại của repo (`redact_secrets`, `infer_field_ctx`, `_read_content`). Bổ sung mock test kiểm tra timeout, malformed JSON và SSE streaming đầy đủ.
