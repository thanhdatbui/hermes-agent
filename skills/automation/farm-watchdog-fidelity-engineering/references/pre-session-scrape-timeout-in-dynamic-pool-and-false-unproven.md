# Pitfall & Remediation: Pre-Session Scrape Timeout in Dynamic Pool and False UNPROVEN Cascade

## 1. Hiện Tượng Thực Tế
Trong báo cáo định kỳ của `tiktok-follow-session-watchdog`:
```text
  + Đối soát TikTok Web (+0 Following thật - Khớp 100% so với script báo):
    - M50 [Tik 2] (@vuthao04123): script báo 5 (chéo 5, tự nhiên 0) | baseline cũ (2026-11-01 10:03) | UNPROVEN
```
Mặc dù thực tế trong DB `tiktok_tracker.db`, số following của tài khoản đã tăng từ 15 (ngày hôm trước) lên 20 (cuối phiên sáng nay), tức tăng đúng **+5 lượt** (khớp chính xác 100% với script), nhưng watchdog vẫn dán nhãn `UNPROVEN` và hạ tổng đối soát về `+0 Following thật`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Dual Cascade Failure)

1. **Pre-Session Scrape Timeout ở Dynamic Pool (`tiktok_runner.py`):**
   * Trong hàm `_scrape_pre_session_following`:
     ```python
     cmd = [
         target_python(),
         tracker_script,
         "--usernames", *sorted(uids),
         "--workers", str(min(15, len(uids))),
     ]
     subprocess.run(cmd, capture_output=True, timeout=90, check=False)
     ```
   * Khi ca chạy theo **Dynamic Pool (`row == 0`)**, danh sách uids cần cào của ca (ví dụ Ca 1 gồm pool {1, 2, 7}) lên tới 80–84 tài khoản.
   * Với 15 workers cào qua proxy 4G xoay, thời gian hoàn tất dao động 100–130s.
   * Ngưỡng cứng `timeout=90` khiến tiến trình bị `TimeoutExpired` kill ngang giữa chừng. Chỉ có 30–36 tài khoản đầu tiên kịp ghi snapshot, **48+ tài khoản còn lại bị mất mốc snapshot T0 đầu phiên**.

2. **Watchdog Fallback về Snapshot Hôm Trước và Kích Hoạt Guard `stale_baseline` (`feed_session_watchdog.py`):**
   * Khi không có mốc T0 trong khoảng buffer đầu phiên (`query_start_iso = 06:15`), query SQL buộc phải lùi về snapshot gần nhất trước đó (rơi vào ca sáng ngày hôm trước, ví dụ `2026-11-01 10:03`).
   * Guard trong watchdog kiểm tra:
     ```python
     is_stale_baseline = (s_dt - b_dt).total_seconds() > 4 * 3600 or b_dt.date() != s_dt.date()
     ```
   * Do `b_dt.date() != s_dt.date()`, snapshot hôm trước bị đánh dấu stale ngay lập tức.
   * Watchdog gạt bỏ delta và dán nhãn `UNPROVEN`, bỏ qua sự thật là `latest_fl - prev_fl == expected_delta` (+5 - 0 = +5).

---

## 3. Quy Tắc & Cơ Chế Khắc Phục Chuẩn (Remediation Invariants)

1. **Quy Chuẩn Scraper Budget Cho Dynamic Pool (`tiktok_runner.py`):**
   * Nâng số worker: `--workers str(min(25, len(uids)))`.
   * Nâng timeout an toàn: `timeout=180` (tránh kill ngầm khi proxy xoay hoặc danh sách > 80 nick).
   * Kiểm thử: Cập nhật unit test runner healing tương thích với assertion `timeout in (90, 180)`.

2. **Cơ Chế Reconcile Fallback Khi Web Delta Khớp 100% (`feed_session_watchdog.py`):**
   * Nếu baseline snapshot cũ (> 4h hoặc khác ngày) NHƯNG `expected_delta > 0` và `latest_fl - prev_fl == expected_delta`:
     * **KHÔNG ĐƯỢC dán nhãn `UNPROVEN`**: Số liệu thực tế trên Web đã chứng minh script đã thực thi thành công đủ số lượt follow.
     * Vẫn ghi nhận `KHỚP` và cộng delta vào tổng số follow của phiên, kèm ghi chú rõ ràng:
       `script X lượt - web X lượt - khớp (baseline cũ <thời gian>)`.
     * Chỉ dán nhãn `UNPROVEN` khi `latest_row` hoàn toàn thiếu, hoặc delta tính ra bị lệch so với script mà khoảng cách thời gian quá lớn không thể đối chiếu.

3. **Canary Runner Subprocess Timeout trong Unified Patch Pipeline:**
   * Khi chạy `canary_runner.py` với mode `multi-machine-feed-session` (vừa navigate vừa swipe feed 2 video trên máy thật), thời gian chạy thực tế trung bình là 200–240s.
   * Do đó trong `unified_patch_pipeline.py`, lệnh gọi `canary_runner.py` bắt buộc phải có timeout tối thiểu `300s` (thay vì 180s) để tránh bị false failure do timeout khi máy thật đang chạy mượt.
