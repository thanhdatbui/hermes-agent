# TikTok Feed Session Post-Run Watchdog & Shift Completion Triage

## 1. Watchdog Báo Cáo Hoàn Tất Phiên Nuôi Tự Động (`feed_session_watchdog.py`)
Khi operator yêu cầu báo cáo kết quả tự động sau mỗi phiên nuôi TikTok về nhóm Telegram:
- **Kiến trúc:** Cron job Hermes `no_agent: true` chạy mỗi 5 phút (`*/5 * * * *`), quét thư mục artifacts theo ngày: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\`.
- **State tracking:** Lưu các run đã báo vào `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
- **Yêu cầu định dạng báo cáo (cực kỳ ngắn gọn, không giải thích lý thuyết):**
  - Tên phiên (`row-X-HHMMSS`)
  - Tổng số máy tham gia phiên
  - `Success (N máy):` Liệt kê danh sách số thứ tự máy thành công (1, 2, 3...)
  - `Fail (M máy):` Liệt kê danh sách số thứ tự máy thất bại kèm mã lỗi vắn tắt (VD: `M37 (blocked-vichanger-vpn)`, `M23 (manual-needed)`).
  - Không có phiên mới kết thúc $\rightarrow$ in rỗng để runner giữ im lặng (watchdog pattern).

## 2. Kiểm Tra Tiến Độ Ca & Phân Biệt Các Đợt Sóng (Wave) Trong Phiên
Khi operator hỏi "phiên ca chiều/sáng/tối này đã xong chưa?":
1. **Đối chiếu lịch Manifest chuẩn:** Đọc `D:\Taadaa\runtime\kibe\cron-state\manifests\<today>\ACTIVE.json` để lấy danh sách block và entries của ca (Ca 1: Row 2, Ca 2: Row 4, Ca 3: Row 2/6).
2. **Kiểm tra mốc `slot_time` và `slot_end`:** Phân tách rõ 3 phiên (`session_index` 1, 2, 3) và các đợt sóng giờ (do stagger/jitter trải dài từ 12:05 đến 17:50).
3. **Kiểm tra tiến trình thực tế trên OS:**
   - Đọc lease `D:\Taadaa\runtime\kibe\cron-state\runner-live-lease\<today>.json` (xác định PID và thời gian bắt đầu).
   - Kiểm tra process thực tế qua `wmic process where "caption like '%powershell%' or caption like '%python%'"` hoặc `ps -ef` để xác nhận `run_tiktok.py --mode multi-machine-feed-session` còn đang chạy đợt sóng sau hay không.
   - Không kết luận "đã xong ca" khi mới chỉ có một đợt máy wave 1 hoàn tất trong khi wave 2 (các máy có slot trễ) vẫn đang chạy.
