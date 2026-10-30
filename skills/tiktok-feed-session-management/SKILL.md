---
name: tiktok-feed-session-management
description: Skills for managing TikTok feed session, tab distribution, watchdog reporting, and farm sync operations
platforms: [windows, linux]
tags: [tiktok, feed-session, watchdog, farm-automation, tab-switching]
version: 1.0.0
author: Hermes Agent
---
## Non-negotiable Operating Rules
- Watchdog Follow Report: BẮT BUỘC hiển thị `{len(rel_...)} máy` kèm % và list máy (vd: `- Nhả liền (23 máy | 0 lượt | 92.0%): (M3, ...)`).
- Anchor & Fallback Invariant: CẤM TUYỆT ĐỐI bịa đặt giả thuyết "hết nick nội bộ làm anchor". Hệ thống luôn đủ nick và follow engine luôn có cơ chế auto-fallback sang Mode 1 khi cần. Máy báo 0 follow mà status OK là do Dual Gate (video < 10 cấp budget = 0) hoặc cơ chế PROBATION_SINGLE_SESSION_LOCK (nick probation chỉ được follow 1 phiên/ngày, đã dùng budget ở phiên trước thì phiên sau cấp budget = 0).

## References
- Follow Anchor Invariants, Dual Gate Budget & UNPROVEN Triage: `references/follow-anchor-invariants-dual-gate-and-unproven-triage.md`
- Phân Biệt Feed Swipe vs Follow Hook & Khóa Cữ Probation: `references/probation-single-session-lock-and-feed-vs-follow-distinction-20261030.md`
- Probation Single Session Lock & Daily Budget Cap: `references/probation-single-session-lock-and-daily-budget-cap.md`
- Khóa Đơn Phiên Hồi Phục & Bù Lượt Khi Dính Preflight: `references/probation-single-session-lock-and-preflight-reschedule.md`
- Sụp Socket ADB giữa phiên & Silent Launcher Crash Triage: `references/mid-session-adb-socket-drop-and-silent-launcher-crash-triage.md`
- Chi tiết toàn bộ quy trình, case study và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
