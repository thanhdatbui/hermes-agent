# Watchdog Upload Concurrency & False-Positive Prevention Guide

## Sự cố ghi nhận (2026-09-19)
- **Hiện tượng**: Báo cáo tổng kết ca từ watchdog (`feed_session_watchdog.py`) thông báo hàng loạt máy bị `Lỗi script/xác minh` ở bước **Đăng Video** (18 máy: M2, M13, M16, M20, M41, M42, M43, M47, M49, M50, M51, M52, M59, M60, M63, M71, M72, M79).
- **Thực tế đối soát hiện trường**:
  - Có tới **11/18 máy** (M2, M42, M43, M47, M49, M51, M52, M59, M60, M63, M79) đã đăng video hoàn toàn thành công (`status: success`, `exit_code: 0`, file log xác nhận `Workflow completed successfully`).
  - Chỉ có **7 máy** gặp lỗi thật (M13, M16 kẹt UI xác minh; M20, M41, M50, M71, M72 thiếu account trong switcher).

## Nguyên nhân gốc rễ (Root Cause)
1. **Lệch pha giữa Feed hoàn tất và Upload Subprocess**:
   - Tiến trình nuôi acc chạy `multi_machine_feed_session.py`. Mỗi worker sau khi feed xong mới gọi upload hook chạy độc lập qua subprocess (`D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/run_post.py`).
   - Bước upload chọn video, viết caption, đăng bài và verify mất thêm 5-10 phút trên từng máy.
2. **Watchdog chốt báo cáo sớm**:
   - Điều kiện `can_report_session()` kiểm tra `completed_expected_count >= expected_count`. Chỉ số này chỉ đếm các máy đã hoàn thành **Feed**, không đại diện cho việc **Upload** đã xong.
   - Hàm `can_report_session()` có nhánh chốt ngay kể cả khi `runner_busy` nếu `completed_expected_count >= expected_count`.
   - Hàm `is_feed_runner_active()` thiếu hoàn toàn các patterns nhận diện tiến trình upload (`run_post.py`, `tiktok_workflow`, `tiktok_upload`).
3. **Logic Fallback phân loại nhầm thành lỗi**:
   - Khi watchdog quét tại thời điểm chốt (07:10), các máy đang upload dở chưa kịp ghi file `upload_result.json`.
   - Đoạn fallback kiểm tra:
     ```python
     elif all_machines[m].get("status") == "success":
         up_error.append(m)
     ```
     đã tự động gán toàn bộ máy lướt Feed xong nhưng chưa có kết quả upload thành `up_error`.

## Quy tắc bắt buộc khi bảo trì Watchdog
1. **Bao phủ đầy đủ Pattern tiến trình con**:
   Trong `is_feed_runner_active()`, bắt buộc phải có:
   ```python
   runner_patterns = (
       "multi_machine_feed_session",
       "multi-machine-feed-session",
       "run-feed-session.ps1",
       "run_follow",
       "run_tiktok.py",
       "hermes_cron_runner.py",
       "tiktok_runner.py",
       "run_post.py",
       "tiktok_workflow",
       "tiktok_upload",
   )
   ```
2. **Bất biến không chốt sớm khi còn tiến trình bận**:
   Trong `can_report_session()`:
   ```python
   if is_today and runner_busy:
       return False
   ```
   Chừng nào còn máy đang chạy hoặc còn tiến trình uploader/runner trong ngày, tuyệt đối không được chốt báo cáo phiên.
3. **Đối soát mtime trước khi kết luận**:
   Trước khi kết luận máy bị lỗi upload, bắt buộc kiểm tra sự tồn tại và mtime của file:
   `D:/Taadaa/runtime/kibe/live/<date>/<run>/machines/machine_<N>/<timestamp>/upload_result.json`.
