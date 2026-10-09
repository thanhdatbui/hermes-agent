# Pitfall: False Positive Upload Errors Do Watchdog Chốt Phiên Sớm

## 1. Hiện tượng
Báo cáo watchdog tổng kết ca/phiên hiển thị hàng chục máy bị `Lỗi script/xác minh` ở mục Đăng Video (`up_error`), trong khi thực tế trên máy các tiến trình upload (`run_post.py`) vẫn đang đăng bình thường và thành công sau đó vài phút.

## 2. Nguyên nhân
1. `is_feed_runner_active()` chỉ bắt các pattern của feed (`multi_machine_feed_session`, `run-feed-session.ps1`, `tiktok_runner.py`), thiếu các process upload con (`run_post.py`, `tiktok_workflow`, `tiktok_upload`). Khi feed vừa xong, runner chính kết thúc nhưng upload workers vẫn chạy nền.
2. Watchdog quét khi file `upload_result.json` chưa kịp ghi và gán ngay các máy lướt feed thành công nhưng chưa có file upload thành `up_error`.

## 3. Quy tắc xử lý
1. `is_feed_runner_active()` bắt buộc phải bao gồm cả các tiến trình uploader: `"run_post.py"`, `"tiktok_workflow"`, `"tiktok_upload"`.
2. Tuyệt đối không chốt báo cáo sớm khi `runner_busy=True` và chưa hết giờ phiên hoặc chưa hoàn tất toàn bộ số máy dự kiến.
3. Khi test `can_report_session`, đảm bảo phân biệt rõ:
   - `completed_expected_count >= expected_count and not has_unattempted_locked`: Đã xong toàn bộ -> cho phép chốt.
   - Chưa hoàn tất máy mà `runner_busy=True`: Luôn chặn chốt sớm (`return False`).
