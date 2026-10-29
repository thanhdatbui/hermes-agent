---
name: hermes-gateway-ops
description: Configure, run, verify, and extend the Hermes messaging gateway (Telegram setup, channel_overrides chat→repo binding, multi-session semantics, Windows install/terminal quirks).
---
# Hermes Gateway Ops

Trigger: set up or operate the messaging gateway (Telegram first), bind a chat/group to a repo via `channel_overrides`, explain multi-session on Telegram, verify a bot is online, or debug gateway config.

- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- Đảm bảo bảo toàn Auto-Resume khi restart Gateway và kỷ luật chống khóc lóc/bại liệt: xem `references/delayed-restart-auto-resume-and-anti-whining.md`.

## CLI commands

```bash
hermes gateway setup          # wizard interactive — chọn platform, nhập token/user ID, tự ghi config, offer start/restart
hermes gateway                # chạy foreground (WSL/Docker/Termux khuyên dùng foreground)
hermes gateway start|stop|restart|status
hermes gateway install [--start-now] [--start-on-login] [--system] [--force]
hermes gateway list           # trạng thái tất cả profiles
hermes gateway enroll         # relay connector (experimental)
```

Gateway = **1 background process** chạy TẤT CẢ platform đã cấu hình cùng lúc + cron scheduler (tick 60s) + session store per chat + voice (STT/TTS). Token/secret → `.env`, KHÔNG bao giờ vào config.yaml; behavioral settings → config.yaml.

For the reusable producer→delivery→Telegram audit and the distinction between logical session splits, transport chunks, and target fan-out, see `references/delivery-layer-per-session.md`. Bots cần model provider + tool providers (TTS, web). Token lộ → BotFather `/revoke`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
