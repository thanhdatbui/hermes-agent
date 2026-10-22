# Taxonomy: Per-Account Organic Rest vs. Farm 4-Day Cycle Rest Day (N4)

## 1. Bối cảnh & Điểm dễ nhầm lẫn
Trong codebase Taadaa TikTok farm, từ "dưỡng sinh" (organic rest) xuất hiện ở 2 cơ chế hoàn toàn khác nhau:

| Cơ chế | Vị trí code | Trạng thái hiện tại | Bản chất |
|---|---|---|---|
| **Dưỡng sinh ngẫu nhiên 33% (Per-Account 1/3)** | `multi_machine_feed_session.py`: `_is_account_organic_rest_day()` | **ĐÃ BỎ** (commit `08cc160` ngày 11/10/2026, `return False`) | Băm MD5 để chọn ngẫu nhiên 1/3 số nick trong ngày nghỉ follow/upload. Đã bị gỡ bỏ theo yêu cầu của Operator. |
| **Ngày Dưỡng Sinh Chu Kỳ 4 Ngày (Farm 4-Day Cycle N4)** | `tiktok_runner.py`: `_SCHEDULE` + `cycle_day = (toordinal - BASE_ORDINAL) % 4` | **VẪN HOẠT ĐỘNG** | Ngày thứ 4 (N4: `cycle_day == 3`), `_SCHEDULE` có `target_row = None`. Runner gọi `determine_healing_row()` để chọn row cứu hộ, set `is_rest_day = True` và export `TAADAA_REST_DAY_NO_FOLLOW = "1"`. |

## 2. Quy tắc N4 trong Chu Kỳ 4 Ngày (`0fl + up`)
Theo định nghĩa chuẩn trong Farm Memory:
- **N1**: Parity lẻ (Row 1, 3, 5)
- **N2**: Parity chẵn (Row 2, 4, 6)
- **N3**: Row 7, 8, tối nghỉ dưỡng sinh
- **N4**: Slot động cứu nick yếu (`0fl + up`) -> **0 Follow, VẪN UPLOAD video bình thường**.

Khi `TAADAA_REST_DAY_NO_FOLLOW = "1"` được truyền:
1. `multi_machine_feed_session.py` ghi nhận `follow_result.json`:
   `{"status": "skipped", "reason": "rest-day-follow-disabled-pure-feed"}`
2. Hook upload **không bị chặn** — video vẫn đăng ở Phiên 1 (06:00) hoặc Phiên 2 (08:00).
3. Sang Phiên 2, upload sẽ skip với lý do `"already_uploaded_in_shift"` do đã up thành công ở Phiên 1.

## 3. Cạm bẫy hiển thị trên Watchdog (`feed_session_watchdog.py`)
- `feed_session_watchdog.py` vẫn giữ chuỗi format cũ:
  `• Chế độ Dưỡng Sinh (Organic Rest ~33%):`
  `  🌿 Nghỉ dưỡng sinh (N máy): ... (Chỉ lướt feed, 0 follow, 0 up)`
- Khi gặp `reason = "rest-day-follow-disabled-pure-feed"`, classifier (`formatters.py`) gán `category = "rest"`, khiến watchdog in ra tiêu đề legacy `~33%` và dòng chữ gây hiểu lầm `0 follow, 0 up`.
- **Thực tế**: Máy vẫn upload video bình thường ở phiên hợp lệ. Chỉ có follow là 0 lượt theo đúng contract của N4.
