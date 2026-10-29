# Watchdog Follow Reconcile: Pitfall T0 Missing on Shift Session 1 (Feed-only / Early Session)

## Bối cảnh sự cố
Trong báo cáo của `tiktok-follow-session-watchdog` (Ca 3 - Phiên 1/2 Tối, Run `row-0-180105`), 4 máy (M17, M24, M42, M68) có follow chéo / tự nhiên phát sinh nhưng bị watchdog gắn nhãn:
```text
- M17 [Tik 5] (@user51904226): script báo 14 (chéo 14, tự nhiên 0) | baseline cũ (2026-10-29 10:03) | UNPROVEN
```
Mặc dù thực tế trong database `snapshots`, following của nick đích và nick cày đều tăng khớp 100% (ví dụ `@user51904226` tăng từ 7 lên 21, đúng +14 lượt).

---

## Nguyên nhân gốc rễ (Root Cause)
1. **Thiết kế lệch pha giữa Runner và Watchdog:**
   - Trong kiến trúc nuôi acc theo ca, mỗi ca có 2 phiên:
     - Phiên 1/2 (`session_index == 1`): Ban đầu được định nghĩa là "Feed only" (lướt feed thuần).
     - Phiên 2/2 (`session_index == 2`): Là phiên chạy kèm Follow / Upload hook.
   - Do đó, cơ chế `_scrape_pre_session_following` (pre-session scrape T0) trong `tiktok_runner.py` chỉ được kích hoạt trước khi spawn Phiên 2, hoặc khi có cờ follow hook.
2. **Thực tế vận hành phát sinh follow ở Phiên 1:**
   - Trong quá trình lướt feed ở Phiên 1, các máy vẫn có thể kích hoạt follow tự nhiên hoặc chạy follow chéo (Anchor/Bù).
   - Vì Phiên 1 bắt đầu lúc 18:00 mà không cào T0, database không có snapshot nào giữa `10:03` sáng và `18:00`.
   - Khi watchdog kết thúc phiên lúc ~19:50 và cào post-session snapshot, hàm `reconcile_cluster_following` tìm snapshot trước `18:00` làm baseline thì chỉ thấy snapshot lúc `10:03` (> 7.5 tiếng).
3. **Max Baseline Age Guard chặn:**
   - Watchdog có guard: nếu khoảng cách giữa baseline và `session_start_iso` > 4 tiếng (`(s_dt - b_dt).total_seconds() > 4 * 3600`), baseline bị coi là stale.
   - Watchdog từ chối tính delta và xuất nhãn `UNPROVEN` để tránh sai số ảo, dẫn đến báo cáo bị coi là lỗi đối soát dù thực tế code đã chạy chuẩn.

---

## Quy tắc phòng tránh & Khắc phục chuẩn (Invariant)
1. **Scrape T0 bắt buộc cho MỌI Session bắt đầu ca (cả Session 1 lẫn Session 2):**
   - Không được giả định Session 1 là zero-follow. Mọi phiên spawn (`_spawn_feed_session`) đều phải đảm bảo các nick tham gia ca có snapshot T0 tươi mới (tuổi <= 15-30 phút).
2. **Fallback Reconcile Window Tolerance:**
   - Khi đối soát Session 1, nếu khoảng cách phiên cách xa mốc cào hàng ngày 10:00 sáng, scraper T0 đầu phiên là mắt xích bắt buộc duy nhất để triệt tiêu nhãn `UNPROVEN`.
3. **Tách bạch giữa Unproven do thiếu data vs Lỗi logic runner:**
   - Khi gặp `UNPROVEN`, kiểm tra ngay timestamp của snapshot gần nhất trong SQLite `snapshots`. Nếu khoảng cách > 4 tiếng, xác định ngay là thiếu scraper T0 ở đầu phiên, không phải runner hay tool đối soát bị hỏng logic.
