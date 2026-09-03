# Hook Upload Subprocess Concurrency & CLI Contract Guidelines

## 1. Concurrency Bottleneck khi tích hợp Feed và Upload
- Khi flow nuôi nick (`multi_machine_feed_session.py`) chạy song song 40 workers:
  - Ở **Phiên 3** (phiên cuối ca nuôi), các worker sau khi lướt feed xong sẽ gọi hook upload.
  - Nếu không có cơ chế throttle riêng, 40 tiến trình upload con được spawn đồng loạt (`subprocess.run`), gửi hàng loạt lệnh ADB/ATX nặng (media push, dump XML, portrait lock) đè nghẽn ADB server chung (port 5037) và ATX agent trên thiết bị.
  - **Quy tắc:** Bắt buộc giới hạn concurrency cho riêng hook upload ở mức **16 workers song song** (dùng `threading.BoundedSemaphore(16)` hoặc queue tương đương), khớp đúng chuẩn `$MaxParallel = 16` của script batch gốc `run_tiktok_upload_batch.ps1`.

## 2. CLI Invocation Contract từ Consumer
- Khi gọi subprocess sang repo `Tiktok-video` (`python -m scripts.tiktok_workflow`):
  - **Truyền trực tiếp target:** Dùng `--single-device <serial>` thay vì `--machine <number>`. Truyền serial giúp bỏ qua bước load workbook scan lại từ đầu, tránh tranh chấp và binding sai row/serial.
  - **Truyền số video đã preflight:** Dùng `--video-number <next_video>` để script upload biết chính xác số thứ tự video cần đăng.
  - **Kích hoạt recovery có giới hạn:** Bổ sung `--allow-device-reboot-recovery` và `--no-dry-run` để thực thi live có ladder recovery chuẩn.

## 3. Post-Verification & Evidence Handling
- **Tên biến verify:** Sử dụng biến `next_video` (không dùng biến nhầm `next_video_num`) khi đối chiếu với `rep_video_num` trong `report.json`.
- **Capture timeout evidence:** Khi subprocess dính `TimeoutExpired` (ngưỡng 1200s), bắt buộc lưu lại `stdout_tail`, `stderr_tail`, và `queue_wait_seconds` vào `upload_result.json` và log JSONL để phân biệt nghẽn hàng đợi với treo UI thực tế.
