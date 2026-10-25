# Follow Watchdog Reconcile: Multi-Row Resolution, Timeout Salvage & Discrepancy Triage

## 1. Bối Cảnh Sự Cố & Hiện Tượng (2026-10-25)
Trong ca follow chéo TikTok (Ca 1 Phiên 2/2, Run `row-0-080000`), hệ thống giám sát Telegram watchdog báo cáo các chỉ số lệch bất thường:
- `M37 [Tik 1] (@ngc.trinh6472)`: script 0 lượt - web 11 lượt - lệch (+11).
- `M39 [Tik 1] (@thanh.huyn4934)`: script 11 lượt - web 14 lượt - lệch (+3).
- `M40 [Tik 1] (@charakrh768)`: script 3 lượt - web 0 lượt - lệch (-3).
- Đồng thời M40 vừa xuất hiện ở mục `+ Thành công (1 máy | 8.3%: M40)` vừa xuất hiện ở mục `+ Nhả follow (- Nhả ở Hồi phục 1: M40: 3 lượt)`.

---

## 2. Bản Chất Kỹ Thuật & Nguyên Nhân Gốc Rễ (Root Causes)

### A. Lỗi Mất Trắng Lượt Follow Khi Dính Timeout (`multi_machine_feed_session.py`)
- **Cơ chế lỗi:** Khi tiến trình con `follow_runner` chạy quá thời gian cho phép (20 phút / 1200s), `subprocess.TimeoutExpired` được kích hoạt. Khối bắt lỗi `except subprocess.TimeoutExpired` cũ gán cứng `followed_count = 0` và xóa trắng mảng `followed`.
- **Hậu quả:** M37 đã bấm thành công 11 nick thật vào `follow_state_37_row_1.json`, TikTok Web tăng đúng 11 following (từ 365 -> 376). Nhưng watchdog nhận `followed_count = 0` nên báo lệch (+11) và coi M37 như thất bại hoàn toàn.
- **Bản vá Invariant:** Khi timeout xảy ra, BẮT BUỘC đọc lại file `follow_state_{machine}_row_{row}.json` của ngày hôm nay (`ts.startswith(today_str)`) để salvage lại danh sách:
  ```python
  payload["followed_count"] = len(salvaged_follows)
  payload["followed"] = salvaged_follows
  ```

### B. Lỗi Soi Nhầm Row/Nick Khi Chạy Ca Hỗn Hợp (`active_row = -1`)
- **Cơ chế lỗi:** Ở các ca nuôi hỗn hợp toàn farm (`row-0` hay pool `{1, 2, 7}`), mỗi máy chạy một slot/row khác nhau (ví dụ: M40 chạy Row 2 / Tik 2 `@nguyenkhoi1403`).
- Trong `scripts/watchdog/parser.py`, hàm `parse_run_all` khi parse `follow_result.json` đã bỏ quên trường `"row": d.get("row")`.
- Khi `scripts/feed_session_watchdog.py` chạy `reconcile_cluster_following`, nó không có thông tin row thực chạy nên fallback lấy dòng đầu tiên trong workbook (`Tik 1: @charakrh768`).
- **Hậu quả:**
  - `@charakrh768` hôm đó không chạy follow nên Web delta = 0.
  - Script báo 3 lượt (của Tik 2 `@nguyenkhoi1403`, Web thực tế tăng đúng +3 từ 38 -> 41).
  - Watchdog đem số 3 của Tik 2 đi so với số 0 của Tik 1 -> Báo cáo sai lệch `script 3 lượt - web 0 lượt - lệch (-3)`, làm người vận hành tưởng nick bị TikTok nhả hoặc drop follow ngầm!
- **Bản vá Invariant:**
  1. `parser.py` BẮT BUỘC lưu giữ `"row": d.get("row")` vào `res_f`.
  2. `feed_session_watchdog.py` trong `reconcile_cluster_following` BẮT BUỘC ưu tiên:
     ```python
     f_row = follow_data.get("row")
     if slot_idx < 0 and f_row and str(f_row).isdigit() and 1 <= int(f_row) <= len(slots):
         val, tik_idx = slots[int(f_row) - 1], int(f_row)
     ```

### C. Lỗi Báo Kép "Vừa Thành Công Vừa Nhả Follow"
- **Cơ chế lỗi:** Trong vòng lặp tổng hợp kết quả follow của `feed_session_watchdog.py`: máy bị `category == "released"` nhưng có `len(flist) > 0` bị nhét đúp vào cả `fl_released` và `fl_success`.
- **Bản vá Invariant:** Máy đã thuộc `category == "released"` thì CHỈ nằm trong `fl_released`, tuyệt đối không đưa vào `fl_success`.

### D. Lệch Lượt Do Path B Verify Trả Về MANUAL_REVIEW Sau Khi Đã Tap (M39)
- **Cơ chế:** Khi tap nút follow trên row danh sách, lệnh tap đã ăn lên server TikTok (Web tăng). Nhưng khi mở profile để verify Path B (`_path_b_verify`), nếu font chữ/emoji hoặc mạng lag làm identity check không đạt `status == "ok"`, script trả về `MANUAL_REVIEW`.
- Script không lưu nick đó vào `state.followed` (để an toàn), nhưng Web thực tế đã được cộng follow. Đây là độ lệch an toàn chấp nhận được giữa Client-side Defensive Check và Server-side Reality.

---

## 3. Kỷ Luật Đồng Bộ File Script & Hermes Cron Mirror
- File `scripts/feed_session_watchdog.py` BẮT BUỘC đồng bộ 100% byte-for-byte với `scripts/hermes_cron/feed_session_watchdog.py`.
- Unit test `test_feed_session_watchdog_and_hermes_cron_sync` kiểm tra điều này tự động. Bất kỳ thay đổi nào trên watchdog đều phải copy hoặc patch đồng thời sang thư mục `hermes_cron/`.
