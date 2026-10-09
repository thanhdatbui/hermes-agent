# Watchdog Device Lock False Alarm Safety & Cadence Rules

## Hiện tượng (Incident Reference: 2026-09-06 Ca 1 Phiên 1)
- Lúc 06:00 - 06:12: Runner kích hoạt đợt chạy đầu tiên của phiên (`row-2-060253`). Do batch đăng ký Gmail ban đêm (`gmail_reg_v10.py` / `gpm-login`) chưa xong và đang giữ `device_lock`, toàn bộ 80 máy bị `skipped-device-locked` trong 10 phút và đợt chạy kết thúc sớm lúc 06:12.
- Lúc 06:15:44: Script `feed_session_watchdog.py` chạy định kỳ `*/5`. Watchdog kiểm tra:
  + Folder `row-2-060253` có 80 máy đã sinh file `summary.txt` (đều có `final_status: skipped-device-locked`).
  + Tại thời điểm đó, đợt chạy trước đã dừng và đợt chạy 15 phút kế tiếp chưa kích hoạt -> `runner_busy == False`.
  + Watchdog ngộ nhận toàn bộ 80 máy đã hoàn thành và runner rảnh, nên kích hoạt chốt báo cáo sớm: `📊 [TIKTOK NUÔI ACC] Ca 1 - Phiên 1/3: Success (0), Fail (80)`.
  + Đồng thời ghi key `2026-09-06_ca1_phien1` vào `feed_session_reported.json`.
- Lúc 06:16:55: Cron runner `phase9-runner-tiktok-feed` vào tick kế tiếp (`row-2-061651`), các máy đã nhả lock Gmail và chạy feed thật thành công 64/80 máy. Nhưng Telegram đã nhận alert gây hoang mang và watchdog không tự cập nhật lại đợt chạy thật nếu key đã bị khóa trong state.

## Quy tắc Bất biến cho Feed Session Watchdog
1. **Cấm chốt phiên sớm khi vướng `skipped-device-locked`:**
   - Trong suốt khung giờ phiên (ví dụ Ca 1 Phiên 1 là `06:00 - 07:30`), nếu các máy chưa thành công chỉ mang trạng thái `skipped-device-locked`, watchdog CẤM TUYỆT ĐỐI coi đó là máy đã chạy xong (`completed`).
   - Runner được thiết kế chạy lặp định kỳ mỗi 15 phút (`*/15`) để tiếp tục nhặt các máy vừa nhả lock trong khung giờ phiên.
   - Chỉ được chốt báo cáo khi:
     (a) Đã hết khung giờ phiên (`now_hm >= window_end_hm`) VÀ runner không bận, HOẶC
     (b) Toàn bộ target machines đã thực sự chạy (`success` hoặc lỗi thực thi thật `blocked-proxy-vpn`, `manual-needed`, etc., KHÔNG phải `skipped-device-locked`).
2. **Quy trình Recovery khi Watchdog báo sai:**
   - Kiểm tra log đợt chạy kế tiếp trong `D:\Taadaa\runtime\kibe\live\<date>\` xem có run folder mới đang chạy thật hay không (`log.jsonl` có nhiều step nuôi feed thật).
   - Xóa key session bị ngộ nhận khỏi file `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
   - Để watchdog ở tick kế tiếp tự động tổng hợp đợt chạy thật mới nhất và báo cáo lại kết quả chính xác lên channel.
