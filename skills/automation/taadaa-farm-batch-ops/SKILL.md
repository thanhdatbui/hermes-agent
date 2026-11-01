---
name: taadaa-farm-batch-ops
description: "Re-run / resume farm batch jobs (TikTok upload, Tik3 render, reg, nuoi acc) using canonical commands."
version: 1.0.0
author: Hermes Agent
tags: [tiktok, farm, batch, render, upload, resume, kibe]
---
# Taadaa Farm Batch Operations

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
- `references/cooldown-nurture-and-shift-cycle-completion.md`: Quy chuẩn nick cooldown vẫn được nuôi dưỡng sinh bình thường nhưng bỏ qua follow; nuôi xong tính hoàn thành chu kỳ để xoay tua Row ngày hôm sau.
- `references/shift-pool-feed-vs-follow-hook-cycle-trap.md`: Cơ chế phân tách Nuôi Feed (parent) vs Follow-hook (child). Bẫy kẹt vòng lặp bốc nick lặp lại do follow skipped không kích hoạt cycle advance.
- `references/dynamic-shift-pool-cooldown-deadlock-trap.md`: Bẫy kẹt vòng lặp bốc nick lặp lại ngày hôm sau do follow bị skip bởi cooldown nhưng không được đánh dấu hoàn thành chu kỳ.
- `references/follow-streak-cooldown-calendar-boundary-and-preflight-gate.md`: Phân biệt Streak Cooldown boundary theo ngày lịch vs Preflight Gate (<6 video). Tra cứu O(1) kho video Admin.
- `references/flop-channel-detection-and-source-rotation-pipeline.md`: Quy chuẩn phát hiện kênh flop 0 view, thứ tự dọn render trước rồi dọn raw, thống kê niche hot trên mẫu toàn diện 1.272 acc thay vì mẫu nhỏ lẻ.
