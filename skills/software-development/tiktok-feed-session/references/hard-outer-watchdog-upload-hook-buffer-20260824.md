# Hard Outer Watchdog Timeout Budget & Upload Hook Interaction (2026-08-24)

## 1. Hiện tượng & Bối cảnh
- **Alert:** `[MÁY XX] DỪNG PHIÊN • Lý do: hard outer watchdog timeout exceeded (15.1m > 15.0m) • Trạng thái: GIỮ HIỆN TRƯỜNG`.
- **Bối cảnh:** Sau khi triển khai Fast Swipe xen kẽ Deep Inspect, thời gian lướt feed rút ngắn còn 3–5 phút. Một bản vá trước đó đã hạ `DEFAULT_DEVICE_TIMEOUT_SECONDS` từ 1500s/1800s xuống 600s (10 phút), khiến `worker_hard_timeout` (`timeout_seconds + 300.0s`) bị co lại còn đúng 900s (15 phút).

## 2. Root Cause
- Mỗi worker trong `multi_machine_feed_session.py` không chỉ chạy `feed_session_smoke` mà còn tuần tự thực thi:
  1. `prepare_tiktok_for_smoke` & ADB preflight (~30s).
  2. `feed_session_smoke` (Fast Swipe + Deep Inspect + Profile Verify + Cleanup) (~3–6 phút).
  3. `_run_follow_hook` (nếu có follow chéo).
  4. `_run_upload_hook` (chạy subprocess `scripts.tiktok_workflow` upload video lên TikTok, timeout của subprocess upload tối đa 900s / 15 phút).
- Khi máy 35 hoàn tất lướt feed thành công sau 5 phút và bước vào `_run_upload_hook`, tiến trình upload video chạy mất ~10 phút. Tổng thời gian thực thi của worker vượt qua 15.0 phút và bị Hard Outer Watchdog ở tiến trình cha (`multi_machine_feed_session`) phát hiện timeout và abort nhầm.

## 3. Quy chuẩn cấu hình Timeout
- `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` (25 phút).
- `worker_hard_timeout = timeout_seconds + 300.0` = **1800.0s (30 phút)**.
- **Quy tắc:** Tuyệt đối không hạ `DEFAULT_DEVICE_TIMEOUT_SECONDS` xuống dưới 1500s khi hệ thống đang bật follow hook hoặc upload hook, vì thời gian upload video qua giao diện TikTok cần buffer từ 10–15 phút.
