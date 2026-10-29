# TikTok Farm 3-Day Shift Pool Phase Decoupling & Dashboard Concurrency

## 1. Chu Kỳ 3 Ngày Cày Liên Tục & Bỏ Hẳn Ngày 4 Dưỡng Sinh
- **Quy hoạch tổ ca (Shift Pools):**
  - **Ca 1 (Sáng: 06:00 / 08:00):** Pool `{Row 1, Row 2, Row 7}` (3 nick).
  - **Ca 2 (Trưa: 12:00 / 14:00):** Pool `{Row 3, Row 4, Row 8}` (3 nick).
  - **Ca 3 (Tối: 18:00 / 20:00):** Pool `{Row 5, Row 6}` (2 nick cứng) + **Lượt 3: Dynamic Slot (`-1`)** bốc theo 3 phễu (Cắn đề xuất -> Xả phạt Cooldown -> Nick non).
- **Loại bỏ ngày 4:** Farm cày liên tục không nghỉ xả tải toàn farm. Sau khi kết thúc Lượt 3 (Row 7, Row 8, Dynamic Slot), hệ thống tự động reset về đầu vòng mới (Ngày 1: Row 1 - Row 3 - Row 5). CẤM đưa chú thích hoặc code Ngày 4 quay trở lại.

## 2. Bản Chất & Tính An Toàn Của Hiện Tượng "Lệch Pha" Giữa Các Ca
- **Cơ chế lưu state:** `shift_pool_cycle_state.json` lưu `cycle_history` độc lập theo từng ca: `cycle_history["1"]`, `["2"]`, `["3"]`.
- **Vì sao xảy ra lệch pha:**
  - Ca 3 chỉ có 2 nick cứng `{5, 6}` nên cạn pool sau 2 ngày và bước vào lượt Dynamic Slot `-1` sớm hơn.
  - Ca 1 hoặc Ca 2 nếu gặp sự cố mạng/proxy ở 1 phiên nào đó sẽ không ghi nhận hoàn thành lượt (`mark_shift_account_cycle_completed`), dẫn đến việc lùi lại để bù lượt ở ngày hôm sau.
  - Kết quả: Ca 3 có thể đã chạy xong lượt Dynamic `-1` trong khi Ca 1 sáng hôm sau mới chạy Row 7.
- **Khẳng định an toàn (Disjoint Sets):**
  - **Tập tài khoản rời nhau 100%:** Pool Ca 1, Ca 2, Ca 3 không có nick nào trùng nhau.
  - **Gate bảo vệ 48h:** Hàm `_is_account_follow_cooldown` kiểm tra timestamp lần follow gần nhất; nếu `< 48.0h` thì chặn cứng follow, chỉ cho lướt feed. Nhịp quay vòng tự nhiên (~72h) luôn đảm bảo $\ge 48$h cooldown.
  - **Khả năng chịu lỗi (Fault Isolation):** Một ca bị trễ lượt tự bù nhịp của chính nó mà không làm đóng băng hay xáo trộn 2 ca còn lại. CẤM can thiệp ép đồng pha cứng nhắc nếu không có chỉ đạo từ User.

## 3. Khắc Phục Lỗi Tranh Chấp Socket Dashboard TikTok (Port 1905)
- **Cơ chế Windows `SO_REUSEADDR`:** Windows cho phép nhiều tiến trình cùng bind vào cùng 1 port nếu socket bật reuse. Khi có 2 tiến trình `tiktok_dashboard.py` (hoặc `pythonw.exe`) cùng chạy, Windows phân phối gói TCP ngẫu nhiên. Tiến trình bị kẹt sẽ gây timeout toàn bộ request của User trên browser.
- **Vòng lặp tự hủy của Watchdog (`tiktok_dashboard_watchdog.ps1`):** Khi SQLite `tiktok_tracker.db` tích lũy lớn (>130k snapshots), cold query mất >4s. Watchdog timeout 8s phán đoán sai server chết, liên tục kill và restart tạo ra orphan processes.
- **Khắc phục:**
  1. Kiểm tra thư mục Windows Startup (`AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup`), xóa các file vbs/script trùng lặp (vd: `tiktok_dashboard_1905.vbs` vs `start_tiktok_dashboard.vbs`).
  2. Kill triệt để cả cây tiến trình `tiktok_dashboard.py`, `pythonw.exe` và watchdog ps1.
  3. Khởi động lại duy nhất 1 tiến trình máy chủ sạch.
