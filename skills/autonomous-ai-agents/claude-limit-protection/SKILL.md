---
name: claude-limit-protection
description: "Enforce Claude CLI usage limits: block at 85% of 5h session limit and 90% of weekly quota. Mirrors Codex limit protection rules."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Claude, CLI, Limit-Protection, Quota, Safety]
    related_skills: [claude-code, codex, agent-model-routing]
---
# Claude CLI Limit Protection Rule

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## Overview
Prevent Claude Code CLI usage when approaching Anthropic API limits to avoid session disruption and quota exhaustion. Mirrors existing Codex limit rules.

## Limit Thresholds

| Limit Type | Threshold | Action |
|------------|-----------|--------|
| **5-hour session window** | 85% (4h 15m) | **BLOCK** new Claude CLI tasks |
| **Weekly quota** | 90% | **BLOCK** new Claude CLI tasks |
| **Warning zone** | 70% 5h / 80% weekly | Log warning, allow with caution |

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
