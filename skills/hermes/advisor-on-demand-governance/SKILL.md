---
name: advisor-on-demand-governance
description: Use when configuring Advisor Sol. Enforces on-demand only.
---

# Advisor On-Demand Governance

## Core Principle
- **100% STRICTLY ON-DEMAND**: Never guess user intent. Never auto-append Advisor (Sol) responses to chat messages based on heuristic words (e.g., "tư vấn", "lời khuyên", "có nên", "theo mày", "đánh giá", "phân tích giúp") or sentence endings with question marks `?`.
- The user must explicitly summon Advisor Sol by name.
- **CẤM LỌC TỪNG TỪ (ERADICATE HEURISTIC GATES, DO NOT CHERRY-PICK WORDS)**: Tuyệt đối không tiếp cận theo hướng "xóa từng từ nghi vấn". Tiếng Việt đa dạng, xóa từ này thì câu hỏi kỹ thuật thông thường (ví dụ: *"canary xem cron có fix đc k ?"*) vẫn bị dính do dấu hỏi `?` hoặc cấu trúc nghi vấn. BẮT BUỘC xóa sạch 100% nhánh suy đoán cảm tính trong `_is_advice_request()` và `classify_advice_intent()`, chuyển thành công tắc so khớp cơ học: Chỉ kích hoạt khi chứa đích danh các từ khóa triệu hồi.

## Strict Triggers Allowlist
In `agent/conversation_loop.py`, `_is_advice_request()` MUST only return `True` for explicit trigger phrases:
```python
_ADVISOR_EXPLICIT_TRIGGERS = (
    "gọi advisor",
    "hỏi sol",
    "gọi sol",
    "sol thấy sao",
    "nhờ sol review",
    "sol lên plan",
)
```

## Anti-Pattern / Pitfalls
- **Post-Turn Dual-Answer Leak (`consult_advisor.py`)**: Even when conversation loop has advisor disabled, post-turn checks invoke `consult_advisor.py:ensure_dual_answer()`. If `classify_advice_intent()` contains legacy regexes matching generic phrases (like `có nên`, `thế nào`, `sao v`, `nghĩ sao`, `tại sao`), it will silently call Sol in the background and append `--- Advisor (Sol / review) ---` to normal operator chat! Ensure `consult_advisor.py` strictly restricts `explicit_patterns` to explicit keywords (`gọi sol`, `hỏi sol`, `kêu sol`, `advisor`, `sol review`, etc.) and sets `generic_patterns = []`.
- **Heuristic Pattern Trap**: Do NOT match generic question markers like `has_phrase("nên") and "?" in text`. That causes normal coordinator inquiries (e.g. "canary xem cron có fix đc k ?") to trigger Advisor Sol unexpectedly, causing latency and frustrating the operator.
- **Masked Key Testing in OmniRoute Pools**: When validating connections under OmniRoute (:20129), do NOT send masked keys (`__Secure****` or `eyJhbG****`) to external endpoints or `/api/providers/validate`. Always use the internal testing endpoint:
  ```http
  POST http://127.0.0.1:20129/api/providers/{connection_id}/test
  ```
  to obtain the live, unmasked validity status.
- **Database vs In-Memory State**: When updating provider connection status in OmniRoute, modifying SQLite directly (`~/.omniroute/storage.sqlite`) does not immediately update the running in-memory cache. Use the REST API:
  ```http
  PUT http://127.0.0.1:20129/api/providers/{connection_id}
  Content-Type: application/json

  {"isActive": true, "testStatus": "active"}
  ```
- **ChatGPT Account Deactivation vs. Gmail Liveness**:
  Khi tài khoản ChatGPT-Web báo lỗi `ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`:
  * Tuyệt đối không phán đoán bừa rằng Gmail bị DIE. Phải kiểm tra độc lập qua `checkmail.live` và đăng nhập Google Account.
  * Nếu Google đăng nhập thành công nhưng khi Google SSO vào ChatGPT bị báo `Lỗi xác thực: account_deactivated` ("Bạn không còn tài khoản vì tài khoản đã xóa hoặc vô hiệu hóa"), điều này khẳng định Gmail hoàn toàn LIVE nhưng tài khoản dịch vụ ChatGPT đã bị OpenAI trảm. Không tiếp tục giải Captcha hay ép login lại tốn tài nguyên; đánh dấu loại khỏi pool ChatGPT và thay thế bằng tài khoản khác.

## Worker & Subagent Dispatch Protocol (Coordinator vs Worker)
- **CẤM TUYỆT ĐỐI Hermes Native Delegation (`delegate_task`)**:
  Coordinator tuyệt đối không được gọi `delegate_task` để spawn subagent bừa bãi. Việc spawn subagent tự do gây bloat context, ngâm timeout 600s làm nghẽn event loop của gateway, vi phạm sandbox và phá vỡ kiểm soát phân vai của farm.
- **Quy chuẩn ủy quyền Worker (Farm Worker CLI)**:
  Khi cần thực hiện các task sửa code / điều tra sâu vượt quá ngân sách Coordinator O(1):
  * **First Responder:** BẮT BUỘC dispatch qua `python D:/Taadaa/tools/sol_worker.py "<contract O(1)>" --workdir <repo>` (hoặc chỉ định `--model`, `--timeout`).
  * **Fallback:** Sử dụng `python D:/Taadaa/tools/dispatch_worker.py` (hoặc `claude_worker.py` / `haiku_worker.py`).
  * Coordinator giữ vai trò nghiệm thu O(1) qua focused test và canary thực tế; cấm spawn subagent mò mẫm file.

