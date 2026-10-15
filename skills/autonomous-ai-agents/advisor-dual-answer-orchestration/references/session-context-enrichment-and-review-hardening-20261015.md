# Session Context Enrichment & Advisor Hardening (15/10/2026)

## Bối cảnh & Mục tiêu
Khi Operator hỏi tư vấn ("Sao lại thế?", "Có nên tăng cooldown?"), Advisor Sol (`gpt-web-sol` qua port 20129) là stateless HTTP pool, không có lịch sử hội thoại. Nếu chỉ gửi tin nhắn cuối cùng, Sol sẽ bị "Context Starvation" (đói ngữ cảnh), suy diễn chung chung và trả lời cụt lủn, lệch khỏi hiện trường máy/nick thực tế.

Hệ thống đã triển khai giải pháp Context Injection: tự động trích xuất hiện trường (`field_context`), tóm tắt 3-5 lượt đối thoại gần nhất (`session_briefing`) và đóng gói thành prompt 5 tầng gửi Advisor.

---

## 5 Bẫy Kỹ Thuật & Bài Học Đắt Giá Được Reviewer Nghiệm Thu

### 1. Bẫy False-Positive Khi Redact Dict Key (`tokens_used`, `total_tokens`)
- **Triệu chứng:** Khi đổi từ exact match `in _SECRET_KEYS` sang substring match `any(sk in norm for sk in _SECRET_KEYS)`, chuỗi `'token'` nằm trong `'tokens_used'` hoặc `'prompt_tokens'` khiến telemetry số liệu token bị xóa thành `[REDACTED]`.
- **Giải pháp chuẩn hóa:**
  ```python
  def _is_secret_key(k: str) -> bool:
      norm = re.sub(r"[-_]", "", str(k).lower())
      if any(sk in norm for sk in _SECRET_KEYS if sk != "token"):
          return True
      return norm == "token" or (norm.endswith("token") and not norm.endswith("tokens"))
  ```
  Quy tắc: Các key kết thúc bằng `tokens` (như `tokens_used`, `totaltokens`) không bị che; chỉ che key là `token` trần hoặc kết thúc bằng `token` (như `access_token`, `github_token`).

---

### 2. Bẫy Cắt Xén Trước Redaction (Truncation Before Redaction)
- **Triệu chứng:** Cắt chuỗi `current_state[:1000]` hoặc `query[:1500]` TRƯỚC KHI gọi `redact_secrets` sẽ chém ngang một secret (ví dụ: `sk-12345` bị cắt ở vị trí ký tự thứ 10), làm chuỗi còn lại không đủ độ dài match regex `sk-[A-Za-z0-9_-]{16,}` -> Secret bị lọt nguyên văn lên upstream.
- **Giải pháp:** BẮT BUỘC redact trước, cắt sau:
  ```python
  state_clean = redact_secrets(current_state)[:1000] if current_state else ""
  query_clean = redact_secrets(query)[:1500]
  ```

---

### 3. Bẫy Bắt Nhầm Serial Từ Log Lỗi ADB (`device unauthorized`, `connection lost`)
- **Triệu chứng:** Khi duyệt messages từ dưới lên để tìm serial máy, regex bắt `device\s*[:=]?\s*([a-zA-Z0-9]+)` sẽ khớp nhầm các từ trạng thái trong log ADB như `adb: device unauthorized` hoặc `device connection lost` -> gán `serial: 'unauthorized'`.
- **Giải pháp:** Bắt buộc dùng positive lookahead yêu cầu serial phải chứa ít nhất một chữ số:
  ```python
  _SERIAL_RE = re.compile(r"(?:serial|thiết bị|device)\s*[:=]?\s*(?=[a-zA-Z0-9]*\d)([a-zA-Z0-9]{8,24})\b", re.IGNORECASE)
  ```
  Nhận diện tốt serial alphanumeric (`R58N12ABCDE`, `9885e64c484c544d32`) nhưng loại bỏ 100% từ trạng thái tiếng Anh (`unauthorized`, `offline`, `connection`).

---

### 4. Bẫy Cookie Phân Tách Dấu Chấm Phẩy (Semicolon Multi-value)
- **Triệu chứng:** Pattern key-value thông thường dùng `[^\s,;]+` chỉ che được cặp cookie đầu tiên (`Cookie: a=1; b=2; c=3` -> `Cookie: [REDACTED]; b=2; c=3`), làm lộ toàn bộ token phiên `sid_tt`, `sessionid` phía sau.
- **Giải pháp:** Pattern cookie phải che toàn bộ dòng cho tới ký tự xuống dòng:
  ```python
  _COOKIE_RE = re.compile(r"(?i)\bcookie\s*[:=]\s*[^\r\n]+")
  ```

---

### 5. Lỗi Cú Pháp Regex Flag `(?i)` Trên Python 3.11+
- **Triệu chứng:** Đặt inline flag `(?i)` ở giữa biểu thức alternation (ví dụ `r"sk-...|(?i)\bbearer..."`) làm Python 3.11+ ném ngoại lệ `re.error: global flags not at the start of the expression at position ...` ngay khi import module.
- **Giải pháp:** Tách các pattern nhạy cảm hoa thường thành danh sách `_SECRET_PATTERNS`, chỉ áp dụng `re.IGNORECASE` ở compile-time cho các pattern thực sự cần thiết.
