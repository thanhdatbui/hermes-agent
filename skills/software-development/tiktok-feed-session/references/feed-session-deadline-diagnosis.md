# Chẩn đoán lỗi `run plan max_duration_seconds exceeded`

## 1. Bản chất & Cơ chế Deadline
- Trong `python_runner/flows/multi_machine_feed_session.py`:
  - Mỗi child worker thiết lập deadline: `child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds`.
  - Mặc định: `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` (25 phút).
- Khi chạm mốc deadline, hàm `ensure_run_plan_deadline(ctx.config, ...)` ném ngoại lệ `RunPlanDeadlineExceeded` với message dạng:
  `run plan max_duration_seconds exceeded before capture swipe_XX_after attempt 1` hoặc `... before feed swipe XX after watch delay`.

## 2. Phân tích định lượng thời gian chạy thực tế
Trên dàn máy điện thoại thật (Samsung Galaxy S7 / Android Box):
- **Preflight & Navigation ban đầu:** ~120s – 180s (mở app TikTok, kiểm tra profile identity/account switcher, tap về Home tab).
- **Mỗi chu kỳ Swipe:**
  - Watch delay ngẫu nhiên: 2s – 8s.
  - Thao tác swipe ADB + sleep animation: ~1s – 2s.
  - Dump UI XML qua ATX/ADB để kiểm tra trạng thái màn hình: ~10s – 25s (tùy tốc độ máy và kích thước cây UI).
  - Quét danh sách blind probe popups (20+ pattern popup): ~5s – 15s.
  - **Tổng trung bình mỗi swipe:** ~35s – 55s/video.
- **Hệ quả với target 30 video:**
  - `30 swipes * 45s = 1350s` (~22.5 phút) + `150s preflight` = **~1500s (~25 phút)**.
  - Do đó, các máy xử lý UI chậm hoặc gặp video nhiều popup sẽ dễ dàng chạm trần 1500s ở các swipe thứ 20 đến 29.
- **Hệ quả khi dính chuỗi lag mạng / loading chậm (`manual-needed:network`):**
  - Mỗi khi gặp màn hình xoay vòng / loading, script kích hoạt full chain an toàn: duyệt 20+ blind popup probes (~10s) -> bấm back -> re-check 2 lần dump XML/screenshot (~30s) -> chạy `swipe_recovery_on_stuck` (~20s).
  - Thời gian mỗi swipe bị đội từ ~40-45s lên tới **~105s (~1.75 phút)**.
  - Nếu gặp 5–6 video lag mạng liên tiếp, chỉ riêng recovery đã tốn thêm 10–12 phút, khiến phiên dù chỉ đặt trần 17–18 video vẫn cạn sạch 25 phút (1500s) và chạm trần deadline ở swipe 16–17.

## 3. Quy trình kiểm tra & Đối soát log thực tế
1. Định vị thư mục log của run live:
   `D:\Taadaa\runtime\kibe\live\YYYY-MM-DD\row-X-HHMMSS\machines\machine_XX\YYYYMMDD-HHMMSS\`
2. Đọc file `log.jsonl`:
   - Lấy timestamp dòng đầu tiên: `step="startup", action="start_runner"`
   - Lấy timestamp dòng ngắt phiên: `action="deadline_exceeded"`
   - Tính hiệu số giữa 2 mốc thời gian. Nếu đúng bằng 1500s (± vài giây), xác nhận máy đã chạy hết toàn bộ 25 phút được cấp chứ không phải bị kẹt hay chạy code cũ (900s).
