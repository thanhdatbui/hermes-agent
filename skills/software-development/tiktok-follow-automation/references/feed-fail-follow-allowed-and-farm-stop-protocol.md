# Feed Failure Follow Policy & Farm-wide Emergency Stop Protocol

## 1. Feed Failure Does Not Block Follow Hook (2026-08-30)
- **Quy tắc:** Kể cả khi phiên lướt Feed thất bại (timeout, swipe stuck, UI drift), runner VẪN ĐƯỢC PHÉP chuyển tiếp gọi `_run_follow_hook` bình thường.
- **Vị trí áp dụng:** `python_runner/flows/multi_machine_feed_session.py` (`_run_child`).
- **Lý do:** Tách biệt lỗi phân phối nội dung của Feed với hành động tương tác Follow; máy gặp sự cố cuộn Feed không bị mất quyền chạy follow chéo của nick trong ca.

## 2. Farm-wide Stop & Verification Protocol ("Tạm dừng all máy")
- **Yêu cầu:** Tuyệt đối không chỉ gửi lệnh mù quáng rồi báo cáo chay.
- **Quy trình 3 bước bắt buộc:**
  1. **Kill Host Processes:** Quét và kill sạch process `run_tiktok`, `multi_machine_feed_session`, `tiktok_workflow`, `pytest`.
  2. **Force-stop App:** Gửi lệnh `am force-stop com.ss.android.ugc.trill`, `am force-stop com.zhiliaoapp.musically` và phím `HOME` (`input keyevent 3`) song song qua pool workers tới toàn bộ online devices.
  3. **Hậu kiểm Focus thực tế (100% Online Devices):** Chạy `dumpsys window windows | grep mCurrentFocus` trên toàn bộ thiết bị để xác nhận 0 máy nào còn giữ TikTok ở foreground trước khi báo cáo kết quả cho user.

## 3. Watchdog Classification Contract
- **Quy tắc phân loại:** Watchdog (`feed_session_watchdog.py`) chỉ được đếm "Lỗi script/xác minh" nếu máy đã lướt Feed thành công (`status == "success"`) mà Follow hook bị exception/không sinh kết quả.
- **Trường hợp loại trừ:** Máy bị lock thiết bị hoặc không chạy Feed tuyệt đối KHÔNG được tính vào danh sách lỗi script của Follow.
