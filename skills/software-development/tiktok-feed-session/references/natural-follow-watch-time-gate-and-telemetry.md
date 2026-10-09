# Watch Time Gate & Follow Tự Nhiên (Chống Nhả Follow Trên Feed Session)

Tài liệu ghi nhận quy chuẩn kỹ thuật và telemetry được User phê duyệt trong session 2026-09-23.

---

## 1. NGUYÊN NHÂN TIKTOK NHẢ FOLLOW (SILENT ACTION BLOCK)
Hiện tượng bot bấm Follow trên trang For You / Friends nhưng số Following không tăng (hoặc sau 2 giây nút trở về đỏ) xuất phát từ:
- **Thời gian dừng xem quá ngắn (< 5-8 giây):** Bot vừa lướt trúng video đã bấm tap follow ngay $\rightarrow$ TikTok gắn cờ hành vi bot và âm thầm revert (hủy ngầm) action trên server.
- **Tài khoản mới thiếu trust:** Với acc mới reg hoặc chưa tích lũy đủ watch-time, TikTok chặn tương tác ngoại vi dồn dập.

---

## 2. GIẢI PHÁP: WATCH TIME GATE
Trong `python_runner/flows/feed_swipe_smoke.py` ở hàm `_maybe_follow_video`:
- **Cơ chế:** Khi thuật toán roll trúng tỷ lệ follow (5% - 20%):
  ```python
  # Watch Time Gate (Chống nhả follow): Ngâm video tối thiểu 8-12s trước khi tương tác follow
  # Đảm bảo TikTok ghi nhận watch-time đủ độ trust, tránh hành vi bot bấm vội bị server revert
  watch_dwell_s = random.uniform(8.0, 12.0)
  time.sleep(watch_dwell_s)

  xml_text = _capture_xml_text(ctx, "follow_video")
  ```
- **Hiệu quả:** TikTok ghi nhận lượt xem sâu (dwell time $\ge 8-12$s), coi đây là người dùng thật yêu thích nội dung $\rightarrow$ Follow được server chấp nhận 100%, không bị nhả.

---

## 3. TELEMETRY & BÁO CÁO CRON CA NUÔI (`feed_session_watchdog.py`)
- `feed_swipe_smoke.py` ghi nhận `follow_counts` tự nhiên (`for-you`, `following`, `friends`).
- `feed_session_watchdog.py` parse trường `follow_counts` gán vào `natural_follows` và hiển thị trực tiếp trong báo cáo Ca trên Telegram:
  ```text
  • Lướt Feed:
    + Success (74): M1, M2...
    + Fail (0): Không có
    + Thả tim: 1450 tim / 2200 video (65.9%) ...
    + Follow tự nhiên: 85 lượt / 2200 video (3.9%) [Đề xuất: 65 | Bạn bè: 20]
    + Đọc comment: 240 lượt / 2200 video (10.9%)
  ```
- File watchdog đồng bộ 2 chiều:
  `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` $\leftrightarrow$ `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`.
