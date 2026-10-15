# Continuous Rolling Avatar Operations & Anti-False-Yield Reporting (2026-10-15)

## 1. Context: 3-Ca Farm Schedule (Bỏ Ca 4 Đêm)
- TikTok feed schedule is now strictly 3 Ca x 2 Sessions (06:00, 12:00, 18:00).
- Night Ca 4 (00:00 - 05:30) is completely abolished.
- This unlocks a continuous 6.5-hour idle window ban đêm: `21:30 → 04:00` (before 04:00 cache clear).
- Farm also has daytime idle windows: `09:30 → 11:45` and `15:30 → 17:45`.

## 2. Pitfall: Legacy 23:45 Evening Truncation & False "Nhường Lịch Nuôi"
- **Legacy truncation:** `is_after_evening_window` triggered at 23:45, stopping batch launches for the entire night and forcing an incomplete report.
- **Reporting bug (Slot vs Distinct Machine):**
  - Summing `unuploaded` across Tik 1..8 yields unuploaded account slots (`tot_miss`), NOT unique machines.
  - Example: M10 and M30 offline in 6 Tiks each = 12 slots, but only 2 physical machines.
- **Reporting bug (False "Nhường lịch"):**
  - Unconditionally labeling `tot_miss` as "Bỏ qua an toàn: {tot_miss} máy (nhường lịch nuôi TikTok / lock tiến trình khác)" falsely blamed the feed schedule during midnight hours when no feed ca was running, while obscuring genuine errors (DEVICE_OFFLINE, SWITCHER_FAILED).

## 3. Standard Continuous Rolling Protocol
- Run continuous rolling batches across all farm idle windows until 100% DONE.
- Stop conditions:
  * Only when feed runner is actively running (`is_feed_runner_active()`).
  * Within 30 minutes before next scheduled feed ca.
  * During 04:00 - 04:45 daily cache-clear window.
- Periodic cadence reporting (every 6h: 00:00, 06:00, 12:00, 18:00 or 12h) to avoid fragmented spam.
- Explicit report breakdown:
  * Total DONE % (accounts / target).
  * New SUCCESS in window.
  * Real Technical Failures (distinct machines grouped by error).
  * Pending Queue (machines waiting for next batch).
  * NEVER claim "nhường lịch nuôi" unless verified active feed lock exists.

## 4. Cạm Bẫy Cột Avatar Excel `OK` vs Kích Hoạt Watchdog (`FORCE_UPLOAD`)
- **Nguyên nhân bỏ sót máy cần đổi avatar:**
  - `post_evening_avatar_watchdog.py` sử dụng `resolve_avatar_pending_machines.py <Tik>` để lập danh sách máy cần upload.
  - Script chỉ lọc các dòng có cột `Avatar != 'OK'`. Nếu nick đã từng up avatar thành công trong quá khứ (`Avatar: OK`), watchdog sẽ **bỏ qua hoàn toàn** mà không upload lại.
- **Quy tắc bắt buộc khi đổi/chuẩn hoá avatar theo lệnh User:**
  1. CẤM TUYỆT ĐỐI hứa "watchdog sẽ tự đổi" khi chưa sửa Excel.
  2. BẮT BUỘC cập nhật cột `Avatar` thành **`FORCE_UPLOAD`** trong `Tik<N>.xlsx`.
  3. BẮT BUỘC kiểm chứng lại bằng lệnh:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <Tik>
     ```
     Xác nhận output có chứa đúng số máy mục tiêu trước khi báo cáo.

## 5. Hiện Tượng Ca Nuôi Nhiều Phiên (Phiên 1 $\to$ Phiên 2) & Cửa Sổ Giờ Của Watchdog
- **Bẫy "Ca trưa kết thúc tưởng máy rảnh":**
  - Mỗi ca nuôi (ví dụ Ca trưa 12:00) thường gồm nhiều phiên liên tiếp:
    * Phiên 1 (Session 1): bắt đầu ~12:02, kết thúc ~13:58.
    * Phiên 2 (Session 2): tự động spawn ngay lập tức ~14:03 (`run_tiktok.py --session-index 2`), tái khóa toàn bộ Device Locks (`status: running`/`queued_v2`).
  - Coordinator nhìn thấy Phiên 1 vừa exit mà vội kết luận "máy đã rảnh" hoặc thắc mắc tại sao watchdog chưa chạy là sai hiện trường.
- **Khung giờ cứng của `is_post_evening_window` trong watchdog:**
  - Code của `post_evening_avatar_watchdog.py` chặn cứng chỉ chạy trong 3 khung giờ an toàn:
    * Khung sáng: `08:30 → 11:05` (sau Ca 1 P2, né reboot 11:20)
    * Khung tối: `20:15 → 23:45` (sau Ca 3 P2)
    * Khung đêm: `03:15 → 05:05` (sau Ca 4 P2, né reboot 05:20)
  - Khung giờ trưa/chiều (12:00 → 20:00) watchdog **CHỦ ĐỘNG KHÔNG CHẠY** để bảo vệ ca nuôi và các tác vụ GPM.
- **Quy tắc điều phối khi User yêu cầu "Làm đi" vào ban ngày:**
  1. Phải giải thích rõ: Giữa ngày đang là Phiên 2 ca nuôi (khóa máy), và watchdog chỉ tự kích hoạt ở khung an toàn tối (sau 20:15).
  2. Nếu cần làm ngay ban ngày: Phải đợi Phiên 2 kết thúc (~15:30), khi máy rảnh hoàn toàn mới chạy lệnh đơn máy cưỡng chế (`run_tiktok_upload_avatar.ps1` hoặc `pin_top_videos.py`), không được ngồi chờ watchdog tự kích hoạt lúc 14h.

