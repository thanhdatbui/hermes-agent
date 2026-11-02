---
name: hermes-gateway-ops
description: Configure, run, verify, and extend the Hermes messaging gateway (Telegram setup, channel_overrides chat→repo binding, multi-session semantics, Windows install/terminal quirks).
---
# Hermes Gateway Ops

Trigger: set up or operate the messaging gateway (Telegram first), bind a chat/group to a repo via `channel_overrides`, explain multi-session on Telegram, verify a bot is online, or debug gateway config.

- Fallback Provider Exhaustion & Multimodal Payload Desync Trap (2026-11-02): xem `references/fallback-provider-exhaustion-and-multimodal-desync.md`. Nguyên nhân văng 'The model provider failed after retries' trên session nặng ảnh do fallback trỏ vào model non-vision (9r-free) và model dính 429 (opencode-free).
- Gateway Venv Migration SSL & Stale Launcher Pitfall (2026-11-03): xem `references/gateway-venv-migration-ssl-and-launcher-audit.md`. Đối soát triệt để khi đổi venv: kill process cũ để nhả `SSL_CERT_FILE` và quét cập nhật các shortcut/launcher Desktop còn trỏ venv cũ.
- Single-Message Topic Stale Routing & Runtime Desync RCA (2026-11-02): Khi topic Telegram mới tinh gửi 1 tin nhắn kèm ảnh mà văng 'The model provider failed after retries', nguyên nhân gốc rễ là bẫy `was_auto_reset: true` với `auto_reset_reason: resume_pending_expired` từ nhịp restart dở dang kết hợp desync `hermes_dev.pth` (D: vs C:) làm kẹt stream socket. Khắc phục tức thời bằng `/new` hoặc `/reset` dọn sạch binding.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- Gateway Crash Loop via hermes_dev.pth Sys.path Desync & Hotfix (2026-11-02): xem `references/gateway-crashloop-pth-desync-rca-20261102.md`. CẤM restart Gateway khi chưa dry-run import kiểm tra `atomic_write_text`, `config.py` và các module core ở `D:\Taadaa\Hermes`.
- Gateway Runtime Dual-Tree Pitfalls (hermes_dev.pth & Watchdog Spawn): xem `references/gateway-dual-tree-pth-desync-pitfalls.md`. Cấm restart mù khi tồn tại 2 bản code D: và C:; kiểm tra import offline trước khi restart tránh crash loop.
- Gateway Runtime Desync & Multimodal supports_vision Overrides (2026-11-02): xem `references/gateway-runtime-desync-and-multimodal-supports-vision-override-20261102.md`. Sửa core phải sync sang `%LOCALAPPDATA%\hermes\hermes-agent\`; model custom bắt buộc `supports_vision: true` để không bị strip ảnh sang auxiliary error.
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
