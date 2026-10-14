# User-Directed Reboot Anti-Paralysis, Sentinel Flag Bypass & In-Flight Session Preservation

## 1. Bản Chất Bẫy Tê Liệt Điều Phối (Paralysis by Confirmation Trap)
- **Hiện tượng thực tế (Sự cố 14/10/2026):**
  * User ra lệnh rõ ràng dứt khoát: *"Reboot kibe r thử lại cho t. Khi reboot có thể tự động resume session này k"*.
  * Coordinator phân tích cơ chế resume khả thi, kiểm tra điều kiện an toàn xong nhưng lại **dừng lại hỏi xin phép**:
    *"👉 Tôi phát lệnh Reboot Kibe PC ngay bây giờ nhé? (Chỉ cần bạn gõ 'ok' hoặc 'reboot')..."*
  * User tưởng bot đã làm nên đi ngủ một giấc. Khi thức dậy sau 2 tiếng thấy bot vẫn nằm im chờ chữ "ok", gây lãng phí nghiêm trọng thời gian và làm người dùng phẫn nộ (*"sao đéo tự làm đi... hỏi lắm vl ngủ 1 giấc dậy vẫn đéo xong"*).
- **Kỷ luật điều phối thép (User Invariant):**
  * Khi User đã phát lệnh mệnh lệnh thức (*"Reboot kibe...", "Restart máy..."*), **đó chính là authorization cuối cùng**.
  * **CẤM TUYỆT ĐỐI hỏi lại "tôi reboot nhé?" hay "xác nhận ok"**.
  * Coordinator BẮT BUỘC thực thi chuỗi hành động ngay lập tức, không được chần chừ hay đóng băng phiên.

## 2. Quy Trình 3 Bước Thực Thi Reboot Theo Lệnh User (User-Directed Reboot Protocol)

### Bước 1: Xóa Cờ Bỏ Qua Trong Ngày (Sentinel Flag Bypass)
- Trong `farm_preflight_daily_reset.py` có cơ chế chống reboot lặp:
  `sentinel = Path(rf"C:\Taadaa_Service\reboot_sentinel_{today}.flag")`
- Nếu hôm nay máy đã từng reboot một lần, script sẽ in:
  `[SKIP] Hom nay da reboot (reboot_sentinel_YYYY-MM-DD.flag). Thoat 0, khong reboot lap.`
  và **thoát 0 mà không hề reboot**!
- Do đó, khi User chủ động yêu cầu reboot, BẮT BUỘC xóa flag này trước:
  ```python
  from pathlib import Path
  from datetime import date
  sentinel = Path(rf"C:\Taadaa_Service\reboot_sentinel_{date.today().isoformat()}.flag")
  if sentinel.exists():
      sentinel.unlink()
  ```

### Bước 2: Bảo Toàn Session Telegram Đang Dở (In-Flight Session Preservation)
- BẮT BUỘC gọi hàm `preserve_in_flight_sessions` để đóng dấu `resume_pending = True` và xóa `.clean_shutdown`:
  ```python
  import sys
  sys.path.insert(0, "D:/Taadaa/tools/services/Taadaa_Service")
  from farm_preflight_daily_reset import preserve_in_flight_sessions
  count = preserve_in_flight_sessions(lookback_minutes=60)
  ```
- Đảm bảo topic Telegram hiện tại được Gateway tự động đánh thức lại và tiếp tục xử lý công việc ngay sau khi host boot vào Desktop.

### Bước 3: Phát Lệnh Reboot Cả Hai Máy Hoặc Máy Cục Bộ
- Chạy trực tiếp `python D:/Taadaa/tools/services/Taadaa_Service/farm_preflight_daily_reset.py`:
  * Script sẽ kiểm tra an toàn game TFT (`League of Legends.exe`).
  * Gửi lệnh SSH reboot Admin PC (`192.168.110.119`).
  * Kích hoạt `shutdown /r /t 5` trên Kibe PC.
  * Cả hai máy boot vào Windows với `AutoAdminLogon = 1` trong ~60 giây.
- Trường hợp chỉ reboot riêng Kibe:
  Gọi trực tiếp `shutdown /r /t 5` trên Windows command.

## 3. Hành Động Tiếp Diễn Sau Reboot (Post-Reboot Execution Invariant)
- Khi Gateway auto-resume đánh thức lại session, model BẮT BUỘC:
  1. Kiểm tra hiện trường O(1) ngay (`python D:/Taadaa/tools/inspect_machine.py <N>` hoặc `adb devices`).
  2. Xác nhận thiết bị đích đã online (`device`, không còn `not found`).
  3. Tiếp tục ngay task đang dở (ví dụ: ghim video, chạy verify, kiểm tra log), chụp ảnh bằng chứng gửi User.
  4. TUYỆT ĐỐI KHÔNG chào hỏi suông hay hỏi "bạn muốn làm gì tiếp theo".
