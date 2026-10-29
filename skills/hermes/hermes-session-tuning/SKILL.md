---
name: hermes-session-tuning
description: "Chẩn đoán Hermes session lag (context bloat → compression threshold), tinh chỉnh compression, và kiểm tra/ép reasoning_effort khi route qua 9router (deepseek v4)."
---
# Hermes Session Tuning (lag + reasoning qua 9router)

## Trigger
- User kêu Hermes lag / session chậm dù RAM-CPU vẫn còn thừa
- Cần kiểm tra model deepseek đang chạy reasoning nào (THINK:auto vs high vs max trong 9router console log)
- Muốn ép reasoning effort chắc chắn qua 9router
- **Bị ngắt turn giữa chừng do chạm trần tool-calling** — prompt cưỡng chế `You've reached the maximum number of tool-calling iterations allowed...` (xem `references/tool-calling-iteration-limit-and-turn-budget-exhaustion.md`)
- **Session bị reset/đứt ngang 04:00** — banner `◆ Session automatically reset (daily schedule at 4:00). Conversation history cleared. Use /resume to browse and restore a previous session.` (live 2026-08-12 Tiktok Reg group)

## 0. Session reset 4:00 tự động — config `session_reset` (live 2026-08-12)
- `session_reset.mode: both` (mặc định setup wizard) = reset theo CẢ 2: `idle_minutes: 1440` (24h idle) VÀ `at_hour: 4` (reset toàn bộ 04:00 hằng ngày). Hệ quả: mọi group/thread bị gom về session mới lúc 4h sáng, mất context, log `sessions` có `end_reason='session_reset'`.
- **Tắt hẳn**: `hermes config set session_reset.mode none` → config.yaml `session_reset: {mode: none}`. (Chế độ khác: `idle` chỉ idle, `daily` chỉ theo giờ.)
- **Phải restart gateway mới áp dụng** — và `hermes gateway restart` chạy TRONG gateway bị block ("cannot restart ... from inside the gateway process"). Restart từ shell ngoài (desktop terminal / login item) hoặc chờ lần khởi động sau.
- Sau khi bị reset, session cũ vẫn còn trong DB (`hermes sessions list` / `/sessions`) — khôi phục bằng `/resume <session_id>` ngay trong group đó hoặc resume qua routing. Session bị reset có `expiry_finalized=true` trong `gateway_routing` state.db nhưng messages vẫn đọc được.
- Không nhầm cơ chế này với compression fail loop (mục 1b) — đây là reset CHỦ ĐỘNG có banner, không phải nén treo.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
