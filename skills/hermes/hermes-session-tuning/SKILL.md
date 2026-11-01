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
- **Tái phình to Context do SKILL.md Re-bloat** — các file SKILL.md bị agent nhồi nhét tài liệu/references cũ phình to >100KB, hoặc agent gọi đọc file con `references/...` làm phình context lên 250.000 tokens (xem `references/skill-re-bloat-and-automated-pruning-governance.md`)
- **Ảo giác báo cáo láo do nén context quá sớm & phá vỡ Prompt Cache** — nén ở 0.3/protect_last_n 20 làm Agent mất ngữ cảnh nhiệm vụ dở dang, dẫn đến completion bias và báo cáo sai sự thật; chuẩn hóa nâng lên threshold 0.60 / protect_last_n 50 (xem `references/context-compression-drift-and-prompt-caching-tuning-20261101.md` và `references/prompt-caching-and-compression-threshold-tuning.md`)
- **Nạp Cấu Hình Gateway Mới Bằng Runner Tách Rời (Detached Restart)** — Sửa file config chỉ ghi xuống đĩa; tiến trình Gateway đang chạy cần restart detached để RAM cập nhật compressor mới mà không bị đứt kết nối hay mất session.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
