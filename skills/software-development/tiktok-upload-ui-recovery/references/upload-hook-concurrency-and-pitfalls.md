# Upload Subprocess Concurrency & Invocation Pitfalls

## 1. Concurrency Bottleneck khi chạy từ Feed Worker
- **Bối cảnh:** Feed session chạy song song 40 workers (ThreadPoolExecutor). Ở Phiên 3, các worker hoàn tất feed sẽ tự động kích hoạt `_run_upload_hook`.
- **Triệu chứng:** Hàng chục subprocess `python -m scripts.tiktok_workflow` spawn đồng thời, ồ ạt gửi lệnh media push, portrait enforce, screenshot, dump XML qua ADB port 5037 -> ADB server nghẽn, child process không kịp hoàn tất trong budget 1200s, sinh ra lỗi `upload-timeout` trên diện rộng.
- **Giải pháp chuẩn:** Phải bọc hook upload trong semaphore độc lập `DEFAULT_UPLOAD_MAX_CONCURRENCY = 16` (`_upload_concurrency_lease`), tái hiện đúng mức `$MaxParallel = 16` của script batch upload gốc.

## 2. Subprocess CLI Parameter Binding
- **Tránh dùng:** `--machine <N>` khi gọi upload workflow từ feed hook, vì script upload sẽ phải đọc lại workbook từ đầu để resolve serial, dễ gây delay hoặc sai lệch row trong batch lớn.
- **Bắt buộc dùng:**
  - `--single-device <serial>` (bind trực tiếp ADB serial đã xác minh)
  - `--video-number <next_video>` (chỉ định video number chính xác)
  - `--allow-device-reboot-recovery` (bật recovery ladder khi OPEN_TIKTOK retry)
  - `--no-dry-run` (chạy thật)

## 3. Post Verification Contract
- Đối chiếu biến `next_video` (không dùng biến nhầm `next_video_num`) với `rep_video_num` từ `report.json`.
- Khi timeout, luôn ghi `stdout_tail`, `stderr_tail` và `queue_wait_seconds` vào artifact để phân biệt kẹt hàng đợi với lỗi UI.
