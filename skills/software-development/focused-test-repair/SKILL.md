---
name: focused-test-repair
description: "Use when focused tests are malformed. Repair and verify."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [pytest, test-repair, structural-repair, payloads, verification]
    related_skills: [systematic-debugging, agent-verification-loop, verification-evidence]
---
# Focused Test Repair and Verification

## Purpose

Repair narrowly scoped Python production/test changes without broad refactors,
then prove the final live bytes with the user's exact verification commands. This
skill is for malformed focused tests, duplicate test definitions, orphaned test
bodies, and contract changes where an old size-limit rejection must become a
large-payload send-through regression.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
