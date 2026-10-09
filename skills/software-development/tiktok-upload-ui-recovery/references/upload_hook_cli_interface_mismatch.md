# Lỗi Lệch Interface CLI Argument Giữa Feed Session Hook và Upload Subprocess

## 1. Hiện tượng & Chữ ký lỗi (Signature)
Khi chạy batch hoặc phiên nuôi nick kết hợp đăng video (`multi-machine-feed-session`), 100% các máy có lịch đăng video đồng loạt thất bại ở bước Đăng Video với exit code 2:
- Báo cáo Watchdog: `Lỗi script/xác minh (N máy)` (0 video đã đăng).
- File `upload_result.json` tại `D:\Taadaa\runtime\kibe\live\<date>\<shift>\machines\machine_<N>\<timestamp>\upload_result.json`:
```text
"reason": "__main__.py: error: argument command: invalid choice: 'D:\\\\TIKTOK-videonuoinick' (choose from None, 'reconcile-stale-upload-locks')",
"returncode": 2,
"status": "failed"
```

## 2. Nguyên nhân gốc rễ
- **Caller (`multi_machine_feed_session.py`)**: Trong `_run_upload_hook()`, lệnh gọi subprocess thực thi `python -m scripts.tiktok_workflow` được thêm tham số mới (ví dụ `--video-source-root <path>`).
- **Callee (`run_post.py` của `Tiktok-video`)**: Trong hàm `build_parser()`, `argparse` chưa đăng ký tham số `--video-source-root`, nhưng lại có một positional argument `command` với `choices=(None, "reconcile-stale-upload-locks")`.
- Khi `argparse` gặp cờ không khai báo đi kèm giá trị không có tiền tố `--`, giá trị đường dẫn (`D:\TIKTOK-videonuoinick`) bị gán nhầm vào positional argument `command` $\rightarrow$ sinh ra lỗi `invalid choice: ...` và crash ngay lập tức trước khi chạm vào ADB/thiết bị.

## 3. Cách khắc phục chuẩn
1. **Tại callee (`run_post.py`)**: Bổ sung argument tương ứng vào `build_parser()`:
```python
parser.add_argument(
    "--video-source-root",
    help="Override video source root directory (defaults to config video_source_root)",
)
```
Và cập nhật cấu hình override khi parse args:
```python
if getattr(args, "video_source_root", None):
    override_vsr = args.video_source_root.strip()
    if not override_vsr:
        print("Video source root override must not be blank", file=sys.stderr)
        return 1
    config._data["video_source_root"] = override_vsr
```
2. **Kiểm tra verification**:
Chạy focused test kiểm tra parse_args với mẫu lệnh gọi đầy đủ từ caller, đảm bảo exit code = 0, `args.video_source_root` nhận đúng đường dẫn và `args.command is None`.
