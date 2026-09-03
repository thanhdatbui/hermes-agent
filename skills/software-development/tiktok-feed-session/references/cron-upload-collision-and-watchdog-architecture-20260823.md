# Cron Feed vs Manual Batch Upload Collision & Lease Auto-Reap (2026-08-23)

## 1. Xung đột Cron Feed và Manual Batch Upload
- **Hiện tượng:** Khi chạy batch đăng video thủ công (`run_tiktok_upload_batch.ps1`), cron nuôi feed `phase9-runner-tiktok-feed` đến chu kỳ tick 15 phút vẫn kích hoạt feed session trên cùng các máy đó.
- **Hệ quả:** 2 tiến trình chạy song song tranh chấp thiết bị: script upload đang ở màn hình biên tập video / CapCut thì script feed nhảy vào tap tìm tab Profile -> văng lỗi `navigation target profile not found in XML` và báo alert đỏ về Telegram Farm Alerts.
- **Quy tắc vận hành:** 
  - Trước khi chạy batch Upload độc lập, phải tạm dừng cron feed: `cronjob(action='pause', job_id='cdd43b124363')`.
  - Sau khi batch Upload hoàn tất, bật lại cron: `cronjob(action='resume', job_id='cdd43b124363')`.
  - Khi user ra lệnh chạy batch upload thủ công: Để batch chạy tự nhiên liên tục cho đến khi hoàn thành 100% danh sách máy, tuyệt đối không tự ý ngắt hay dừng giữa chừng.

## 2. Bảo vệ 2 lớp chống treo / kẹt tiến trình nuôi feed
- **Lớp 1 (Tầng Flow - `multi_machine_feed_session.py`):**
  - Không dùng `future.result()` chờ vô hạn.
  - Sử dụng vòng lặp `wait(pending_futures, timeout=5.0, return_when=FIRST_COMPLETED)` kết hợp **hard outer watchdog timeout (30 phút/máy)**.
  - Khi một worker bị deadlock ADB/UI quá 30 phút, watchdog tự động bứt future ra khỏi hàng đợi, đánh dấu `failed` với `hard outer watchdog timeout exceeded`, ghi log và gửi cảnh báo Farm Alerts, giải phóng để process cha tổng kết và thoát sạch sẽ.
- **Lớp 2 (Tầng Cron Runner - `tiktok_runner.py`):**
  - `_lease_alive()` tự động dọn sạch file lease stale (`runner-live-lease/<day>.json`) nếu thời gian bắt đầu đã vượt quá **90 phút** hoặc PID đã chết.
  - Ngăn chặn triệt để tình trạng cron bị skip `already running — skipping` liên tục nhiều tiếng.

## 3. Sửa module gọi Upload Hook
- Lệnh gọi sub-process upload trong `multi_machine_feed_session.py`:
  - SAI: `python -m tiktok_workflow` (lỗi `No module named tiktok_workflow`).
  - ĐÚNG: `python -m scripts.tiktok_workflow` (vì package `tiktok_workflow` nằm trong thư mục `scripts/` của repo `tiktok-video`).

## 4. Tắt Follow Hook chống nhả follow (23/08)
- Theo chỉ đạo của Operator, toàn bộ các Row (1, 2, 3+) tạm dừng follow chéo, trả về `reason: follow-disabled-by-operator`. Chỉ tập trung nuôi feed và đăng video để tránh thuật toán TikTok nhả follow.
