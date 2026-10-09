# Natural Follow: Watch Time Gate Chống Nhả Follow & Telemetry Watchdog

## 1. Cơ Chế Nhả Follow (Silent Action Block) & Root Cause
- Hiện tượng: Tài khoản tap Follow khi lướt feed, sau 1-2 giây nút chuyển lại đỏ hoặc server TikTok âm thầm hủy bỏ lượt follow.
- Nguyên nhân: Thời gian dừng (dwell time) trên video quá ngắn (< 1-2s) trước khi bấm follow. AI TikTok gắn cờ bot/script tự động tương tác và drop action ở backend.

## 2. Watch Time Gate (Chống Nhả Follow)
- Vị trí sửa: `python_runner/flows/feed_swipe_smoke.py` trong hàm `_maybe_follow_video`.
- Cơ chế:
  ```python
  if random.randint(1, 100) > int(follow_rate_percent):
      return False

  # Watch Time Gate: Ngâm video tối thiểu 8-12s trước khi tap follow
  watch_dwell_s = random.uniform(8.0, 12.0)
  time.sleep(watch_dwell_s)

  xml_text = _capture_xml_text(ctx, "follow_video")
  ```
- Kết quả: Đảm bảo thời lượng xem video đạt độ trust cao, server ghi nhận tương tác người dùng tự nhiên.

## 3. Telemetry Báo Cáo Ca Nuôi (Watchdog)
- File nguồn: `scripts/feed_session_watchdog.py`
- Cần parse `follow_counts` từ `summary.txt` từng máy và merge vào `natural_follows` theo từng feed type (`for-you`, `friends`, `following`).
- Định dạng hiển thị báo cáo Telegram:
  `+ Follow tự nhiên: {tot_nat_follows} lượt / {tot_swipes} video ({tot_nat_follow_rate:.1f}%) [Đề xuất: {tot_fy_nat_follows} | Bạn bè: {tot_fr_nat_follows}]`
- Lưu ý đồng bộ: Bắt buộc copy và kiểm tra cú pháp trên cả `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py` và `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`.
