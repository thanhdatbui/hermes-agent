# Follow Tự Nhiên Trong Feed Session & Watch Time Gate (Chống Nhả Follow)

## 1. Bối cảnh & Hiện tượng TikTok Nhả Follow
- **Triệu chứng:** Khi lướt feed có bật follow tự nhiên, máy bấm nút Follow trên UI TikTok xong nhưng sau 1-2 giây nút bị revert về đỏ, hoặc số Following trên profile/server không hề tăng.
- **Nguyên nhân cốt lõi:** Lướt trúng video và tap Follow quá nhanh (< 5s). Thuật toán AI của ByteDance phát hiện hành vi tương tác thiếu dwell time (thời gian xem video) nên đánh dấu là bot tương tác rác và âm thầm drop action (Silent Action Block).

## 2. Giải pháp: Watch Time Gate (8.0s - 12.0s)
- **Vị trí cài đặt:** `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` trong hàm `_maybe_follow_video`.
- **Cơ chế:**
  ```python
  if random.randint(1, 100) > int(follow_rate_percent):
      return False

  # Watch Time Gate: Ngâm xem video tối thiểu 8.0s - 12.0s trước khi tap follow
  watch_dwell_s = random.uniform(8.0, 12.0)
  time.sleep(watch_dwell_s)

  xml_text = _capture_xml_text(ctx, "follow_video")
  # Tìm nút follow và tap
  ```
- **Tách biệt cổng kiểm tra:**
  - Cổng 10 video (`under-10-videos-follow-disabled`): CHỈ áp dụng cho Follow chéo nội bộ farm (`run_follow.py` Mode 1 & Mode 2).
  - Follow tự nhiên trong khi lướt feed: Chạy độc lập theo tỷ lệ tự nhiên (`DEFAULT_FEED_FOLLOW_RATES` ~5% For You, ~20% Deep Inspect), không bị chặn bởi cổng 10 video.

## 3. Telemetry & Báo cáo Cron Watchdog
- **File:** `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` (đồng bộ sang `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`).
- **Trích xuất:**
  - `parse_run_all`: Quét chuỗi `"follow_counts":` từ `summary.txt` của từng máy, trích xuất số lượng theo các tab (`for-you`, `following`, `friends`) vào dictionary `follow_counts_map`.
  - `merge_machine_result`: Merge telemetry `natural_follows` theo max giữa các lần chạy.
- **Hiển thị báo cáo Telegram theo Ca:**
  - Tính tổng: `tot_nat_follows = tot_fy_nat_follows + tot_fl_nat_follows + tot_fr_nat_follows`.
  - Tỷ lệ: `tot_nat_follow_rate = (tot_nat_follows / tot_swipes * 100.0)`.
  - Dòng hiển thị ngay dưới Thả tim:
    `+ Follow tự nhiên: {tot_nat_follows} lượt / {tot_swipes} video ({tot_nat_follow_rate:.1f}%) [Đề xuất: {tot_fy_nat_follows} | Bạn bè: {tot_fr_nat_follows}]`
