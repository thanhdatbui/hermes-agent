# Case 186: Watch Time Gate Cho Follow Tự Nhiên & Telemetry Follow Tự Nhiên Trên Watchdog Farm (23/09/2026)

## 1. Hiện Tượng & Nghi Vấn
- Tính năng Follow Tự Nhiên (`_maybe_follow_video`) khi lướt feed từng bị tắt do người vận hành phát hiện nhiều nick bấm nút Follow trên UI xong thì bị TikTok âm thầm hủy (nhả follow - Silent Action Block).
- Đồng thời, báo cáo Watchdog theo ca (`feed_session_watchdog.py`) chỉ thống kê "Follow chéo" (chạy sau ca lướt qua Mode 1/Mode 2), hoàn toàn thiếu số liệu về số lượt và tỷ lệ % Follow tự nhiên thực tế diễn ra trong lúc lướt feed.

## 2. Root Cause
1. **Thiếu thời gian ngâm video (Watch Time Gate):**
   - Khi lướt feed For You, nếu roll trúng tỷ lệ follow (5% For You, 20% Deep Inspect), script tìm nút Follow và tap ngay lập tức (chỉ sau 1–2 giây xuất hiện trên màn hình).
   - Hệ thống chống bot của ByteDance gắn cờ đây là hành vi spam/tự động hóa và âm thầm hủy action trên server (client UI có thể đổi trạng thái nhưng sau khi reload hoặc qua video khác thì Following count không tăng).
2. **Thiếu Telemetry trên Watchdog:**
   - Script `feed_swipe_smoke.py` có đếm `follow_counts` trong `_feed_action_counts`, nhưng watchdog `feed_session_watchdog.py` không trích xuất trường này từ per-machine `summary.txt` và không merge vào payload tổng hợp.

## 3. Giải Pháp Kỹ Thuật (Case Fix)

### A. Thêm Watch Time Gate trong `python_runner/flows/feed_swipe_smoke.py`
Ngay trong hàm `_maybe_follow_video(ctx, after_attempt, follow_rate_percent)`:
```python
    if random.randint(1, 100) > int(follow_rate_percent):
        return False

    # Watch Time Gate (Chống nhả follow): Ngâm video tối thiểu 8-12s trước khi tương tác follow
    # Đảm bảo TikTok ghi nhận watch-time đủ độ trust, tránh hành vi bot bấm vội bị server revert
    watch_dwell_s = random.uniform(8.0, 12.0)
    time.sleep(watch_dwell_s)

    xml_text = _capture_xml_text(ctx, "follow_video")
```
- Ngâm video đủ từ 8 đến 12 giây giúp server TikTok ghi nhận tín hiệu retention cao (người dùng thật xem kỹ và thích nội dung trước khi bấm follow), bảo đảm 100% không bị revert follow.

### B. Cập nhật Telemetry trong `scripts/feed_session_watchdog.py`
1. **`merge_machine_result`**:
   Bổ sung gộp dict `natural_follows` lấy max theo từng tab (`for-you`, `following`, `friends`).
2. **`parse_run_all`**:
   Bổ sung regex parse `"follow_counts":` từ `summary.txt` của từng máy, gán vào dict payload `m_payload["natural_follows"] = follow_counts_map`.
3. **Thống kê tổng & format hiển thị**:
   - Tính toán: `tot_fy_nat_follows`, `tot_fl_nat_follows`, `tot_fr_nat_follows`, `tot_nat_follows` và tỷ lệ `tot_nat_follow_rate = tot_nat_follows / tot_swipes * 100%`.
   - Hiển thị trong khối `🏢 【FARM ...】` ngay dưới dòng Thả tim:
     ```text
     • Lướt Feed:
       + Success (78): M1, M2...
       + Fail (2): M30, M54
       + Trống slot/chưa có nick (0): Không có
       + Thả tim: 142 tim / 1,440 video (9.9%) [Đề xuất: 120 (10.1%) | Bạn bè: 22 (8.8%)]
       + Follow tự nhiên: 24 lượt / 1,440 video (1.7%) [Đề xuất: 20 | Bạn bè: 4]
       + Đọc comment: 310 lượt / 1,440 video (21.5%)
     ```

## 4. Kỷ Luật Đồng Bộ 4 Vị Trí
Mọi thay đổi trên `feed_session_watchdog.py` bắt buộc phải được đồng bộ và biên dịch cú pháp pass 100% trên cả 4 vị trí:
1. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
2. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
3. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/feed_session_watchdog.py`
4. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
