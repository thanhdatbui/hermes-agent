# Quy Tắc Điều Kiện Follow Tự Nhiên Khi Lướt Feed & Xử Lý Popup Gợi Ý

## 1. Bối cảnh & Nguyên nhân lỗi (Incident Case 2026-10-07)
Khi bot lướt nuôi acc (`tiktok-luot nuoi acc`), có 2 luồng phát sinh hành vi bấm follow tự nhiên ngoài luồng Follow Hook:
1. **Thẻ đề xuất tài khoản trên Feed (`feed_swipe_smoke.py` -> `follow_back_suggestion`):** Xuất hiện nút "Follow lại" / "Theo dõi lại" kèm nút "Không quan tâm".
2. **Popup Gợi ý bạn bè / Gợi ý follow (`benign_popup.py` -> `dismiss_follow_friends_suggestion_popup`):** Popup modal hiện danh sách người quen/bạn bè với nút "Follow lại" / "Follow".

Trước đây, các handler này chỉ kiểm tra sơ sài `is_account_in_follow_cooldown(ctx)` (kiểm tra xem nick có đang bị phạt nhả hay không) mà **KHÔNG kiểm tra điều kiện Dual Gate (tuổi nick, số lượng video, ngày dưỡng sinh)**. Dẫn đến việc các máy Farm Admin hoặc nick non (< 10 video, < 30 ngày) dù bị chặn Follow Hook 100% nhưng khi lướt feed vẫn bị handler popup bấm follow dạo.

## 2. Quy Tắc Phân Quyền Follow Tự Nhiên (Dual Gate Invariant)
**CẤM TUYỆT ĐỐI** tắt cứng follow tự nhiên của toàn bộ farm, nhưng cũng **CẤM** cho nick non / nick dưỡng sinh bấm follow dạo.

Phải sử dụng hàm chuẩn `is_account_eligible_for_follow(ctx)`:

### Tiêu chí ĐỦ ĐIỀU KIỆN (Eligible):
- Tuổi nick $\ge$ 30 ngày (`_account_age_days >= 30`).
- Số lượng video đã đăng $\ge$ 10 clip (`_video_count >= 10`).
- Không nằm trong ngày nghỉ dưỡng sinh (`_is_organic_rest == False` và `rest_day_no_follow == False`).
- Không bị phạt cooldown / nhả follow từ các phiên trước (`_follow_cooldown == False` và follow state file sạch).

### Hành vi chuẩn theo phân nhánh:
| Luồng | Nick ĐỦ điều kiện (Eligible) | Nick CHƯA ĐỦ điều kiện / Nick non / Dưỡng sinh |
| :--- | :--- | :--- |
| **Thẻ đề xuất Feed (`follow_back_suggestion`)** | Tap nút "Follow lại" (detector node) để tăng trust tự nhiên | Tap nút "Không quan tâm" (`id/cv6`) để ẩn thẻ an toàn |
| **Popup Gợi ý bạn bè (`dismiss_follow_friends_suggestion_popup`)** | Cho phép follow 1–2 người (`follow_limit = 2`), sau đó đóng popup | Đặt `follow_limit = 0`, tuyệt đối không tap follow, chỉ tìm nút X / Back để đóng popup |
| **Lướt Video FYP (`_maybe_follow_video`)** | Tỷ lệ ngẫu nhiên 2%–5% khi Deep Inspect | Bị chặn `skipped` ngay từ đầu |
