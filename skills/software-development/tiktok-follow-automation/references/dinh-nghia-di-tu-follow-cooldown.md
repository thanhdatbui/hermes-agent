# Thuật ngữ "Đi tù" trong Vận hành Follow TikTok

## 1. Định nghĩa thuật ngữ
- **"Đi tù"**: Trong ngôn ngữ vận hành farm của user, "đi tù" **KHÔNG PHẢI** là tài khoản bị ban/khóa vĩnh viễn hay dính checkpoint đăng nhập.
- **Nghĩa chuẩn**: Nick bị TikTok phạt chặn tính năng follow hoặc tự động nhả follow (`FOLLOW_FAILED` / silent block follow). Khi bấm follow, TikTok âm thầm hủy follow sau vài giây hoặc reload profile không tăng following.

## 2. Cơ chế xử lý khi nick "Đi tù" (Progressive Cooldown 3-5-7-15 ngày)
- Khi phát hiện nick bị nhả follow (`FOLLOW_FAILED`), hệ thống tự động gắn Progressive Cooldown theo số cữ/ngày bị nhả liên tiếp:
  - **Streak 1 (Lần đầu bị nhả):** Nghỉ 3 ngày (`today + 3 days` đến 23:59:59 local).
  - **Streak 2 (2 cữ liên tiếp bị nhả):** Nghỉ 5 ngày (`today + 5 days`).
  - **Streak 3 (Tái phạm lần 3):** Nghỉ 7 ngày (`today + 7 days`).
  - **Streak >= 4 (Persistent Spammer):** Cách ly sâu 15 ngày (`today + 15 days`).
- Trong thời gian thụ án:
  - Chặn 100% mọi thao tác bấm follow (cả trên feed lẫn popup gợi ý bạn bè) để tránh việc cố follow làm TikTok reset hoặc gia hạn thời gian phạt.
  - Vẫn chạy lướt feed + thả tim bình thường (tỷ lệ 50-70%) để nuôi tương tác tự nhiên, gỡ trust score.
  - Sau khi hết hạn `cooldown_until_date` / `cooldown_until_at`, hệ thống mới cho phép thử nghiệm follow lại.
- **Xóa án tích khi thành công:**
  - Khi nick ra tù và bấm follow thành công (`STATUS_FOLLOWED`), hệ thống lập tức reset `fail_streak = 0`, `follow_failed = False`, xoá sạch markers `cooldown_until_at` và `cooldown_until_date`.
  - **Lưu ý đối soát:** Do `fail_streak` bị reset về 0 ngay khi follow thành công, để phân biệt giữa **"Acc khoẻ chưa từng nhả"** vs **"Acc từng đi tù ra đã hồi phục"**, BẮT BUỘC phải kiểm tra trường `last_cooldown_decision['decided_at']` (hoặc lịch sử `last_failed_date`). Nếu `decided_at < today` mà hôm nay follow thành công -> Đó là nick từng đi tù ra đã hồi phục. Nếu `last_cooldown_decision` hoàn toàn không có -> Đó là nick khoẻ chưa từng nhả.

## 3. Cách tra cứu và phân loại 4 nhóm sức khỏe của Row
- Đọc các file JSON trong thư mục:
  `D:/Taadaa/tiktok-follow/runs/state/follow_state_<machine>_row_<row>.json`
- Đối chiếu với kết quả phiên chạy trong ngày:
  `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<row>-<run_time>/<timestamp>/machines/machine_<m>/<sub_timestamp>/follow_result.json`
  và DB SoT `D:/Taadaa/data/tiktok_tracker.db` (`daily_account_actions`).
- **Quy tắc phân loại 4 nhóm chuẩn xác:**
  1. **Acc khoẻ chưa từng nhả:** `fail_streak == 0`, `last_cooldown_decision` is None, hôm nay hoàn thành follow tốt, 0 lỗi nhả.
  2. **Acc từng đi tù ra đã hồi phục:** `last_cooldown_decision['decided_at'] < today` (có tiền sử tù cũ), hôm nay ra tù follow thành công, streak reset về 0.
  3. **Acc mới dính nhả lần đầu hôm nay:** Trước hôm nay sạch (`streak cũ = 0`), hôm nay lần đầu dính `FOLLOW_FAILED` -> `streak = 1`, cooldown 3 ngày (đến `today + 3 days`).
  4. **Acc từng đi tù ra nhưng tái phạm hôm nay:** Đã có tiền sử tù (`streak cũ >= 1` hoặc `decided_at < today`), hôm nay vừa ra tù follow lại thì tiếp tục bị nhả -> Progressive Cooldown kích hoạt: Streak 2 (5 ngày), Streak 3 (7 ngày), Streak 4-6 (15 ngày).
