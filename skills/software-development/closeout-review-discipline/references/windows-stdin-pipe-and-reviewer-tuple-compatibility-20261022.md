# Windows Stdin Pipe for Unbounded Reviewer Diff & Tuple Compatibility (2026-10-22)

## 1. Giới hạn Windows 32KB Cmdline & Kỹ thuật Stdin Pipe (`claude -p -`)

Khi triển khai Claude Sonnet CLI làm Primary Reviewer để đọc 100% diff và test log mà không bị cắt tỉa bởi trần 37KB (`sol_payload_guard.py`):
- **Bẫy Windows `CreateProcessW` Limit:** Trên hệ điều hành Windows, độ dài chuỗi tham số dòng lệnh bị giới hạn cứng ở **32.767 ký tự** (~32KB). Nếu gom `system_prompt` + `diff_text` (test + code) + `test_evidence_text` vượt quá 32KB và truyền trực tiếp qua argument `cmd = ["claude", "-p", full_prompt, ...]` sẽ kích hoạt lỗi `WindowsError: [Error 206] The filename or extension is too long` hoặc `command too long`.
- **Giải pháp Stdin Pipe Chuẩn:** Claude Code CLI hỗ trợ đọc prompt trực tiếp từ standard input thông qua cú pháp `-p -`:
  ```python
  cmd = [
      "claude",
      "-p", "-",
      "--model", "sonnet",
      "--effort", "high",
      "--no-session-persistence",
      "--disable-slash-commands",
      "--max-turns", "1",
      "--disallowedTools", "Edit,Write,NotebookEdit",
      "--dangerously-skip-permissions",
  ]
  proc = subprocess.run(
      cmd,
      input=full_prompt,
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      timeout=timeout,
  )
  ```
  Kỹ thuật này cho phép gửi payload ngữ cảnh lên tới 200KB - 500KB mà không bị giới hạn bởi shell/OS buffer.

---

## 2. Bẫy Tương Thích Ngược Unpack Tuple Reviewer (`client.review()`)

- **Bối cảnh:** Các phiên bản hiện đại của `OmniRouteClient.review()` trả về 4-tuple:
  ```python
  (verdict, scorecard, content, meta)
  ```
  Trong khi đó, nhiều bộ test hồi quy cũ (như `test_closeout_gate_scorecard.py::test_telemetry_model_locked_fields`) sử dụng `DummyClient` mô phỏng trả về 3-tuple legacy:
  ```python
  return "APPROVED", {"overall_score": 95}, "ok"
  ```
- **Triệu chứng lỗi:** Khi chạy kiểm thử hồi quy, lệnh unpack tĩnh `verdict, scorecard, content, meta = client.review(...)` văng lỗi:
  ```text
  ValueError: not enough values to unpack (expected 4, got 3)
  ```
- **Giải pháp Phòng vệ:** BẮT BUỘC kiểm tra độ dài tuple trước khi giải nén:
  ```python
  res_review = client.review(...)
  if isinstance(res_review, tuple) and len(res_review) == 3:
      verdict, scorecard, content = res_review
      meta = {}
  else:
      verdict, scorecard, content, meta = res_review
  ```

---

## 3. Bài Học Chống Ngộ Nhận Danh Tính Model ChatGPT Web Free

- **Hiện tượng:** Web Free của OpenAI giấu nút chọn model, tự động map các request `model: "auto"` sang cụm Luna Free (`gpt-5-6`).
- Khi client bắn ép slug suy luận `gpt-5-6-thinking` kèm `thinking_effort: "extended"` trên một tài khoản Free, server OpenAI trả về chuỗi suy luận bình thường. Tuy nhiên, backend OpenAI hoàn toàn có thể điều hướng ngầm (internal routing / downscale) sang cụm compute của Luna CoT thay vì Sol xịn.
- **Kỷ luật Điều phối:** Không được suy diễn hoặc khẳng định chủ quan về danh tính model sau bức tường server của OpenAI nếu không có telemetry/metadata chính thống từ hãng. Đối với các tác vụ giám định khắt khe (Reviewer, Architect), ưu tiên sử dụng Claude Sonnet CLI có identity và rubric rõ ràng thay vì phụ thuộc vào pool Web Free.
