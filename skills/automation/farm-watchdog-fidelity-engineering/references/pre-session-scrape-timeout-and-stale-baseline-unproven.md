# Pitfall & Remediation: Pre-Session Crawl Timeout & Stale Baseline False UNPROVEN

## 1. Hiện Tượng & Cơ Chế Lỗi
Trong báo cáo watchdog follow (`feed_session_watchdog.py`), tài khoản có thể bị dán nhãn:
```text
- M17 [Tik 5] (@user51904226): script báo 14 (chéo 14, tự nhiên 0) | baseline cũ (2026-10-29 10:03) | UNPROVEN
```
Mặc dù thực tế trong DB `tiktok_tracker.db`, tài khoản đã tăng đúng 14 lượt following trong ca tối.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)

1. **Pre-Session Scrape Timeout:**
   - Trong `tiktok_runner.py` (`_scrape_pre_session_following`), cơ chế cào T0 trước phiên gọi:
     ```python
     cmd = [target_python(), tracker_script, "--usernames", *uids, "--workers", str(min(15, len(uids)))]
     subprocess.run(cmd, capture_output=True, timeout=90, check=False)
     ```
   - Khi ca nuôi chạy **Dynamic Pool (`row == 0`)**, danh sách tài khoản cần cào có thể lên tới 80–82 uids.
   - Với 15 workers chạy qua proxy 4G xoay, tổng thời gian cào thực tế dao động từ 95–120s.
   - Ngưỡng cứng `timeout=90` khiến tiến trình bị `TimeoutExpired`, ngoại lệ bị `except Exception` nuốt im lặng (`logger.warning`), dẫn đến **không có snapshot baseline T0 nào được ghi vào DB lúc đầu phiên**.

2. **Cascade sang Watchdog Stale Baseline Guard:**
   - Đến cuối phiên, watchdog kích hoạt cào snapshot sau phiên (`latest`).
   - Để tính delta, watchdog tìm snapshot trước phiên (`timestamp <= query_start_iso`).
   - Do thiếu mốc T0 đầu phiên, watchdog buộc phải lùi về snapshot gần nhất (thường là từ ca sáng 10:03).
   - Guard khoảng cách thời gian (`(s_dt - b_dt).total_seconds() > 4 * 3600`) phát hiện snapshot cũ hơn 4 tiếng, lập tức đánh dấu `is_stale_baseline = True` và từ chối tính delta, dán nhãn `UNPROVEN`.

3. **Hiện tượng Nick ID `@user<số>`:**
   - Khi các tài khoản reg tự động (ví dụ qua Hotmail) mới tạo, TikTok gán ID mặc định `user + chuỗi số`.
   - Tool có thể đã đổi Biệt danh (Display Name), nhưng Handle/Username trong file Master Excel `taikhoan_dat_v2_updated .xlsx` vẫn giữ nguyên ID gốc dạng `@user...`. Đây là tài khoản hợp lệ của farm tại slot tương ứng, không phải tài khoản lạ.

---

## 3. Quy Trình Khắc Phục Chuẩn (Remediation Invariants)

1. **Quy Chuẩn Budget & Workers Cho Pre-Session Crawl (`tiktok_runner.py`):**
   - Tối thiểu 25 workers: `--workers str(min(25, len(uids)))`.
   - Timeout tối thiểu 180s: `timeout=180` (tránh kill ngầm khi proxy hoặc mạng chập chờn).
   - Log rõ số lượng uid thành công / timeout thay vì nuốt ngoại lệ im lặng.

2. **Watchdog Same-Day Reconcile Fallback (`feed_session_watchdog.py`):**
   - Khi baseline cũ quá 4h nhưng cùng ngày (`b_dt.date() == s_dt.date()`):
     * Nếu delta tính ra khớp chính xác với script báo (`web_delta == expected_delta`): Vẫn công nhận kết quả `KHỚP` kèm chú thích `(baseline sáng)`.
     * Chỉ dán nhãn `UNPROVEN` khi khác ngày hoặc delta bị lệch không thể chứng minh.
