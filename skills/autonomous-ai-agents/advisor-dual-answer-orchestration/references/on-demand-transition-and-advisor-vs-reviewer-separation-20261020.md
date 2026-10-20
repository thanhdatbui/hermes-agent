# Chuyển Đổi Sang On-Demand & Phân Định Rạch Ròi Sol Advisor vs. Sol Reviewer (2026-10-20)

## 1. Bối Cảnh & Phản Hồi Từ Operator
- **Hiện tượng:** Operator phàn nàn:
  > *"Nên tiếp tục xài guard advisor không, nó cứ thiếu ngữ cảnh nói chuyện như ngáo ngáo vậy? Hay là khi cần tao mới chat gọi"*
  > *"Với lại tao thấy session khác nó vừa báo sol advisor mọi câu hỏi và đều quá 45s"*
- **Triệu chứng cụ thể:**
  1. Auto-append tự động chèn đuôi `--- Advisor (Sol / review) ---` sau mỗi câu chat thường có từ *"nên"*, *"được không"*. Do ChatGPT-Web pool (:20129) là stateless, Sol bị đói context (Context Starvation), dẫn đến phán đoán lệch lạc, đòi Operator phải gửi lại đoạn chat với Claude.
  2. Bị ngộ nhận lỗi timeout 45s liên tục: Khi Sol trả về text Markdown thuần thay vì JSON hợp lệ, `_first_json_object` trong `advisor_tool.py` ném lỗi parse JSON ở giây thứ 23, nhưng Agent nhìn nhầm cờ unavailable và quy chụp là *"quá 45s"*.

---

## 2. Quyết Định Kiến Trúc: Chuyển Dứt Điểm Sang On-Demand (100%)

### A. Vô hiệu hóa Auto-append trên Conversation Loop
Trong `Hermes/agent/conversation_loop.py`, hàm `_is_advice_request()` đã được chuẩn hóa lại:
- **CẤM:** Không tự động bắt các câu chat thường chứa *"tư vấn"*, *"lời khuyên"*, *"có nên"*, *"được không"*, *"sao vậy"*.
- **CHỈ BẮT:** Các từ khóa chỉ định đích danh từ Operator:
  ```python
  _ADVISOR_EXPLICIT_TRIGGERS = (
      "gọi advisor", "hỏi sol", "gọi sol",
      "sol thấy sao", "nhờ sol review", "sol lên plan"
  )
  ```

### B. Nâng trần Bối cảnh cho Lệnh On-Demand (`advisor_context.py`)
Khi Operator chủ động gọi, Sol cần nhận đầy đủ chi tiết hiện trường:
- `MAX_MSG_CHARS`: Nâng từ `280` lên **`800` ký tự/turn** (giữ trọn vẹn chi tiết kỹ thuật).
- `MAX_BRIEF_CHARS`: Nâng từ `1.500` lên **`4.000` ký tự** (chứa 3–5 turn đối thoại sâu mà không bị cắt xén).

### C. Nâng Cấp Streaming SSE & Keepalive (`advisor_tool.py`)
- Chuyển `payload["stream"] = True` thay vì `False`.
- Xử lý dòng stream qua `_read_stream_content`:
  - `FIRST_TOKEN_TIMEOUT = 80s` (cho phép Sol Web suy luận ngầm TTFT mà không bị chém ngang).
  - `IDLE_TOKEN_TIMEOUT = 20s` (reset timer liên tục mỗi khi nhận thêm chunk text).
  - `DEFAULT_TIMEOUT = 140s` (trần an toàn tối đa).

---

## 3. Bản Đồ Phân Định Rạch Ròi: Sol Advisor vs. Sol Reviewer

Tuyệt đối không nhầm lẫn giữa 2 thực thể này trên hệ thống:

| Đặc tính | **Sol Advisor (Tư vấn kiến trúc)** | **Sol Reviewer (Chấm điểm Closeout Gate)** |
| :--- | :--- | :--- |
| **Vai trò** | Đàm đạo, phản biện giải pháp, gợi ý kiến trúc | Quan tòa độc lập thẩm định chất lượng code & diff |
| **File thực thi** | `Hermes/tools/advisor_tool.py` & `consult_advisor.py` | `D:/Taadaa/tools/closeout_gate.py` & `sol_payload_guard.py` |
| **Đầu vào** | Câu hỏi của Operator + Session Briefing Pack | `git diff HEAD~1` + Focused Pytest Output |
| **Đầu ra** | Markdown phân tích đa chiều | JSON bắt buộc: `overall_score`, `verdict`, `findings` |
| **Giới hạn trần** | 4.000 ký tự briefing text | 40.000 Bytes UTF-8 (80% diff, 10% test log, 10% rubric) |
| **Thời điểm kích hoạt** | **On-Demand:** Chỉ khi Operator gọi từ khóa rõ ràng | **Closeout:** Khi Operator phát lệnh chốt phiên |
| **Timeout trần** | 140s stream keepalive | 300s (`REVIEWER_TIMEOUT`) |

---

## 4. Cảnh Báo Bẫy Phân Tích Lỗi (Anti-Hallucination Pitfall)
Khi thấy `Advisor: unavailable`:
- BẮT BUỘC kiểm tra trường `error` và `latency_ms` trong telemetry.
- CẤM vội vã kết luận là "bị quá 45s" nếu log chỉ ra lỗi là do parse JSON (`response content did not contain a JSON object`) hoặc do pool exhaustion (429/All targets skipped).
