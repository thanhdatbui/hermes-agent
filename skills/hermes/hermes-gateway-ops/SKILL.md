---
name: hermes-gateway-ops
description: Configure, run, verify, and extend the Hermes messaging gateway (Telegram setup, channel_overrides chat→repo binding, multi-session semantics, Windows install/terminal quirks).
---
# Hermes Gateway Ops

Trigger: set up or operate the messaging gateway (Telegram first), bind a chat/group to a repo via `channel_overrides`, explain multi-session on Telegram, verify a bot is online, or debug gateway config.

- Telegram Proxy Flapping & Heartbeat Interval Tuning (2026-11-03): xem `references/telegram-proxy-flapping-and-heartbeat-interval-tuning.md`. Khắc phục flapping WARP ↔ LAN proxy và ép `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=30` chống ngâm silent TCP stall 6-13 phút.
- Gateway In-Process Cron Scheduler Stale sys.executable & [WinError 2] RCA (2026-11-03): xem `references/gateway-cron-stale-sys-executable-winerror-2.md`. Bẫy cron văng WinError 2 khi xóa venv cũ trong khi Gateway cũ vẫn sống trong RAM; phân biệt script missing vs interpreter missing.
- Native Vision vs Browser Vision & Windows Atomic Replace Resilience (2026-11-03): xem `references/native-vision-vs-browser-vision-and-windows-atomic-replace.md`. Cấm dùng browser_vision đối phó khi model có Native Multimodal; xử lý WinError 5 trong atomic_replace và kỷ luật Scope không lôi session khác vào.
- Fallback Provider Exhaustion & Multimodal Payload Desync Trap (2026-11-02): xem `references/fallback-provider-exhaustion-and-multimodal-desync.md`. Nguyên nhân văng 'The model provider failed after retries' trên session nặng ảnh do fallback trỏ vào model non-vision (9r-free) và model dính 429 (opencode-free).
- Gateway Venv Migration SSL & Stale Launcher Pitfall (2026-11-03): xem `references/gateway-venv-migration-ssl-and-launcher-audit.md`. Đối soát triệt để khi đổi venv: kill process cũ để nhả `SSL_CERT_FILE` và quét cập nhật các shortcut/launcher Desktop còn trỏ venv cũ.
- Single-Message Topic Stale Routing & Runtime Desync RCA (2026-11-02): Khi topic Telegram mới tinh gửi 1 tin nhắn kèm ảnh mà văng 'The model provider failed after retries', nguyên nhân gốc rễ là bẫy `was_auto_reset: true` với `auto_reset_reason: resume_pending_expired` từ nhịp restart dở dang kết hợp desync `hermes_dev.pth` (D: vs C:) làm kẹt stream socket. Khắc phục tức thời bằng `/new` hoặc `/reset` dọn sạch binding.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- Gateway Crash Loop via hermes_dev.pth Sys.path Desync & Hotfix (2026-11-02): xem `references/gateway-crashloop-pth-desync-rca-20261102.md`. CẤM restart Gateway khi chưa dry-run import kiểm tra `atomic_write_text`, `config.py` và các module core ở `D:\Taadaa\Hermes`.
- Gateway Runtime Dual-Tree Pitfalls (hermes_dev.pth & Watchdog Spawn): xem `references/gateway-dual-tree-pth-desync-pitfalls.md`. Cấm restart mù khi tồn tại 2 bản code D: và C:; kiểm tra import offline trước khi restart tránh crash loop.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
