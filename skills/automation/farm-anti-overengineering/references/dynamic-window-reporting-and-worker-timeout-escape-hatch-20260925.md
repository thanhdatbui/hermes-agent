# Dynamic Window Reporting & Worker Timeout Escape Hatch (25/09/2026)

## 1. Bẫy Báo Cáo Sai Khung Giờ (Static Hardcoded Shift Label)
Khi mở rộng thêm khung giờ chạy cuốn chiếu cho một watchdog (ví dụ watchdog ca tối `post_evening_avatar_watchdog.py` được mở thêm khung ca sáng 08:30–11:15):
- **Triệu chứng:** Watchdog quét hết khung giờ sáng lúc 11:26 và phát alert mang tiêu đề "Hết khung giờ ca tối (sau 23:30)" và "Kết quả ca tối nay", khiến người vận hành tưởng nhầm hệ thống bị nhảy lịch hoặc phát nhầm alert cũ.
- **Root Cause:** Template string trong hàm format report (`format_report_html`) bị hardcode chuỗi chữ tĩnh ("ca tối", "sau 23:30"), không gán nhãn động theo `now_dt` thực tế khi chạy.
- **Quy tắc:**
  1. Khi bổ sung hoặc mở rộng window thời gian cho bất kỳ cron/watchdog nào, **BẮT BUỘC** kiểm tra toàn bộ hàm format report và template text xem có hardcode tên ca/khung giờ không.
  2. Bắt buộc derive ca chạy từ timestamp `now_dt` (ví dụ `06:00 <= hour < 14:00` -> `ca sáng`, `sau 11:15`; còn lại -> `ca tối`, `sau 23:30`).
  3. Viết regression test chuyên biệt cho từng khung giờ phát report (cả ca sáng lẫn ca tối).

## 2. Kỷ Luật Điều Phối & Worker Timeout Escape Hatch
- Khi dispatch worker subagent sửa code đơn giản/O(1) nhưng worker liên tiếp bị timeout (>600s do mạng, tool gate hoặc model stall):
  1. Coordinator không được ngồi đợi thụ động hoặc lặp lại prompt cũ.
  2. Phải phân tích rõ anchor và diff còn thiếu để người dùng nắm được hiện trạng chính xác.
  3. Khi hoàn tất bản vá và test pass 100%, phải đồng bộ cả file repo deploy (`D:/Taadaa/Hermes/deploy/...`) lẫn runtime (`~/.hermes/scripts/`), compile kiểm tra cú pháp và chạy pytest để có bằng chứng nghiệm thu máy sinh.
