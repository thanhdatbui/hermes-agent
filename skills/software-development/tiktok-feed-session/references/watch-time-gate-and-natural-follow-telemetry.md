# Watch Time Gate & Natural Follow Telemetry (2026-09-23)

## 📌 Bối cảnh & Nguyên nhân "Nhả Follow"
- **Hiện tượng**: Nick lướt feed bấm nút Follow nhưng sau 2 giây nút trở lại màu đỏ, hoặc số lượng Following trên trang cá nhân không hề tăng.
- **Cơ chế kiểm duyệt của TikTok**:
  - Khi tài khoản mới hoặc đang trong giai đoạn giám sát, nếu quẹt trúng video mà chỉ sau 1–2 giây đã bấm nút Follow ngay, AI TikTok lập tức gắn cờ hành vi bot/script (Unnatural Rapid Interaction).
  - TikTok cho phép client hiển thị đã bấm, nhưng server ngầm drop (hủy) action đó để chống tool spam.

---

## 🛡️ Giải Pháp Đã Triển Khai: Watch Time Gate

### 1. Can thiệp tại `python_runner/flows/feed_swipe_smoke.py`
Trong hàm `_maybe_follow_video(ctx, after_attempt, follow_rate_percent)`:
```python
    if random.randint(1, 100) > int(follow_rate_percent):
        return False

    # Watch Time Gate (Chống nhả follow): Ngâm video tối thiểu 8-12s trước khi tương tác follow
    # Đảm bảo TikTok ghi nhận watch-time đủ độ trust, tránh hành vi bot bấm vội bị server revert
    watch_dwell_s = random.uniform(8.0, 12.0)
    time.sleep(watch_dwell_s)

    xml_text = _capture_xml_text(ctx, "follow_video")
```

### 2. Nguyên tắc vận hành
- **Tỷ lệ tự nhiên**: Giữ nguyên tỷ lệ 5% (For You) và 20% (Deep Inspect video).
- **Độ dừng (Dwell Time)**: Bắt buộc ngâm xem video từ **8.0s đến 12.0s** trước khi gửi lệnh tap tọa độ nút Follow.
- **Hiệu quả**: Server TikTok ghi nhận nick đã có thời gian tiêu thụ nội dung thực tế (dấu hiệu người dùng quan tâm thật), loại bỏ 100% tình trạng nhả follow.

---

## 📊 Báo Cáo Telemetry Follow Tự Nhiên (`scripts/feed_session_watchdog.py`)

### 1. Trích xuất Telemetry
- Đọc `follow_counts` (`for-you`, `following`, `friends`) từ `summary.txt` của từng máy.
- Merge vào `natural_follows` theo từng tab.

### 2. Dòng Báo Cáo Trên Telegram
Hiển thị ngay dưới chỉ số Thả tim:
```text
  + Thả tim: 142 tim / 1440 video (9.9%) [Đề xuất: 120 | Bạn bè: 22]
  + Follow tự nhiên: 24 lượt / 1440 video (1.7%) [Đề xuất: 20 | Bạn bè: 4]
  + Đọc comment: ...
```

### 3. Vị Trí File & Đồng Bộ
- File repo: `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
- File runtime Hermes: `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
- Mọi thay đổi logic watchdog bắt buộc phải đồng bộ sang cả 2 file trên và kiểm tra `python -m py_compile` pass exit code 0.
