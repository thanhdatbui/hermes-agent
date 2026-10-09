# Daily Cooldown & Consecutive Run Backoff Rules (Follow Drop)

## 1. Bối cảnh & Điểm yếu của cơ chế cũ (48h cứng theo giờ)

Trước đây, khi nick bị TikTok nhả follow (Follow Drop), hệ thống set cooldown cứng 48 giờ (`now + 48h`):
- **Vấn đề lệch ca:** Nếu nick bị nhả lúc 10h sáng ngày 1, cooldown kéo dài đến đúng 10h sáng ngày 3. Do farm chạy theo cữ cách nhật (ngày 1 -> ngày 3), các phiên sáng sớm (06:00, 08:00) của ngày 3 bị preflight gate chặn oan, làm mất cơ hội follow buổi sáng của nick.
- **Preflight check nghẽn:** Preflight check ở `multi_machine_feed_session.py` từng check `state_data.get("follow_failed") and state_data.get("budget_date") == today_str`, dẫn đến việc khóa toàn bộ các phiên còn lại trong ngày dù đã qua mốc cooldown.

## 2. Quy tắc Cooldown mới (Daily Cooldown + Consecutive Run Backoff)

### BẤT BIẾN QUAN TRỌNG: STREAK TÍNH THEO NGÀY (KHÔNG TÍNH THEO PHIÊN)
- **Tuyệt đối không tăng Streak theo từng phiên trong ngày:** Nếu một tài khoản chạy qua Phiên 1 (sáng), Phiên 2 (trưa), Phiên 3 (tối) trong cùng một ngày và đều gặp lỗi nhả follow, cơ chế `last_failed_date == today` đảm bảo **Streak vẫn giữ nguyên là 1** cho toàn bộ ngày hôm đó.
- **Chỉ tăng Streak khi sang cữ ngày chạy hôm sau (`diff_days >= 1`):** Phải đến cữ chạy của ngày tiếp theo (sau 2 ngày) mà tài khoản tiếp tục bị nhả follow thì `Streak` mới nhảy lên 2.

### Quy tắc theo chu kỳ chạy cách nhật:
1. **Streak = 1 (Lần đầu bị nhả trong ngày):**
   - Dừng follow tất cả các phiên còn lại của **ngày hôm đó** (cooldown đến `23:59:59` giờ local).
   - Nick vẫn tham gia lướt feed và up video (phiên 3) bình thường.
   - Đến **cữ chạy tiếp theo (2 ngày sau)**: Tự động reset và mở follow 100% ngay từ Phiên 1 sáng.
2. **Streak = 2 (2 cữ chạy liên tiếp đều dính nhả follow):**
   - Xác định nick bị TikTok theo dõi/gắn cờ rate limit liên tục qua 2 ngày chạy.
   - Kích hoạt cooldown dài **4 ngày (+4 ngày)** để nick nghỉ trọn vẹn 1 chu kỳ chạy phục hồi trust score.
3. **Streak >= 3 (Bị nhả >=3 cữ liên tiếp):**
   - Cooldown dài **7 ngày (+7 ngày / 1 tuần)**.
4. **Follow thành công:**
   - Ngay khi nick thực hiện 1 lượt follow thành công trên thiết bị, `FollowState.mark(uid, "followed")` tự động reset `fail_streak = 0`, xóa bỏ toàn bộ cờ `follow_failed` và `cooldown_until_at`.

## 3. Gating đồng bộ giữa 2 Repo

- **Trong `tiktok-follow` (`FollowState`):**
  - `set_follow_failed()` tính toán `cooldown_until_at` (UTC ISO) và `cooldown_until_date` (Local YYYY-MM-DD).
  - Đối chiếu khoảng cách ngày giữa `today` và `last_failed_date`: nếu nằm trong grace window của cữ chạy (`diff_days <= prior_cd + 4 ngày`), tăng `streak = min(10, curr_streak + 1)`. Nếu cách xa hơn (đã nghỉ lâu), reset `streak = 1`.
  - Quản lý idempotency: duplicate callbacks trong cùng ngày hoặc khi đang trong active cooldown không làm nhảy sai streak.

- **Trong `tiktok-luot nuoi acc` (`multi_machine_feed_session.py`):**
  - Preflight gate đọc trực tiếp `cooldown_until_at` và so sánh với `now_utc`.
  - Nếu `now_utc < cooldown_until_at`: Ghi nhận `status: "skipped", reason: "follow-released-daily-cooldown"` an toàn mà không spawn subprocess follow.
  - Sau khi hết hạn (sang ngày mới hoặc qua mốc cooldown): Mở lại ngay lập tức.
