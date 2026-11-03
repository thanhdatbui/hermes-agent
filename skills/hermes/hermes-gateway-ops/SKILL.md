---
name: hermes-gateway-ops
description: Configure, run, verify, and extend the Hermes messaging gateway (Telegram setup, channel_overrides chat→repo binding, multi-session semantics, Windows install/terminal quirks).
---
# Hermes Gateway Ops

Trigger: set up or operate the messaging gateway (Telegram first), bind a chat/group to a repo via `channel_overrides`, explain multi-session on Telegram, verify a bot is online, or debug gateway config.

- Post-Reboot Gateway Freeze & Model Combo Cascading Timeout RCA (2026-11-03): xem `references/host-reboot-gateway-half-open-stall-and-auto-resume-stuck-rca.md`. Sau khi reboot máy, Gateway đã tự khởi động lại theo boot (cấm đoán mò xúi giục restart lại); khoảng mù >10 phút thực chất do Half-Open long-polling socket ngậm TCP hoặc Auto-Resume ngâm tool execution timeout kịch trần (600s); cắt kẹt bằng `/new` hoặc `/reset` thay vì restart mù.
- Context Compression Governance & OmniRoute Frontend Stub Pitfall (2026-11-03): xem `references/context-compression-hermes-vs-omniroute-governance-20261103.md`. Nén ngữ cảnh BẮT BUỘC ở Hermes (cấm chế cháo vào OmniRoute); cảnh báo bẫy `build:backend` làm mất giao diện web; dùng `gemini-web` (Argon 1M) với timeout 300s thay cho Sol Web tránh tràn context 32k/64k; cơ chế tỉa cơ học giữ 100% prompt cache.
- Telegram Gateway Idle Blind Spot vs. OmniRoute 403 Turnstile Burst RCA (2026-11-03): xem `references/telegram-gateway-idle-blind-spot-vs-omniroute-403-turnstile-rca-20261103.md`. Đối soát CSDL `storage.sqlite` bóc trần vệt `TI: 0 | TO: 0` là do ChatGPT Web dính Turnstile Captcha (HTTP 403) kích hoạt combo fallback 8 lần, và khoảng mù 2-3 phút thực chất là IDLE chờ user; phân biệt sự cố mạng thật vs session nghỉ.
- OmniRoute Blind Window & Zero-Token Spike RCA (2026-11-03): xem `references/omniroute-blind-window-zero-token-freeze-rca.md`. Chẩn đoán khoảng mù 2-3+ phút trên OmniRoute và vệt `TI: 0 | TO: 0` do Half-Open socket Long-polling Telegram, backoff retry hoặc tool execution latency.
- Telegram Multi-ISP ReadTimeout Failover & Wedged getUpdates Queue RCA (2026-11-03): xem `references/telegram-polling-readtimeout-retryable-failover-rca-20261103.md`. Khắc phục tử huyệt bỏ sót `httpx.ReadTimeout` trong `_is_retryable_connect_error`, kích hoạt failover tức thì sang Fallback proxy thay vì văng lỗi làm sập updater PTB và kích hoạt án phạt restart 3-5 phút của watchdog.
- Telegram Proxy Flapping & Heartbeat Interval Tuning (2026-11-03): xem `references/telegram-proxy-flapping-and-heartbeat-interval-tuning.md`. Khắc phục flapping WARP ↔ LAN proxy và ép `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=30` chống ngâm silent TCP stall 6-13 phút.
- Gateway In-Process Cron Scheduler Stale sys.executable & [WinError 2] RCA (2026-11-03): xem `references/gateway-cron-stale-sys-executable-winerror-2.md`. Bẫy cron văng WinError 2 khi xóa venv cũ trong khi Gateway cũ vẫn sống trong RAM; phân biệt script missing vs interpreter missing.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
