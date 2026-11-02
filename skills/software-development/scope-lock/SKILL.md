---
name: scope-lock
description: "Use before any task or tool sequence to lock the user's current goal, scope, non-goals, acceptance criteria, and stop condition."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [scope, task-contract, anti-drift, verification, orchestration]
    related_skills: [agent-verification-loop, plan, test-driven-development]
---
# Scope Lock

## Overview

Use this skill before acting on any non-trivial request, especially repository,
automation, debugging, testing, deployment, or delegated work. Its purpose is
to prevent **scope drift**: turning a narrow request into a larger plan because
an old plan, test failure, worker handoff, or adjacent route is visible.

This is a coordination gate, not permission to edit anything. The latest
explicit user request remains authoritative.

## Task contract

Create a compact contract before the first state-changing action:

```text
Goal:              the single outcome the user asked for
In scope:          exact repo/worktree/files/routes/devices/operations allowed
Non-goals:         adjacent files/routes/operations that must remain untouched
Acceptance:        observable conditions proving the goal is met
Stop condition:    when acceptance passes, stop; do not continue by curiosity
```

Keep the allowlist concrete. “Recovery” or “the repo” is not an allowlist;
name the actual route, file, worktree, or operation. If the request is clear,
derive the contract narrowly instead of asking the user to repeat it.

## Authority and stale context

1. The latest user message wins over older plans, summaries, TODOs, handoffs,
   delegated-worker prompts, and compressed context.
2. A plan describes possible work; it does not authorize every phase. Adopt only
   the phases and paths covered by the current contract.
3. A discovered dependency or failing adjacent test is not automatically in
   scope. Record it as `OUT_OF_SCOPE` or `NEEDS_USER_DECISION`.
4. Do not treat “make it robust,” “full suite,” or “audit everything” as
   permission unless the user actually requested that breadth.
5. **Cross-Session Context Bleed Guard (KỶ LUẬT CHỐNG RÒ RỈ NGỮ CẢNH):**
   - Khi phiên chat có khối tóm tắt `[CONTEXT COMPACTION — REFERENCE ONLY]` hoặc kết quả subagent/tiến trình ngầm trả về, CẤM TUYỆT ĐỐI tự ý lôi các sự cố, câu hỏi, hoặc chủ đề của các phiên cũ (ví dụ: nick bị ban, lỗi 413, audit trước đó) vào trả lời nếu người dùng KHÔNG HỀ hỏi tới trong lượt hiện tại.
   - Việc trả lời vượt ngoài prompt đang hoạt động bị người dùng coi là "trả lời nhầm session" hoặc nói nhảm.
   - BẮT BUỘC neo câu trả lời 100% vào đúng câu hỏi ở tin nhắn mới nhất của người dùng. Mọi context thừa từ khối tóm tắt chỉ dùng để tra cứu ngầm (read-only), không được chủ động phát tán ra câu trả lời.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
