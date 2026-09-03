# Scoped row follow/upload re-enable — 2026-08-23

## Đã xác minh
- Cron job `phase9-runner-tiktok-feed` chạy wrapper `tiktok_runner.py` mỗi 15 phút.
- Wrapper spawn `scripts/run-feed-session.ps1` theo `account_row` từ active manifest.
- Consumer gọi độc lập `_run_follow_hook(...)` và `_run_upload_hook(...)` sau feed session success/degraded.
- Trạng thái tạm dừng global nằm ngay đầu hai hook; thay đổi đúng scope là gate physical `account_row_index in (1, 2)`.

## Policy đã encode
- Row 1/2: được qua gate row để tiếp tục runner.
- Row 3+: skip follow với `follow-disabled-outside-row-1-2`.
- Row 3+: skip upload với `upload-disabled-outside-row-1-2`.
- Các gate sau đó vẫn giữ nguyên; đặc biệt nick 0 video vẫn bị skip follow, sensitive stop vẫn skip, upload vẫn chỉ ở final session và yêu cầu workbook/media.

## Verification lesson
- `multi_machine_feed_session.py` compile được.
- Focused test collection bị chặn bởi `IndentationError` có sẵn trong `python_runner/flows/feed_swipe_smoke.py:15029` (thiếu indent sau `if retry_profile_xml:`), thuộc dirty change ngoài phần row gate.
- Không được tự sửa blocker ngoài scope hoặc báo live cron đã chạy thành công khi chưa có artifact child run xác nhận.
