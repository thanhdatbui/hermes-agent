# Quy trình tra cứu nhanh Row / Ca nuôi acc TikTok trong ngày (O(1))

## 1. Mục đích
Khi cần kiểm tra hôm nay cron nuôi acc TikTok (cả Kibe và Admin) chạy những Row nào, tuyệt đối không quét đĩa, không grep log diện rộng. Sử dụng các điểm kiểm tra O(1) sau.

## 2. Các điểm kiểm tra O(1) chuẩn

### A. Thư mục Live Artifacts (Chính xác 100% theo thực tế đã spawn)
- Cụm Kibe: `D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/`
- Cụm Admin: `D:/Taadaa/runtime/admin/live/YYYY-MM-DD/`

Tên các thư mục con mang trực tiếp thông tin Row và Timestamp:
`row-<Row>-<HHMMSS>`
Ví dụ:
- `row-3-060037` -> Row 3, Ca 1 Phiên 1 (06:00)
- `row-3-080058` -> Row 3, Ca 1 Phiên 2 (08:00)
- `row-4-120009` -> Row 4, Ca 2 Phiên 1 (12:00)
- `row-4-140005` -> Row 4, Ca 2 Phiên 2 (14:00)
- `row-5-180035` -> Row 5, Ca 3 Phiên 1 (18:00)
- `row-5-200007` -> Row 5, Ca 3 Phiên 2 (20:00)

### B. File trạng thái Runtime
- `D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`:
  ```json
  {
    "last_row": 5,
    "last_window": "2026-10-14T20",
    "last_run_at": "2026-10-14T20:00:07.194697+07:00"
  }
  ```
- `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`:
  Danh sách phiên đã được `feed_session_watchdog.py` tổng kết và gửi báo cáo Telegram (`YYYY-MM-DD_caX_phienY`).

## 3. Công thức tính Chu kỳ 4 ngày (Parity 96h)
Schedule gồm 3 ca x 2 phiên/ngày (bỏ ca đêm 0h):
- Ca 1: Phiên 1 (06:00), Phiên 2 (08:00)
- Ca 2: Phiên 1 (12:00), Phiên 2 (14:00)
- Ca 3: Phiên 1 (18:00), Phiên 2 (20:00)

Base ordinal: `739900` (ngày `2026-10-11` là Ngày 1 / cycle_day 0):
`cycle_day = (date.today().toordinal() - 739900) % 4`

- **Day 0 (Ngày 1 - Lẻ):** Ca 1 -> Row 1; Ca 2 -> Row 3; Ca 3 -> Row 5.
- **Day 1 (Ngày 2 - Chẵn):** Ca 1 -> Row 2; Ca 2 -> Row 4; Ca 3 -> Row 6.
- **Day 2 (Ngày 3):** Ca 1 -> Row 7; Ca 2 -> Row 8; Ca 3 -> Dưỡng sinh Row 3/4.
- **Day 3 (Ngày 4 - Dưỡng sinh động):** 3 ca 3 row do `healing_selector.py` chọn (thường là Ca 1 -> Row 3, Ca 2 -> Row 4, Ca 3 -> Row 5).
