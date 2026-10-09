# Diagnostic & Recovery: Upload Hook CLI Positional Argument Clash

## Hiện tượng
- User phản ánh: "Đăng video lỗi lắm v".
- Cronjob Watchdog báo cáo: 46 máy cần đăng video đều rơi vào "Lỗi script/xác minh" (0 video được đăng).
- Chi tiết file `upload_result.json` của toàn bộ máy trong ca nuôi nick:
  `__main__.py: error: argument command: invalid choice: 'D:\\TIKTOK-videonuoinick' (choose from None, 'reconcile-stale-upload-locks')`

## Nguyên nhân
- Caller `multi_machine_feed_session.py` bổ sung argument `--video-source-root <path>` khi gọi runner subprocess `scripts.tiktok_workflow`.
- Callee `run_post.py` chưa khai báo `--video-source-root` trong `build_parser()`. Do parser có positional argument `command`, `argparse` gán giá trị đường dẫn vào `command` và báo lỗi `invalid choice`, thoát với exit code 2.

## Khắc phục & Nghiệm thu
1. Khai báo `--video-source-root` trong `run_post.py`:
   ```python
   parser.add_argument(
       "--video-source-root",
       help="Override video source root directory (defaults to config video_source_root)",
   )
   ```
2. Gán override trong `main()`:
   ```python
   if getattr(args, "video_source_root", None):
       override_vsr = args.video_source_root.strip()
       if not override_vsr:
           print("Video source root override must not be blank", file=sys.stderr)
           return 1
       config._data["video_source_root"] = override_vsr
   ```
3. Test focused: `pytest tests/test_run_post_cli_args.py -v` hoặc chạy `--preflight`.
