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
- Channel Isolation Invariant: Báo cáo Feed chỉ về nhóm Tiktok Luot Nuoi Acc (-5377611430); Báo cáo Follow chỉ về nhóm Tiktok Follow (-5127276494); Báo cáo Video chỉ về nhóm Tiktok video (-5435853713). Phân rã tuyệt đối `is_feed_runner_active()`, cấm đưa pattern upload video/avatar vào lock check nuôi feed.
- Group B Quota & Mode 2 Continuity: Trần Nhóm B khóa cứng `cap = min(cap, 20)` (dải random 18-20, max ngày 40). Khi Mode 2 gặp lỗi verify row trên 1 nick con đơn lẻ, BẮT BUỘC skip nick đó và cuộn tiếp, CẤM `break` đánh sập toàn bộ vòng lặp của Anchor khi Anchor còn tài nguyên.
- Triage Skip Follow (Streak Cooldown vs Chưa Đủ 6 Video): Khi đối soát báo cáo follow 0 lượt (như "Bỏ qua: Cooldown nhả follow" vs "Chưa đủ điều kiện"), BẮT BUỘC phân biệt rõ 2 nguyên nhân cốt lõi giữa các cụm:
  * `Cooldown nhả follow` (`follow-released-daily-cooldown`): Thường gặp ở Farm Kibe (nick cũ), do `fail_streak >= 1` lưu tại `D:/Taadaa/tiktok-follow/runs/state/follow_state_{machine}_row_{row}.json` với thang phạt `cooldown_until_date` (Streak 1: 1 ngày, 2: 3 ngày, 3: 5 ngày, >=4: 15 ngày).
  * `Chưa đủ điều kiện` (`under-6-videos-follow-disabled`): Thường gặp ở Farm Admin (nick mới), do `video_count < 6` hoặc tuổi < 21 ngày, bị preflight gate chặn sớm bảo vệ tài khoản, hoàn toàn chưa có state và không phải do streak cooldown.
- Cạm bẫy Logic Streak Cooldown & Lượt Chạy Liên Tiếp:
  * Bẫy Tích Lũy Streak Mù: Khi nick gãy ca mới nhưng giữa 2 ca gãy đã có ca follow thành công (>0 lượt), cấm cộng dồn streak cũ theo `diff_days <= 7`; bắt buộc reset về Streak 1.
  * Bẫy Reset Streak Oan Do Lịch Cách Ngày: Cấm dùng khoảng cách ngày tuyệt đối (`diff_days > 7`) để reset streak của nick bị gãy liên tiếp. Streak phải bám theo chuỗi ca chạy gãy thực tế liên tiếp (consecutive sessions), chi tiết xem `references/follow-fail-streak-logic-traps-and-consecutive-session-invariants.md`.

## References
- Chi tiết toàn bộ quy trình, case study và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
