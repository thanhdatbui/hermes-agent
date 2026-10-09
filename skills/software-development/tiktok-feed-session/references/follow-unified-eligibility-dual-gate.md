# Thống Nhất Điều Kiện Follow Farm (Single Source of Truth - Dual Gate)

## Bối cảnh & Nguyên lý (Chốt ngày 02/10/2026)
Trước đây tồn tại sự lệch pha giữa 2 repo:
- `tiktok-follow` (Follow chéo): Áp dụng Dual Gate (video >= 6 VÀ tuổi nick >= 21 ngày). Nick < 21 ngày tuổi bị set `budget = 0`.
- `tiktok-luot nuoi acc` (Lướt feed): Chỉ kiểm tra `video_count >= 6` mà không kiểm tra tuổi nick.

Hậu quả: Nick mới tạo (ví dụ 16 ngày tuổi, 6 video) khi lướt feed vẫn bị roll trúng 5% follow tự nhiên và bấm nút trên tab Đề xuất. Nhưng vì nick chưa đủ 21 ngày ngâm, TikTok shadow-revert/hủy toàn bộ follow này, dẫn đến khi watchdog đối soát TikTok Web thì số following không tăng (lệch -3, -1) và nick lọt vào báo cáo gây nhiễu.

User chỉ đạo: **Follow tự nhiên bắt buộc phải tuân theo 100% cơ chế của Follow chéo. Chéo bị cooldown thì tự nhiên cũng cooldown; chéo chưa đủ điều kiện thì tự nhiên cũng chưa đủ điều kiện.**

---

## 4 Điều Kiện Bắt Buộc Để Được Phép Follow (Cả Tự Nhiên & Chéo)
Một tài khoản CHỈ ĐƯỢC PHÉP follow khi thỏa mãn TOÀN BỘ 4 điều kiện sau:
1. **Không phải ngày Dưỡng sinh (Organic Rest day):** Tài khoản trong ngày dưỡng sinh chỉ lướt feed giải trí, 0 follow, 0 upload.
2. **Không bị Cooldown do nhả follow:** `is_account_in_follow_cooldown(ctx) == False` (đọc file state `follow_state_{machine}_row_{row}.json`).
3. **Số video đã đăng >= 6 video:** Nick < 6 video chưa đủ trust để đi follow.
4. **Tuổi tài khoản >= 21 ngày:** Tính từ cột `Ngày Tạo` (`created_date`) trong safe workbook. Nếu workbook thiếu cột ngày tạo thì yêu cầu tối thiểu 10 video.

---

## Cơ Chế Thực Thi Trong Code

1. **`feed_session_workbook.py`**:
   - Quét cột `Ngày Tạo` qua `DATE_COLUMNS = ("ngay tao", "ngày tạo", "created at", "created_at", "ngay", "date")`.
   - Tính toán `account_age_days = (today - created_date).days` và gán vào `MachineAccount`.

2. **`multi_machine_feed_session.py`**:
   - Khi chuẩn bị child context (`_run_child`): Nếu nick dính dưỡng sinh, `< 6` video, hoặc `< 21` ngày tuổi -> lập tức set `_follow_rate = {"for_you": 0, "following": 0, "friends": 0}`.
   - Khi chạy hook follow chéo (`_run_follow_hook`): Bỏ qua sớm ngay từ đầu nếu `< 21` ngày tuổi với reason `under-21-days-follow-disabled` (không gọi subprocess tốn tài nguyên).

3. **`feed_swipe_smoke.py`**:
   - Trong `_maybe_follow_video`: Kiểm tra `_account_age_days < 21` bên cạnh `video_count < 6` và cooldown check. Bỏ qua hoàn toàn hành động bấm nút follow.

4. **`feed_session_watchdog.py`**:
   - Gom các lý do `under-21-days`, `under-6-videos` vào danh mục `Chưa đủ điều kiện`.
   - Lọc bỏ (ẩn) các nick có `diff == 0` (KHỚP) khỏi chi tiết đối soát TikTok Web để báo cáo tập trung vào các nick thực sự có lỗi hoặc lệch.
