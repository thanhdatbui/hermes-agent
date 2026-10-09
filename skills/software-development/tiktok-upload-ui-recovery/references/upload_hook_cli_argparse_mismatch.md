# Upload Hook CLI Argparse Mismatch (Exit code 2)

## Hiện tượng
Trong báo cáo watchdog cron (`tiktok-feed-session-watchdog`):
- Toàn bộ máy trong ca đến lượt Đăng video đồng loạt báo: **`Lỗi script/xác minh (N máy)`** (ví dụ 46/46 máy fail, 0 video được đăng).
- Kiểm tra `upload_result.json` tại `D:\Taadaa\runtime\kibe\live\<date>\<session>\machines\machine_<N>\<session>\upload_result.json` thấy:
  ```json
  {
    "exit_code": 2,
    "status": "failed",
    "reason": "__main__.py: error: argument command: invalid choice: 'D:\\\\TIKTOK-videonuoinick' (choose from None, 'reconcile-stale-upload-locks')"
  }
  ```

## Nguyên nhân
- Subprocess CLI mismatch giữa caller (`multi_machine_feed_session.py`) và callee (`scripts.tiktok_workflow` / `run_post.py`).
- Khi caller thêm flag CLI không có trong `argparse` của callee (ví dụ: `--video-source-root <path>`), nhưng callee có positional argument `command` (để nhận `reconcile-stale-upload-locks`), argparse sẽ gom chuỗi giá trị path phía sau vào positional argument `command`.
- Do `choices=(None, "reconcile-stale-upload-locks")`, argparse từ chối và crash ngay lập tức với exit code 2 trước khi kết nối thiết bị.

## Quy trình xử lý O(1)
1. **Kiểm tra nhanh O(1)**: Đọc `upload_result.json` của 1 máy bất kỳ. Nếu thấy `exit_code: 2` và `invalid choice: ...`, kết luận ngay lỗi CLI schema, không cần probe ADB hay reset máy.
2. **Khắc phục**:
   - Hoặc gỡ cờ không được hỗ trợ trong lệnh gọi subprocess tại `multi_machine_feed_session.py`.
   - Hoặc thêm argument tương ứng vào `run_post.py` của `tiktok_workflow` nếu muốn hỗ trợ override CLI.
