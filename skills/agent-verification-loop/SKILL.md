---
name: agent-verification-loop
description: "How to produce fresh, accepted test/lint verification evidence inside a Hermes agent session: the same-turn execution gate, and the pytest.main() deadlock pitfall under subprocess/multiprocessing suites."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, verification, pytest, agent-loop, evidence, harness]
    related_skills: [test-driven-development, systematic-debugging]
---
# Agent Verification Loop

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

How to *run* verification so it counts as evidence inside a Hermes agent session,
distinct from TDD philosophy (which is covered by `test-driven-development`). This
skill is about the mechanics of proving a change works *to the harness that audits
your work*, and the non-obvious failure modes of invoking pytest from within the
agent.

## When this applies

Any time you finish (or incrementally edit) code and must show it passes:
- After a RED→GREEN TDD cycle
- After a bug fix
- Before reporting "done" on a task with a verification gate
- When a system message says your work is `unverified`

## Same-Turn Execution Invariant (Anti-Turn-Ending Freeze)
- **CẤM hứa hẹn tương lai rồi dừng turn**: Kết thúc turn bằng các câu "Em đang chuẩn bị chạy...", "Chờ vài phút để em nghiệm thu..." mà không kèm tool call thực thi ngay sẽ làm phiên đóng băng hoàn toàn (vì runtime hoạt động dạng turn-based, không tự chạy ngầm nếu agent không gọi tool).
- **Hành động tức thì**: Mọi tuyên bố thực thi bắt buộc phải đi kèm lệnh gọi tool (`terminal(background=True)` hoặc `process`) ngay trong cùng lượt phản hồi.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
