# Upload Subprocess CLI Schema Mismatch

## Hiện tượng
Báo cáo watchdog ca nuôi nick (feed session watchdog) ghi nhận toàn bộ máy đến lượt đăng video bị fail:
`Lỗi script/xác minh (N máy)` (ví dụ: 46/46 máy fail, 0 video đăng thành công).

Kiểm tra `upload_result.json` tại `D:\Taadaa\runtime\kibe\live\<date>\<session>\machines\machine_<N>\<session>\upload_result.json`:
```json
{
  "exit_code": 2,
  "status": "failed",
  "reason": "__main__.py: error: argument command: invalid choice: 'D:\\\\TIKTOK-videonuoinick' (choose from None, 'reconcile-stale-upload-locks')"
}
```

## Nguyên nhân
- Lỗi không tương thích CLI schema giữa repo gọi (`tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`) và repo thực thi (`Tiktok-video/scripts/tiktok_workflow/run_post.py`).
- Caller truyền thêm cờ `--video-source-root <path>`, trong khi parser của `run_post.py` không khai báo option này và có positional argument `command` (`choices=(None, "reconcile-stale-upload-locks")`).
- Argparse gán chuỗi path vào `command` và quăng error invalid choice, thoát ngay với exit code 2 trước khi kết nối thiết bị.

## Hướng dẫn chẩn đoán O(1)
- Không mất thời gian probe UI/ADB trên thiết bị khi thấy toàn bộ máy đăng video đều fail trong một batch.
- Đọc ngay `upload_result.json` của 1 máy để kiểm tra `exit_code` và `reason`. Nếu là lỗi `argparse` / `exit_code: 2`, nguyên nhân là mismatch CLI giữa feed runner và upload runner.
