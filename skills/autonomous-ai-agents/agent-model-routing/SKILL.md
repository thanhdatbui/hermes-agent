---
name: agent-model-routing
description: "Route coordinator and worker agents by task difficulty and cost."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [agents, orchestration, model-routing, delegation, cost]
    category: autonomous-ai-agents
    related_skills: [hermes-agent, codex, opencode]
---
# Agent Model Routing Skill

Use this skill when one agent coordinates work while another model or coding CLI performs implementation. It defines routing by role, difficulty, quota, and verification needs. It does not prescribe a permanent ranking for models; provider catalogs and model IDs change, so verify the live catalog before configuring.

> **Canonical policy precedence:** For orchestration and closeout policy, follow `D:\Taadaa\HERMES_SUBAGENT_RULES.md` marker `CANONICAL-POLICY-PRECEDENCE-2026-10-05`; this routing skill points to it and must not redefine it.


### Wrapper bắt buộc: `claude_worker.py` (Kẹp turns & Quota gate)
- Chi tiết đối soát thực chiến Sol vs Gemini vs Codex Luna: xem `references/sol-worker-vs-gemini-farm-benchmark.md`.
Mọi lượt gọi Claude CLI bắt buộc đi qua `D:/Taadaa/tools/claude_worker.py` (hoặc `haiku_worker.py` tương thích ngược):
- `--role worker` (Haiku 5.5, max 15 turns): Thợ gõ code O(1),

### Emergency Fallback Worker: `sol_worker.py` (Zero-Cost ChatGPT Web Pool via :20129)
Khi cả Claude CLI và Agy CLI đều chạm trần Quota (5h/weekly), kích hoạt `D:/Taadaa/tools/sol_worker.py`:
- **Model:** `gpt-web-sol` qua OmniRoute (`http://127.0.0.1:20129/v1/chat/completions`), tận dụng pool ChatGPT Web tự xoay tua tài khoản.
- **Local ReAct State Machine:** Lưu lịch sử hội thoại 100% tại local, chịu lỗi tốt khi pool đổi session giữa các tài khoản web khác nhau.
- **Tolerant Tool DSL:** Sử dụng block DSL (`ACTION: READ_FILE`, `ACTION: PATCH`, `ACTION: COMMAND`, `ACTION: DONE`, `ACTION: BLOCKED`), triệt tiêu hoàn toàn lỗi vỡ JSON khi streaming dài.
- **Cưỡng chế Test Verification trước DONE:** Bắt buộc có `ACTION: COMMAND` kiểm thử thành công trước khi cho phép `ACTION: DONE`. Mọi thao tác `PATCH` mới đều tự động reset `has_verified = False`.
- **Sandbox An Toàn:** Chặn toàn bộ shell injection (`shell=False`, cấm `;`, `&`, `|`, `$`, `<>`), khóa chặt allowlist test runners (`pytest`, `python -m pytest`, `python -m unittest`). Ghi patch atomic bằng file tạm kèm `os.fsync`, read-back verification và auto-rollback nếu lỗi.
- **Quy tắc phân vai:** Worker chạy xong CHỈ xuất báo cáo diff và test evidence, TUYỆT ĐỐI không tự ý commit hay chốt phiên.
 tool Read/Edit/Write/Bash.
- `--role planner` (Sonnet 5.5, max 10 turns): Lên bản vẽ kiến trúc, tool Read/Bash (cấm Edit/Write).
- `--role reviewer` (Sonnet 5.5, max 8 turns): Soi lỗi, chấm điểm nghiệm thu, tool Read/Bash (cấm Edit/Write).
- **CẤM TUYỆT ĐỐI** gọi raw CLI `claude -p` không có wrapper: Một session trước đã thả rông Sonnet không kẹp max-turns, chạy 72 turns đốt 2.1M tokens (98% quota).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
