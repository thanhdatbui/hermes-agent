# Watchdog Session Queue Hold and Early-Completion Release Invariant (2026-10-20)

## 1. Symptom
User query: *"Sao lại trả report 2 phiên 1 lần v (cách nhau có 5ph) ?"*
Telegram watchdog (`tiktok-feed-session-watchdog`, cron job `1d62cb3562e0`) gửi báo cáo **Ca 1 - Phiên 1/2 (Row 2)** lúc 09:30, và ngay sau đó 5 phút gửi tiếp **Ca 1 - Phiên 2/2 (Row 2)** lúc 09:35.

---

## 2. Root Cause Analysis
### A. Farm Execution Timeline (20/10/2026)
- **Ca 1 - Phiên 1/2 (Khung 06:00 – 08:00):**
  - Cụm Kibe (Máy 1-80): Bắt đầu 06:03:13, kết thúc lúc **08:03:14** (`run_manifest.json` ghi nhận `end_time = 08:03:14`).
  - Cụm Admin (Máy 201-280): Bắt đầu 06:02:57, kết thúc sớm lúc **07:51:17** (`end_time = 07:51:17`).
- **Ca 1 - Phiên 2/2 (Khung 08:00 – 12:00):**
  - Khởi chạy lúc **08:00:10** trên cả hai cụm Kibe và Admin.
  - Cụm Kibe kết thúc lúc **09:22:13**.
  - Cụm Admin kết thúc lúc **09:26:32**.

### B. Cơ Chế Nghẽn Khóa Của Watchdog
1. Khi Phiên 2/2 đang chạy (08:00 – 09:26):
   - `is_feed_runner_active()` luôn trả về `True` do tiến trình runner (`multi_machine_feed_session` / `run-feed-session.ps1`) đang active trên hệ thống.
2. Để tránh chặn nhầm báo cáo của phiên cũ khi phiên mới đã chạy, watchdog gọi `is_cluster_session_busy()`:
   ```python
   latest_hhmmss, latest_run_name = max(session_runs, key=lambda item: item[0])
   completed_after_window = _is_session_manifest_completed(date_live, latest_run_name, win_end_hm)
   if not completed_after_window:
       return global_runner_busy
   ```
3. Trong `_is_session_manifest_completed`:
   ```python
   if win_end_hm in {"24:00", "00:00"}:
       return True
   end_hm = end_time...
   if end_hm >= win_end_hm:
       return True
   ```
   - Cụm Admin kết thúc lúc **07:51:17**, trong khi `win_end_hm` là **08:00**.
   - Biểu thức `07:51 >= 08:00` trả về **`False`**.
   - `_is_session_manifest_completed` trả về `False` -> hàm return early ở dòng `if not completed_after_window: return global_runner_busy` (True).
   - Hàm **chưa từng chạy đến** dòng `has_later_run = _has_later_session_run_started(...)` phía dưới.
4. Hệ quả:
   - Cụm Admin bị kẹt trạng thái `busy: True` cho Phiên 1/2 suốt từ 08:00 đến 09:26.
   - Vì watchdog yêu cầu `can_report_all = True` (mọi cụm phải hoàn tất mới chốt report), Phiên 1/2 bị giữ nghẽn (hold) toàn cục.
5. Lúc 09:26:32:
   - Phiên 2/2 kết thúc trên toàn farm -> `global_runner_busy` trở về `False`.
   - Cả Phiên 1/2 và Phiên 2/2 đồng loạt đủ điều kiện chốt báo cáo.
   - Do cơ chế an toàn chống spam Telegram `one_message_delivered` kèm `break` tại dòng 1432 trong `main()`:
     - **Tick 09:30:** Gửi báo cáo **Phiên 1/2** -> Claim state `reported_sessions`.
     - **Tick 09:35 (5 phút sau):** Gửi tiếp báo cáo **Phiên 2/2**.

---

## 3. The Fix & Invariant Contract
### Nguyên tắc:
Khi một lượt chạy của phiên kế tiếp (`has_later_run == True`, ví dụ: `row-2-080010` so với `row-2-060046`) đã thực sự xuất hiện trong thư mục ngày:
- Mọi hoạt động `runner_busy` hiện tại thuộc về phiên mới.
- Phiên trước đó chỉ cần `run_manifest.json` có `end_time` hợp lệ (đã kết thúc hoàn toàn) là được coi là `completed`, **không bắt buộc `end_hm >= win_end_hm`**.

### Implementation Pattern:
1. `_is_session_manifest_completed` chấp nhận cờ `has_later_run: bool = False`:
   ```python
   def _is_session_manifest_completed(date_live: str, run_name: str, win_end_hm: str, has_later_run: bool = False) -> bool:
       ...
       for manifest_path in manifest_paths:
           ...
           if has_later_run or win_end_hm in {"24:00", "00:00"}:
               return True
           if end_hm >= win_end_hm:
               return True
   ```
2. `is_cluster_session_busy` tính `has_later_run` trước và truyền vào:
   ```python
   latest_hhmmss, latest_run_name = max(session_runs, key=lambda item: item[0])
   has_later_run = _has_later_session_run_started(date_live, latest_run_name, latest_hhmmss)
   completed_after_window = _is_session_manifest_completed(
       date_live, latest_run_name, win_end_hm, has_later_run=has_later_run
   )
   if not completed_after_window:
       return global_runner_busy
   decision = False if has_later_run else global_runner_busy
   ```

### Đồng bộ các file:
- `scripts/feed_session_watchdog.py` (file chạy cron chính thức).
- `scripts/hermes_cron/feed_session_watchdog.py` (bản sync trong hermes_cron).
- `python_runner/tests/test_feed_session_watchdog.py` (test suite với test case `test_is_cluster_session_busy_releases_when_run_ended_before_window_and_later_run_exists`).
