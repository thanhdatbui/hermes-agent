---
name: hermes-gateway-ops
description: Configure, run, verify, and extend the Hermes messaging gateway (Telegram setup, channel_overrides chat→repo binding, multi-session semantics, Windows install/terminal quirks).
---
# Hermes Gateway Ops

Trigger: set up or operate the messaging gateway (Telegram first), bind a chat/group to a repo via `channel_overrides`, explain multi-session on Telegram, verify a bot is online, or debug gateway config.

- Cronjob LLM Hang vs Anti-Destructive Remediation Invariant (2026-11-03): xem `references/cron-llm-hang-and-anti-destructive-remediation.md`. Xử lý triệt để bẫy cronjob LLM (`no_agent: false`) dính timeout ngậm cứng tool `cronjob` làm gateway treo 60 phút ("No activity for 60 min"); kỷ luật TUYỆT ĐỐI CẤM tự ý xóa cronjob sản xuất (`cronjob action='remove'`), bắt buộc khóa cứng `no_agent: true` trỏ vào script Python nền.
- ChatGPT-Web Cloudflare Turnstile 403: IP/ASN Reputation vs. Token Validity & In-Flight Triage RCA (2026-11-03): xem `references/chatgpt-web-turnstile-ip-reputation-vs-token-validity-rca-20261103.md`. CẤM bảo User bấm /new khi task đang dở (dùng /stop); giải mã vệt TI: 0 | TO: 0 do IP MikroTik dính Sentinel (46% lỗi) chứ không phải do dồn tải; và lỗ hổng probe của cron watchdog chỉ test api/auth/session thay vì chat sentinel.
- Post-Reboot Gateway Freeze & Model Combo Cascading Timeout RCA (2026-11-03): xem `references/host-reboot-gateway-half-open-stall-and-auto-resume-stuck-rca.md`. Sau khi reboot máy, Gateway đã tự khởi động lại theo boot (cấm đoán mò xúi giục restart lại); khoảng mù >10 phút thực chất do Half-Open long-polling socket ngậm TCP hoặc Auto-Resume ngâm tool execution timeout kịch trần (600s); cắt kẹt bằng `/new` hoặc `/reset` thay vì restart mù.
- Post-Reboot Session Freeze Diagnosis vs. Turnstile 403 & Anti-/new Discipline (2026-11-03): xem `references/gateway-post-reboot-freeze-vs-turnstile-discipline.md`. Phân định rõ lỗi config vs độ trễ sau reboot PC; giải mã vệt `TI: 0 | TO: 0` do Turnstile 403 trên OmniRoute Dashboard; kỷ luật TUYỆT ĐỐI CẤM xúi user bấm `/new` khi session đang làm dở dang.
- Context Compression Governance & OmniRoute Frontend Stub Pitfall (2026-11-03): xem `references/context-compression-hermes-vs-omniroute-governance-20261103.md`. Nén ngữ cảnh BẮT BUỘC ở Hermes (cấm chế cháo vào OmniRoute); cảnh báo bẫy `build:backend` làm mất giao diện web; dùng `gemini-web` (Argon 1M) với timeout 300s thay cho Sol Web tránh tràn context 32k/64k; cơ chế tỉa cơ học giữ 100% prompt cache.
- Telegram Gateway Idle Blind Spot vs. OmniRoute 403 Turnstile Burst RCA (2026-11-03): xem `references/telegram-gateway-idle-blind-spot-vs-omniroute-403-turnstile-rca-20261103.md`. Đối soát CSDL `storage.sqlite` bóc trần vệt `TI: 0 | TO: 0` là do ChatGPT Web dính Turnstile Captcha (HTTP 403) kích hoạt combo fallback 8 lần, và khoảng mù 2-3 phút thực chất là IDLE chờ user; phân biệt sự cố mạng thật vs session nghỉ.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
