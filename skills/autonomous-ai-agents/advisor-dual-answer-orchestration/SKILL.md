---
name: advisor-dual-answer-orchestration
description: "Use when the operator explicitly requests Advisor Sol review or an architecture second opinion."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [advisor, orchestration, dual-answer, canary, intent-routing, sol]
    related_skills: [hermes-agent, verification-evidence, agent-review-loops]
---
# Advisor Dual-Answer Orchestration

Use this skill when the operator explicitly asks for Advisor Sol review, a second opinion, or an architecture plan. The required behavior is not merely exposing an `advisor_consult` tool: preserve a read-only Advisor path with explicit operator control and a focused context briefing.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
