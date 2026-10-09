# Non-Interactive Stdin Prompt & Follow Timeout (Case UI-54)

## Triệu chứng
Farm Alert kích hoạt cảnh báo đỏ trên máy farm (ví dụ Máy 74, Ca Row 2, nick `phannhu185`):
```text
• Triệu chứng: follow-timeout (1200s / 20 phút)
• Hiện trường: GIỮ HIỆN TRƯỜNG FOLLOW TIMEOUT
```
Màn hình TikTok giữ nguyên ở Feed "Đề xuất", không hề phát sinh bất kỳ thao tác navigation hay tìm kiếm nào trong suốt 20 phút.

## Root Cause
Trong `follow_runner/run_follow.py`:
1. Khi parent feed runner (`multi_machine_feed_session.py`) kích hoạt follow-hook qua subprocess:
   `["python.exe", "run_follow.py", "--machine", "74"]`
   tiến trình con được gọi mà không truyền tham số `--account-row-index`.
2. Hàm `_prompt_account_row(source_mapping, machine, cfg, args)` kiểm tra nếu `args.account_row_index is None` thì gọi `input("Chọn account row..."):` để hỏi tương tác qua bàn phím CLI.
3. Trong môi trường background/headless subprocess (không có TTY attached):
   - Lệnh `input()` bị treo vĩnh viễn (stuck waiting on stdin).
   - Tiến trình con không thể tiếp tục thực thi, không bao giờ bắt đầu khởi tạo camera/navigation hay tìm kiếm.
   - Sau 1200.0s (20 phút timeout của follow hook), parent feed session bắn tín hiệu SIGKILL / timeout.
   - `follow_result.json` ghi nhận: `status: "timeout"`, `reason: "follow-timeout"`, `followed_count: 0`, `failed: 1`.

## Fix Pattern
Trong `follow_runner/run_follow.py` (`_prompt_account_row`):
1. **Kiểm tra TTY / stdin interactivity trước khi gọi `input()`**:
   ```python
   is_interactive = False
   try:
       is_interactive = bool(sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty())
   except Exception:
       is_interactive = False

   if not is_interactive:
       logger.warning(
           "Môi trường non-interactive (not sys.stdin.isatty()), tự động chọn default account row %s cho máy %s",
           default, machine,
       )
       return default
   ```
2. **Bắt `EOFError` phòng ngừa**:
   Nếu `isatty()` trả về True nhưng stdin pipe bị đóng giữa chừng (EOF):
   ```python
   try:
       raw = input(f"Chọn account row ({options_str}, default {default}): ").strip()
   except EOFError:
       logger.warning(
           "EOF trên stdin khi prompt account row, fallback về default account row %s cho máy %s",
           default, machine,
       )
       return default
   ```

## Focused Verification
- Thêm `test_live_path_non_interactive_stdin_fallback` trong `follow_runner/tests/test_cli.py`: Mock `sys.stdin.isatty` trả về `False`, mock `builtins.input` thành `pytest.fail()`, đảm bảo `input()` không bao giờ được gọi và trả về đúng `rows[0].account_row_index`.
- Thêm `test_live_path_eof_error_fallback`: Mock `input()` raise `EOFError`, đảm bảo fallback an toàn về `rows[0].account_row_index`.
- Cập nhật các test tương tác cũ để mock `sys.stdin.isatty` trả về `True`.
