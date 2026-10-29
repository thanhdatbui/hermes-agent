# Dashboard vs Farm Decoupling & Chu Kỳ 3 Ngày Shift-Pool

## 1. Độc Lập Tuyệt Đối Giữa Dashboard và Farm Runner
- **Kiến trúc tách biệt 100%:**
  - **Farm Runner (`tiktok_runner.py`):** Điều phối các máy Android cày feed/follow/upload qua ADB và PowerShell `run-feed-session.ps1`.
  - **Dashboard (`tiktok_dashboard.py` trên port 1905):** Chỉ là một HTTP server đọc dữ liệu từ SQLite `D:/Taadaa/data/tiktok_tracker.db` để hiển thị UI web.
  - **CẤM TUYỆT ĐỐI** liên đới lỗi Dashboard sang Farm. Dashboard sập hoàn toàn không làm farm ngừng chạy.

- **Bệnh học Dashboard bị treo / xoay đơ / timeout trên Windows:**
  1. **Tranh chấp Socket Port 1905:**
     - Windows cho phép nhiều socket cùng bind port nếu có cờ `SO_REUSEADDR`. Khi watchdog PowerShell (`tiktok_dashboard_watchdog.ps1`) kill tiến trình con mà sót tiến trình cha, hoặc thư mục `Startup` có file trùng lặp (`start_tiktok_dashboard.vbs` và `tiktok_dashboard_1905.vbs`), sẽ có 2–3 tiến trình `python.exe`/`pythonw.exe` cùng chiếm port 1905.
     - Windows phân phối request ngẫu nhiên vào tiến trình bị kẹt socket $\implies$ Trình duyệt xoay đơ hoặc báo `ERR_CONNECTION_TIMED_OUT`.
  2. **Cache Expiry & SQLite Heavy Query:**
     - Database tích lũy > 130.000 dòng snapshots. Hàm `get_farm_data()` chạy query phân tích window function mất ~4.2s.
     - Nếu `_CACHE_TTL` quá ngắn (15s), nhiều request song song từ trình duyệt sẽ làm bão hòa luồng và gây nghẽn I/O. Cần đặt `_CACHE_TTL >= 180s` (3 phút).
  3. **Quy trình xử lý dứt điểm khi Dashboard lỗi:**
     - Kill sạch mọi tiến trình liên quan: `tiktok_dashboard.py`, `tiktok_dashboard_watchdog.ps1`, `pythonw.exe`.
     - Xóa các shortcut / file `.vbs` trùng lặp trong `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.
     - Chỉ khởi chạy duy nhất 1 tiến trình `tiktok_dashboard.py`.
     - Kiểm chứng bằng urllib: `http://127.0.0.1:1905/` và `http://192.168.110.123:1905/` (LAN) phản hồi HTTP 200 < 0.1s.

## 2. Chu Kỳ 3 Ngày Shift-Pool & Phân Định 48h vs 72h
- **Cấu trúc chu kỳ 3 ngày liên tục (ĐÃ BỎ HOÀN TOÀN NGÀY 4 DƯỠNG SINH):**
  - **Ca 1 (Sáng: 06:00 & 08:00):** Pool `{Row 1, Row 2, Row 7}` (3 ngày cày hết 3 nick).
  - **Ca 2 (Trưa: 12:00 & 14:00):** Pool `{Row 3, Row 4, Row 8}` (3 ngày cày hết 3 nick).
  - **Ca 3 (Tối: 18:00 & 20:00):** Pool `{Row 5, Row 6}` (Ngày 1 & 2 chạy nick 5, 6; Ngày 3 kích hoạt slot Dynamic 3 phễu: nick cắn đề xuất, nick dính án nhả follow cần xả phạt, hoặc nick non ít video).
  - Kết thúc Ngày 3: Tự động reset về đầu vòng Ngày 1 cày tiếp, cày liên tục không có ngày nghỉ trắng toàn farm.

- **Phân định rõ 48h Cooldown vs Giãn cách chu kỳ 72h:**
  - **48h Cooldown (Hard Gate cơ giới hóa):** Nằm trong `_is_account_follow_cooldown` (`multi_machine_feed_session.py`). Nếu một tài khoản vừa bấm follow trong vòng 48.0 giờ qua, gate này chặn cứng (`is_in_cooldown = True`), tài khoản chỉ được lướt feed, cấm bấm follow.
  - **72h Giãn cách tự nhiên:** Khoảng cách thời gian giữa 2 lần cày của cùng 1 slot trong chu kỳ 3 ngày (ví dụ từ 06:00 Ngày 1 đến 06:00 Ngày 4 là tròn 72 tiếng). Vì $72h > 48h$, tài khoản luôn xả sạch điểm nghi vấn trước khi vào ca mới.

- **Lệch pha giữa các ca là an toàn & độc lập (Decoupled Resilient):**
  - Sổ cái `shift_pool_cycle_state.json` lưu `cycle_history` độc lập cho từng ca (`["1"]`, `["2"]`, `["3"]`).
  - Do 3 ca sở hữu các tập tài khoản rời nhau 100%, việc Ca 1 ở Lượt 3 (Row 7) trong khi Ca 3 ở Lượt 1 (Row 5) hoàn toàn không gây xung đột và không vi phạm thời gian hồi phục của bất kỳ tài khoản nào.
  - Thiết kế độc lập giúp farm chịu lỗi: một ca gặp sự cố mạng/proxy không làm đóng băng hay xáo trộn nhịp cày của các ca còn lại.
