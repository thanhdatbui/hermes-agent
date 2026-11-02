---
name: hermes-gateway-remote-control
description: "Set up and operate the Hermes messaging gateway (Telegram first) for remote control: bot setup, per-chat repo binding via channel_overrides, session semantics, and verification."
version: 1.0.0
author: Hermes Agent
tags: [hermes, gateway, telegram, remote-control, channel-overrides, sessions]
---
# Hermes Gateway Remote Control

Operate Hermes from Telegram (or other messaging platforms) on the user's Windows farm machine. Covers: first-time gateway setup, per-chat/per-group repo binding (`channel_overrides`), session semantics (context storage, `/new` vs `/resume` vs `/background`, threads/topics), reporting discipline, and evidence-based verification.

**Environment facts (Kibe machine):** HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes` (NOT `~/.hermes`). Gateway runs as its own process; desktop app + gateway are two views into the SAME HERMES_HOME (config.yaml, .env, state.db, sessions/, skills/, memory). Telegram is a thin adapter — no separate config namespace.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
