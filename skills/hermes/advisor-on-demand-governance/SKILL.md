---
name: advisor-on-demand-governance
description: Use when configuring Advisor Sol. Enforces on-demand only.
---
# Advisor On-Demand Governance

## Core Principle
- **100% STRICTLY ON-DEMAND**: Never guess user intent. Never auto-append Advisor (Sol) responses to chat messages based on heuristic words (e.g., "tư vấn", "lời khuyên", "có nên", "theo mày", "đánh giá", "phân tích giúp") or sentence endings with question marks `?`.
- The user must explicitly summon Advisor Sol by name.
- **CẤM LỌC TỪNG TỪ (ERADICATE HEURISTIC GATES, DO NOT CHERRY-PICK WORDS)**: Tuyệt đối không tiếp cận theo hướng "xóa từng từ nghi vấn". Tiếng Việt đa dạng, xóa từ này thì câu hỏi kỹ thuật thông thường (ví dụ: *"canary xem cron có fix đc k ?"*) vẫn bị dính do dấu hỏi `?` hoặc cấu trúc nghi vấn. BẮT BUỘC xóa sạch 100% nhánh suy đoán cảm tính trong `_is_advice_request()` và `classify_advice_intent()`, chuyển thành công tắc so khớp cơ học: Chỉ kích hoạt khi chứa đích danh các từ khóa triệu hồi.

## Dual Advisor Architecture (Hội Đồng Cố Vấn: Sol + Claude)
- **Mặc định khi "gọi advisor"**: Hệ thống triệu hồi song song cả 2 cố vấn độc lập qua `consult_advisor.py`:
  1. **🟢 Sol Advisor (:20129 / GPT-5.6)**: Am hiểu sâu về context nghiệp vụ Taadaa Farm, prompt contracts và DAL SQLite.
  2. **🟣 Claude Advisor (Claude Code CLI `claude -p` / Sonnet)**: Phản biện độc lập, săm soi lỗ hổng kiến trúc, rủi ro fail-open, bypass guard, và receipt forge.
- **Thực thi song song (Zero Extra Latency)**: Chạy qua `concurrent.futures.ThreadPoolExecutor(max_workers=2)`. Thời gian phản hồi tổng = `max(latency_sol, latency_claude)` (~3-5 giây).
- **Độ linh hoạt CLI**: Hỗ trợ flag `--advisor {both,sol,claude}` (mặc định: `both`). Tự động failover khi 1 trong 2 con gặp lỗi hoặc timeout.

## Strict Triggers Allowlist
In `agent/conversation_loop.py` and `consult_advisor.py`, `_is_advice_request()` / `classify_advice_intent()` MUST only return `True` for explicit trigger phrases:
```python
_ADVISOR_EXPLICIT_TRIGGERS = (
    "gọi advisor",
    "hỏi sol",
    "gọi sol",
    "hỏi claude",
    "gọi claude",
    "sol thấy sao",
    "nhờ sol review",
    "nhờ claude review",
    "sol lên plan",
    "hội đồng cố vấn",
)
```

## Anti-Glazing & Independent Benchmark Protocol
- **Chống thiên vị nội bộ (Anti-Glazing)**: Khi User đặt nghi vấn Agent đang "nịnh hót", bias về hệ thống hiện tại, hoặc yêu cầu so sánh/phản biện sản phẩm bên ngoài:
  - BẮT BUỘC gọi Advisor độc lập (Claude CLI `claude -p` hoặc Sol) để phân xử.
  - Phân tách rõ ràng các trục so sánh (UX/Consumer vs Industrial Headless, Single-user vs Farm quy mô lớn, Human-in-the-loop vs Mechanical Gates), không đánh đồng hoặc so lệch trục.
  - Chỉ rõ các điểm đối thủ vượt trội hoàn toàn (UX, packaging, third-party integrations) và các điểm yếu/chi phí bảo trì thật của hệ thống hiện tại (overhead từ việc tự đẻ gate/enforcer).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> - `references/advisor-gate-planning-and-gemini-web-quirk.md`: Advisor Gate planning pipeline (Claude CLI/Sol consult before Worker dispatch) & Gemini Web CDP vs Antigravity API tool-calling boundary.
> - `references/openmausbot-vs-hermes-benchmark-and-anti-glazing.md`: Benchmark đối chiếu khách quan OpenMausBot vs Hermes, quy tắc chống thiên vị & bài học kiến trúc đóng gói Playbook.
> - `references/dual-advisor-architecture-sol-and-claude.md`: Kiến trúc Hội Đồng Cố Vấn (Dual Advisor Sol + Claude) chạy song song ThreadPoolExecutor, failover và cờ CLI.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
