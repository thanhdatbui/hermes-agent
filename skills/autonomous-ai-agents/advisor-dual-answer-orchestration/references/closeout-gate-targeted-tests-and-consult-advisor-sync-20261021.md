# Kỹ Thuật Đóng Khung Targeted Test Cho Closeout Gate & Đồng Bộ Consult Advisor (2026-10-21)

## 1. Bối cảnh Phiên Làm Việc (21/10/2026)
Trong phiên giải quyết triệt để lỗi Advisor Sol ngáo do đói ngữ cảnh và bẫy báo lỗi timeout 45s ảo, Operator phát lệnh chốt phiên:
> *"Done"*
Hệ thống kích hoạt quy trình thẩm định độc lập `closeout_gate.py` trên repo `D:/Taadaa/Hermes` và phát hiện 2 nút thắt kỹ thuật quan trọng.

---

## 2. Nút Thắt 1: Bẫy Timeout 120s Khi Chạy Test Toàn Repo & Cấm Tuyệt Đối `--skip-test`

### Hiện tượng:
Khi chạy lệnh thẩm định:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1 --files agent/conversation_loop.py tools/advisor_tool.py --json-output
```
- Lệnh bị treo và văng lỗi sau 120 giây:
  `✘ Tests timeout sau 120s`
  `✘ Focused tests FAILED (0 failed, 1 errors) in 120.0s`
- Nếu thêm `--skip-test` để bỏ qua:
  `✘ [Gate] FATAL: --skip-test is forbidden in repo mode! Closeout Gate requires verified test execution.` (Gate từ chối nghiêm ngặt).

### Nguyên nhân:
- `closeout_gate.py` có cơ chế tự động tìm file test tương ứng từ danh sách `--files`.
- Nếu trong `--files` **chỉ truyền các file mã nguồn** (`agent/conversation_loop.py`, `tools/advisor_tool.py`) mà không có file test nào, logic fallback của gate sẽ chạy lệnh:
  `pytest tests --tb=short -q`
- Trên các repo monolith lớn như Hermes (hàng trăm file test), việc quét và chạy toàn bộ thư mục `tests` vượt quá ngưỡng `PYTEST_TIMEOUT = 120s`.

### Giải pháp chuẩn hóa (Targeted Test Invariant):
Khi chạy `closeout_gate.py` với cờ `--files` trên repo lớn, **BẮT BUỘC kẹp file test focused trực tiếp vào danh sách `--files`**:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1 \
  --files agent/conversation_loop.py tools/advisor_tool.py tests/agent/test_advisor_context.py \
  --json-output
```
- Khi nhận diện có file test trong `--files`, `closeout_gate.py` chuyển ngay sang chế độ focused test:
  `Chạy tests: pytest tests/agent/test_advisor_context.py --tb=short -q`
- Thời gian chạy test giảm từ **>120s (timeout) xuống chỉ còn 1.1s – 3.1s**, pass 100% và chuyển tiếp sang bước AI Review.

---

## 3. Nút Thắt 2: Thiếu Hàm `build_advisor_prompt` trong `D:/Taadaa/tools/consult_advisor.py`

### Hiện tượng:
Test suite `tests/agent/test_advisor_context.py` kiểm tra hàm `test_advanced_review_checks`:
```text
FAILED tests/agent/test_advisor_context.py::test_advanced_review_checks
AttributeError: module 'consult_advisor' has no attribute 'build_advisor_prompt'
```

### Nguyên nhân:
- File `D:/Taadaa/tools/consult_advisor.py` là CLI độc lập dùng cho cả farm, nhưng trước đây chỉ chứa `classify_advice_intent`, `redact_secrets` và `consult_advisor`.
- Module `test_advisor_context.py` import `consult_advisor` và gọi hàm `build_advisor_prompt` để đóng gói prompt 5 tầng. Do thiếu hàm này trên đĩa, test sập ngay lập tức.

### Khắc phục:
Bổ sung hàm chuẩn hóa `build_advisor_prompt` có bọc `redact_secrets` vào `D:/Taadaa/tools/consult_advisor.py`:
```python
def build_advisor_prompt(query: str = "", context: str = "", briefing: str = "", field_ctx: Any = None) -> str:
    """Đóng gói prompt 5 tầng gửi Sol Web có kèm redact_secrets."""
    cleaned_q = redact_secrets(query)
    cleaned_c = redact_secrets(context)
    cleaned_b = redact_secrets(briefing)
    parts = []
    if field_ctx:
        parts.append(f"[BỐI CẢNH HIỆN TRƯỜNG]\n{field_ctx}")
    if cleaned_b:
        parts.append(f"[DIỄN BIẾN GẦN NHẤT]\n{cleaned_b}")
    if cleaned_c:
        parts.append(f"[TRẠNG THÁI HIỆN TẠI]\n{cleaned_c}")
    if cleaned_q:
        parts.append(f"[CÂU HỎI TƯ VẤN]\n{cleaned_q}")
    parts.append("[YÊU CẦU]\nĐóng vai trò Solution Architect phản biện độc lập. Trả lời súc tích, đi thẳng vào nguyên nhân gốc rễ và giải pháp thực tế.")
    return "\n\n".join(parts)
```
Sau khi bổ sung, `pytest tests/agent/test_advisor_context.py` chạy sạch **6/6 passed in 1.13s**.

---

## 4. Phân Định Giới Hạn Dung Lượng: Sol Advisor vs. Sol Reviewer

1. **Sol Advisor (`advisor_tool.py` & `consult_advisor.py`):**
   - Khống chế theo ký tự hội thoại: `MAX_MSG_CHARS = 800`, `MAX_BRIEF_CHARS = 4000`.
   - Timeout: 140s (stream SSE), 80s first-token, 20s idle.
2. **Sol Reviewer (`closeout_gate.py` & `sol_payload_guard.py`):**
   - Giới hạn cứng: `40.000 Bytes (~40 KB)`. Phân bổ I3: 80% diff (~28.8 KB), 10% test log, 10% rubric.
   - Smart Truncator: Giữ file code P0/P1, thu gọn các file ít quan trọng.
   - Không nên nâng trần quá 65 KB vì Web-Pool ChatGPT sẽ bị nghẽn TTFT reasoning kéo dài quá 300s hoặc dính lỗi HTTP 413 Payload Too Large.
