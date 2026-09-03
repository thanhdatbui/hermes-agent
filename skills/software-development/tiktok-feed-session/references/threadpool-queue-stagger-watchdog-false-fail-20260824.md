# ThreadPoolExecutor Queue Stagger Watchdog False-Fail Triage

## Hiện tượng (Symptom)
- Bot Telegram bắn alert: `🚨 [MÁY XX] DỪNG PHIÊN | multi-machine-feed-session | hard outer watchdog timeout exceeded (35.1m > 35.0m) | 🟡 GIỮ HIỆN TRƯỜNG`.
- Ảnh đính kèm hoặc inspect màn hình thiết bị: TikTok feed hiển thị bình thường, không có blocker/popup kẹt.
- Đọc `run_manifest.json` trong thư mục artifact của máy con (`machines/machine_XX/YYYYMMDD-HHMMSS/`): `final_status: success`, `total_swipes_completed` đạt chỉ tiêu (ví dụ 10–11 swipes), tài khoản khớp.

## Nguyên nhân gốc (Root Cause)
1. **Xếp hàng trong ThreadPoolExecutor (Queue Wait Time):**
   - Khi ca chạy có số lượng máy lớn hơn `max_workers` (ví dụ: 72 máy với `max_workers = 40`), sẽ có 32 máy thuộc đợt 2 (wave 2) phải nằm chờ trong hàng đợi của `ThreadPoolExecutor`.
   - Thời gian chờ luồng rảnh của wave 2 có thể kéo dài 20–23 phút.
2. **Gán mốc Watchdog sai thời điểm (`start_mono` at submit):**
   - Trong `python_runner/flows/multi_machine_feed_session.py`:
     ```python
     future = executor.submit(_run_child, ctx, account, resolved_adb or fallback_adb, reservation)
     futures[future] = (account, reservation, time.monotonic())
     ```
   - Mốc `time.monotonic()` được gán ngay lúc `submit()` (thời điểm đưa job vào hàng đợi), thay vì lúc worker con thực sự được thread pool nhấc lên thực thi.
3. **Kích hoạt Watchdog oan:**
   - Watchdog vòng lặp cha tính: `elapsed = now_mono - futures[future][2]`.
   - `elapsed` = `queue_wait_time (~20m)` + `actual_run_time (~15m)` = `~35m > 35.0m (worker_hard_timeout)`.
   - Vòng lặp cha tưởng nhầm worker bị treo, tự hủy future, ghi đè status thành `failed` với stop_reason `hard outer watchdog timeout exceeded`, và bắn alert Telegram báo lỗi sai (False-Fail).
   - Trong khi đó, worker thực tế dưới nền vẫn chạy bình thường và hoàn thành phiên thành công sau đó vài phút.

## Quy trình đối soát & điều tra (Triage Checklist)
1. Không can thiệp thiết bị hoặc reboot live khi thấy alert watchdog.
2. Mở `run_manifest.json` và `log.jsonl` tại artifact của máy con:
   - Kiểm tra `start_time` và `end_time` của child runner.
   - So sánh khoảng cách giữa thời điểm batch submit (`batch start_time`) với thời điểm child thực sự gọi `startup/start_runner`.
3. Kiểm tra số lượng máy bị dính timeout: nếu rơi vào một loạt máy ở nửa sau của `machine_launch_order` (wave 2) với `elapsed ~ 35m`, xác nhận 100% là ThreadPoolExecutor Queue Watchdog False-Fail.

## Quy tắc sửa code (Fix Contract)
- Mốc bắt đầu tính timeout của `worker_hard_timeout` **bắt buộc phải là thời điểm worker con thực sự bắt đầu chạy** (bên trong `_run_child` hoặc qua state tracking object / thread callback), tuyệt đối không đo thời gian từ lúc `executor.submit()`.
- Queue wait time không được tính vào quota thời gian chạy của thiết bị.
