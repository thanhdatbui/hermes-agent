# Rolling Cache Clear & Device Lock Safeguards (Bảo Vệ Khóa Máy & Dọn Cache Cuốn Chiếu)

## 1. Bối cảnh & Rủi ro thực tế (Sự cố Ca 4 - 18/09/2026)
- **Hiện tượng:** Phiên nuôi Ca 4 thất bại hơn 50% máy với các lỗi đồng loạt: `TikTok focus lost to launcher`, `focused package unavailable`, `screen capture invalid`, `adb command timed out`.
- **Nguyên nhân gốc rễ:** Script dọn cache định kỳ chạy không có `DeviceLock` từng máy, và đặt lệnh `am force-stop com.ss.android.ugc.trill; input keyevent KEYCODE_HOME;` trong khối `finally` vô điều kiện. Khi cron kích hoạt, nó bắn lệnh force-stop và ấn Home vào thẳng các máy đang lướt feed thật, phá vỡ phiên nuôi của toàn farm.

## 2. Các Invariant Bắt Buộc (Chỉ đạo User 18/09/2026)

### Quy tắc 1: Khóa máy trước khi dọn (`DeviceLock` per-machine)
- Mọi thao tác bảo trì, dọn cache, hoặc can thiệp máy BẮT BUỘC phải acquire `DeviceLock`:
  ```python
  from automation_core.device_lock import DeviceLock, DeviceLockUnavailable, DeviceLockNeedsUserDecision

  try:
      with DeviceLock(serial=serial, machine=str(m_num), project="clear-cache", bypass_proxy_readiness=True):
          # Chỉ thao tác adb / dọn cache trong khối lock này
          ...
          # Safe teardown khi hoàn tất trong lock
          adb_shell("am force-stop ...; input keyevent 3")
  except (DeviceLockUnavailable, DeviceLockNeedsUserDecision):
      # Máy đang có script khác giữ lock -> BỎ QUA NGAY
  ```

### Quy tắc 2: Tuyệt đối CẤM PHÁ LOCK & Không can thiệp máy bận
- Khi phát hiện máy đang có script khác giữ lock:
  - **CẤM TUYỆT ĐỐI** gửi lệnh ADB can thiệp (không `shell`, không `input`, không `am force-stop`).
  - **CẤM** ép về HOME.
  - Đánh dấu máy ở trạng thái `[LOCKED]` và bỏ qua, ngồi chờ lượt cron tiếp theo để dọn cuốn chiếu khi máy rảnh nhả lock.

### Quy tắc 3: Chạy cuốn chiếu 1 lần/ngày (`cleared_machines_today`)
- Dọn cache chỉ chạy cuốn chiếu trong khung giờ rảnh sau ca (ví dụ 03:00 - 05:45).
- Quản lý state theo ngày:
  - File state lưu `last_date` và `cleared_machines` (danh sách ID máy đã dọn thành công).
  - Sang ngày mới: tự động reset danh sách.
  - Mỗi tick cron (ví dụ `*/15 3,4,5 * * *`): chỉ lọc các máy online **chưa nằm trong `cleared_machines`**.
  - Máy nào dọn thành công thì append ngay vào state. Dọn xong máy nào thì thôi máy đó.
  - Khi toàn bộ máy online đã hoàn tất: thoát im lặng (`silent`), không spam Telegram.

### Quy tắc 4: Giới hạn phạm vi Cleanup
- Lệnh `force-stop` và `KEYCODE_HOME` chỉ được thực thi **BÊN TRONG** context manager `with lock:` sau khi đã hoàn tất tác vụ dọn dẹp.
- **CẤM** đặt lệnh `force-stop` trong khối `finally` bên ngoài `DeviceLock`, vì nó sẽ chạy kể cả khi acquire lock thất bại hoặc máy đang bận.

### Quy tắc 5: Preflight bảo vệ Feed Runner
- Luôn kiểm tra `is_feed_runner_active()` ở đầu hàm `main()`. Nếu phát hiện runner nuôi feed đang hoạt động thì abort an toàn (`return 0`), không can thiệp.
