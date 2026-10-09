# Case Feed-Follow-Unified-Gate: Hợp Nhất Dual Gate Follow Chéo & Follow Tự Nhiên (2026-10-02)

## 1. Ngữ cảnh & Triệu chứng lỗi
- Trong phiên nuôi feed (Ca 4 - Phiên Đêm), báo cáo tổng kết watchdog hiển thị:
  - `Follow tự nhiên: 7 lượt / 1333 video (0.5%)`
  - `Đối soát TikTok Web (+0 Following thật | Lệch -4 so với script báo 4)`: M19 báo 0 (khớp), M51 báo 3 (lệch -3), M63 báo 1 (lệch -1).
  - Trong khi đó `Follow chéo (0 lượt follow)`: 73 máy bị skip (21 dưỡng sinh, 48 chưa đủ 6 video, 4 "Khác").
- User bức xúc vì sao follow chéo không máy nào đủ điều kiện mà follow tự nhiên vẫn roll follow trên feed, và tại sao report lại in cả nick khớp 100% không lệch.

## 2. Root Cause Analysis
1. **Lệch pha Dual Gate giữa 2 repo:**
   - Repo `tiktok-follow` có Dual Gate (25/09): Yêu cầu CẢ HAI điều kiện `video_count >= 6` VÀ `account_age_days >= 21`.
   - Các nick Row 8 (M51, M56, M59, M63, M77) tạo ngày 15/09 - 16/09/2026, tại thời điểm chạy (02/10/2026) mới 16-17 ngày tuổi (< 21 ngày).
   - Khi follow chéo chạy, `FollowState.session_budget` trả về `budget = 0` -> Cả Module 2 và Module 1 đều nhận budget 0 và dừng ngay lập tức.
   - Nhưng bên `feed_swipe_smoke.py` và `multi_machine_feed_session.py`, cơ chế check gate follow tự nhiên lúc lướt feed chỉ kiểm tra `video_count >= 6` mà KHÔNG kiểm tra `account_age_days >= 21`.
   - Kết quả: Khi lướt feed, nick 16 ngày tuổi vẫn roll 5% follow tự nhiên và bấm nút trên feed, nhưng server TikTok shadow-revert hoặc không ghi nhận khiến web đối soát +0 và gây ra lệch số.

2. **Cạm bẫy đọc tag chẩn đoán (Anti-Pattern):**
   - Chuỗi `"mode2_zero_following_fix": "zero-following-skip-v2"` trong `follow_result.json` chỉ là tên version tag gắn tĩnh vào metadata của result.
   - Tuyệt đối KHÔNG được suy diễn nhầm rằng "anchor có 0 following / rỗng list" để giải thích sai lệch cho User. Anchor Tik1/Tik2 của farm luôn có đầy đủ following.

3. **Nguyên tắc Single Source of Truth (User chốt):**
   - Follow tự nhiên khi lướt feed PHẢI tuân thủ 100% cùng một bộ điều kiện với Follow chéo:
     + Cooldown do nhả follow (giam cả chéo lẫn tự nhiên).
     + Ngày nghỉ dưỡng sinh (Organic rest: 0 follow).
     + Số video đã đăng (`video_count >= 6`).
     + Tuổi nick (`account_age_days >= 21`).
   - Bất kỳ điều kiện nào không đạt -> Tắt hoàn toàn tỷ lệ follow tự nhiên (`_follow_rate = 0`).

4. **Kỷ luật Watchdog Report Đối soát Web:**
   - Trong mục "Đối soát TikTok Web", chỉ in chi tiết các nick THỰC SỰ LỆCH (`diff != 0`) hoặc UNPROVEN / lỗi snapshot.
   - Các nick khớp 100% (`diff == 0`, chênh lệch +0) BẮT BUỘC ẩn khỏi danh sách chi tiết để tránh làm loãng report của User.
