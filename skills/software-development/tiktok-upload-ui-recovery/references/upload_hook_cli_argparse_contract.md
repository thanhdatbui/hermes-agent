# Upload Hook CLI Argparse Contract & Positional Command Clash

## Hiện tượng & Triệu chứng
- Khi chạy ca nuôi nick kèm đăng video (ví dụ Ca 2 Row 4), toàn bộ máy đến công đoạn hook upload đều crash ngay giây đầu tiên với `exit_code: 2`.
- Trong `upload_result.json`:
  ```text
  "reason": "__main__.py: error: argument command: invalid choice: 'D:\\\\TIKTOK-videonuoinick' (choose from None, 'reconcile-stale-upload-locks')",
  "returncode": 2
  ```

## Nguyên nhân gốc rễ
- Caller (`D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py`) gọi `scripts.tiktok_workflow` và truyền thêm cờ:
  `"--video-source-root", str(media_root)`
- Callee (`D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\run_post.py`) có định nghĩa positional argument:
  ```python
  parser.add_argument(
      "command",
      nargs="?",
      default=None,
      choices=(None, "reconcile-stale-upload-locks"),
  )
  ```
- Khi `run_post.py` chưa khai báo argument `--video-source-root`, `argparse` xử lý giá trị theo sau cờ lạ này như một positional argument và nuốt vào `command`.
- Do giá trị là đường dẫn thư mục video (không nằm trong choices `None` hay `reconcile-stale-upload-locks`), parser báo lỗi `invalid choice` và exit 2 ngay lập tức.

## Quy tắc & Khắc phục
1. **Đồng bộ Argument Parser:**
   Bất cứ khi nào caller truyền thêm tham số CLI mới cho subprocess cross-repo, parser của callee (`run_post.py`) bắt buộc phải khai báo đầy đủ tham số tương ứng trong `build_parser()`:
   ```python
   parser.add_argument(
       "--video-source-root",
       help="Override video source root directory (defaults to config video_source_root)",
   )
   ```
2. **Override cấu hình sau khi parse:**
   Trong `main()` của `run_post.py`, cập nhật lại dữ liệu config:
   ```python
   if getattr(args, "video_source_root", None):
       override_vsr = args.video_source_root.strip()
       if not override_vsr:
           print("Video source root override must not be blank", file=sys.stderr)
           return 1
       config._data["video_source_root"] = override_vsr
   ```
3. **Focused Verification Test:**
   Luôn kiểm tra lệnh gọi CLI qua test focused hoặc `--preflight`:
   ```bash
   python -m scripts.tiktok_workflow \
     --config "D:/CodexRuntime/tiktok-video/config-machine-13.yaml" \
     --workflow-workbook "D:/OneDrive/TaadaaData/kibe/Tik4.xlsx" \
     --single-device "<serial>" \
     --video-number 1 \
     --video-source-root "D:/TIKTOK-videonuoinick" \
     --preflight
   ```
   Xác nhận `returncode == 0` và không còn lỗi `argument command: invalid choice`.
