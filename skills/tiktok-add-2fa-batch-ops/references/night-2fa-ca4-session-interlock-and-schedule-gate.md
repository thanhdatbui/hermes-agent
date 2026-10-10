# Ngăn Chặn Xung Đột Lịch Nuôi Ca 4 Đêm & Cơ Chế Khóa Liên Động Trạng Thái (10/10/2026)

## 1. Bối cảnh sự cố xung đột tài nguyên ban đêm
Tại farm TikTok (80-160 máy), Ca 4 (Đêm) vận hành theo cấu trúc 2 phiên:
- **Phiên 1 (00:00 - ~01:00):** Lướt feed đêm.
- **Phiên 2 (01:30 - ~02:35):** Lướt feed + Upload video (ví dụ: `row-8-013048` hoàn tất lúc 02:36).

**Điểm nghẽn cũ:**
- Cron `night-tiktok-2fa-watchdog` đặt khung giờ `01:00 - 02:50` (schedule `*/10 1,2 * * *`).
- Khi Phiên 1 vừa xong lúc ~01:00 và Phiên 2 chưa kịp spawn (khe nghỉ 30 phút giữa 2 phiên), watchdog 2FA thấy không có feed runner đang active nên lập tức kích hoạt batch và chiếm device lock hàng loạt (`machine_*.lock.json`).
- Đến 01:32:23 khi Phiên 2 spawn, runner phát hiện 30+ máy bị lock nên buộc phải kích hoạt cơ chế né an toàn (`skipped-device-locked`). Watchdog nuôi acc phân loại nhầm thành lỗi script/tập trung.

---

## 2. Giải pháp kỹ thuật 3 lớp chuẩn hóa

### Lớp 1: Khóa liên động trạng thái (Event-Driven State Gate)
Không chỉ kiểm tra liveness của tiến trình (`is_feed_runner_active()`) vì giữa các phiên luôn có khoảng thời gian chết (inter-session gap). Bắt buộc kiểm tra sổ cái báo cáo chính thức `feed_session_reported.json`:

```python
REPORTED_FILE = Path(os.getenv("TAADAA_REPORTED_FILE", "D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json"))

def is_ca4_finished(today_str: str) -> bool:
    """Kiểm tra Ca 4 Phiên 2 đã hoàn tất và đã được Watchdog báo cáo hay chưa."""
    if not REPORTED_FILE.is_file():
        return False
    try:
        data = json.loads(REPORTED_FILE.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        return f"{today_str}_ca4_phien2" in sessions or f"{today_str}_ca4" in sessions
    except Exception as exc:
        logger.warning("Lỗi kiểm tra trạng thái Ca 4: %s", exc)
        return False
```

### Lớp 2: Dời cửa sổ an toàn sau Ca 4
- Dời cửa sổ chạy trong code sang: **02:45 - 04:50** (sau khi Phiên 2 Ca 4 kết thúc hoàn toàn lúc ~02:35).
- Biểu thức kiểm tra:
  ```python
  in_window = (now.hour == 2 and now.minute >= 45) or (3 <= now.hour <= 4)
  ```
- Cập nhật Cron Schedule trên Hermes:
  - Cũ: `*/10 1,2 * * *`
  - Mới: `*/10 2,3,4 * * *`

### Lớp 3: Kỷ luật phân rã diff Closeout Gate (Diff-Cap < 30.000 bytes)
Khi bổ sung tính năng vào watchdog hoặc test suite:
- Cẩn trọng với các docstrings dài dòng và văn bản verbose. Closeout Gate giới hạn cứng diff candidate `MAX_DIFF_BYTES_GATE = 30_000`.
- Nếu diff candidate vượt nhẹ 30KB (như 30.179 bytes), tiến hành rút gọn docstring/comments thay vì cắt bớt logic hay test assertions.
