---
name: advisor-on-demand-governance
description: Use when configuring Advisor Sol. Enforces on-demand only.
---

# Advisor On-Demand Governance

## Core Principle
- **100% STRICTLY ON-DEMAND**: Never guess user intent. Never auto-append Advisor (Sol) responses to chat messages based on heuristic words (e.g., "tư vấn", "lời khuyên", "có nên", "theo mày", "đánh giá", "phân tích giúp") or sentence endings with question marks `?`.
- The user must explicitly summon Advisor Sol by name.

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
