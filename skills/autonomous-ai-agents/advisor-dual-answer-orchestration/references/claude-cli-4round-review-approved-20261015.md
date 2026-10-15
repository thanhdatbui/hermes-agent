# Claude CLI 4-Round Review Approved & Production Hardening (15/10/2026)

Tài liệu này ghi lại toàn bộ hành trình review mã nguồn 4 vòng với Claude Code CLI (Sonnet 5.5) cho tính năng **Session Context Enrichment (Bơm Ngữ Cảnh Phiên cho Advisor Sol)** đạt chứng chỉ **APPROVED** chính thức.

---

## 1. Hành trình 4 Vòng Review với Claude CLI

- **Vòng 1 (REJECTED):**
  * *Phát hiện:* Lỗi cú pháp `(?i)` nằm giữa regex pattern làm `consult_advisor.py` crash ngay khi import trên Python 3.11+.
  * *Thiếu sót:* Chưa có early redaction trong `advisor_context.py`, cắt chuỗi thô bạo làm mất câu hỏi của Operator.
- **Vòng 2 (REJECTED):**
  * *Phát hiện:* Lọt secret trong Dict key có tiền tố (`MY_API_KEY`, `GITHUB_TOKEN`) do dùng exact match `_SECRET_KEYS`.
  * *Lọt JSON quoted:* `{"password": "...", "cookie": "..."}` không bị che vì dấu nháy kép bao quanh key.
  * *Lọt Authorization:* `Authorization: Basic ...` chỉ che từ Basic, credential nguyên vẹn.
- **Vòng 3 (REJECTED có điều kiện):**
  * *Phát hiện:* `_SERIAL_RE` nhận nhầm chuỗi trạng thái ADB (`device unauthorized`, `device offline`, `connection lost`) làm serial thiết bị.
  * *Lọt Cookie:* `Cookie: a=1; b=2; c=3` chỉ che `a=1` do `[^\s,;]+` ngắt ngay tại dấu chấm phẩy.
  * *Cắt trước khi che:* `current_state[:1000]` và `query[:1500]` cắt ngang lưng token `sk-` khiến regex không nhận diện được.
  * *False-positive:* Substring match trên dict key xóa nhầm `tokens_used: 150` thành `[REDACTED]`.
- **Vòng 4 (APPROVED):**
  * Toàn bộ 5 ca kiểm thử nâng cao được giải quyết và kiểm chứng bằng test suite: **31/31 unit tests PASSED**.
  * Claude Sonnet 5.5 ra phán quyết chính thức: **APPROVED**.

---

## 2. Các Bài Học & Chuẩn Hóa Kỹ Thuật Bắt Buộc

### A. Phân loại Secret Key trong Dict (`_is_secret_key`)
Không dùng substring match đơn giản `sk in key` vì sẽ làm vạ lây các trường telemetry thông dụng như `tokens_used`, `prompt_tokens`, `total_tokens`, `author`.
```python
def _is_secret_key(k: str) -> bool:
    norm = re.sub(r"[-_]", "", str(k).lower())
    if any(sk in norm for sk in _SECRET_KEYS if sk != "token"):
        return True
    return norm == "token" or (norm.endswith("token") and not norm.endswith("tokens"))
```

### B. Ngăn Chặn Lọt Secret Tại Ranh Giới Cắt Chuỗi (Redact Before Truncate)
Tuyệt đối không cắt ngắn văn bản trước khi chạy bộ lọc regex. Secret bị cắt cụt một nửa sẽ không còn khớp pattern và sẽ lọt ra ngoài upstream.
```python
# ĐÚNG:
state_clean = redact_secrets(current_state)[:1000] if current_state else ""
query_clean = redact_secrets(query)[:1500]

# SAI:
state_str = f"[Trạng thái]\n{current_state[:1000]}"
query_str = f"[Câu hỏi]\n{query[:1500]}"
full = redact_secrets(state_str + query_str)  # Lọt nếu secret nằm ở ký tự 995-1015!
```

### C. Regex Serial Tránh Bắt Nhầm Log Lỗi ADB
Serial của thiết bị Android phải có ít nhất 1 chữ số. Sử dụng lookahead `(?=[a-zA-Z0-9]*\d)` để phân biệt serial thật (`9885e64c484c544d32`, `R58N12ABCDE`) với các thông báo lỗi thuần chữ (`unauthorized`, `offline`, `connection`):
```python
_SERIAL_RE = re.compile(r"(?:serial|thiết bị|device)\s*[:=]?\s*(?=[a-zA-Z0-9]*\d)([a-zA-Z0-9]{8,24})\b", re.IGNORECASE)
```

### D. Che Giấu Cookie Toàn Dòng
Cookie trong các session TikTok/GPM thường phân tách bằng `; ` chứa nhiều token quan trọng (`sessionid`, `sid_tt`). Bộ lọc cookie bắt buộc phải nuốt toàn bộ dòng:
```python
_COOKIE_RE = re.compile(r"(?i)\bcookie\s*[:=]\s*[^\r\n]+")
```

---

## 3. Kỷ Luật Giao Tiếp Telegram Khi Chạy Review Loop Tự Động
- Khi điều phối các subagent chạy ngầm kết hợp kiểm thử với Claude CLI, Coordinator **tuyệt đối không được xuất các câu lẩm bẩm debug, trích đoạn guard warning, hay log kỹ thuật thô vào tin nhắn chat Telegram**.
- Operator cần kết quả rõ ràng, súc tích và minh bạch. Báo cáo tiến độ theo hướng outcome-first: "Đang sửa điểm X -> Đang chạy review vòng Y -> Kết quả APPROVED".
