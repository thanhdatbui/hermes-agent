# Investigation & Recovery Guide: upload_subprocess_nonzero

## 1. Triệu chứng & Vị trí Log Trực tiếp
Khi Farm Alert báo lỗi `upload_subprocess_nonzero` (exit code 1 hoặc non-zero) cho Máy N:
- **CẤM** dùng `os.walk`, `find`, `grep -r` quét diện rộng ổ đĩa.
- **Đọc trực tiếp** file `upload_result.json` tại đường dẫn chuẩn của batch run:
  `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<ROW>-<time>/<timestamp>/machines/machine_<N>/<timestamp>/upload_result.json`

File JSON này chứa:
- `exit_code` / `returncode`: Mã lỗi trả về từ tiến trình con.
- `reason`: `"upload_subprocess_nonzero"`
- `workbook`: Tên file workbook tương ứng (ví dụ `Tik4.xlsx`).
- `stderr_tail`: Traceback lỗi chi tiết của Python (ví dụ `IndentationError`, `ImportError`, unhandled exception trước khi vào StateMachine).

## 2. Quy trình Recovery 5 Bước
1. **B1 (Inspect Máy):**
   `python D:/Taadaa/tools/inspect_machine.py <N>`
   Kiểm tra thiết bị ADB online và phản hồi.

2. **B2 (Root Cause):**
   Đọc `stderr_tail` trong `upload_result.json` để xác định chính xác file/dòng bị lỗi.

3. **B3 (Codebase & Focused Test):**
   - Sửa lỗi cú pháp hoặc logic trong `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/`.
   - Kiểm tra compile toàn bộ module: `python -m compileall scripts/tiktok_workflow`.
   - Chạy focused test lock: `pytest tests/test_tiktok_workflow.py -k "<TargetTest>"` (CẤM chạy pytest trần cả repo).

4. **B4 (Canary Test):**
   Chạy lệnh thực tế trên máy gặp lỗi:
   ```bash
   python -m scripts.tiktok_workflow --config "D:\Taadaa\Tiktok-video\config.example.yaml" --workflow-workbook "D:\OneDrive\TaadaaData\kibe\Tik<X>.xlsx" --single-device <SERIAL> --video-number 1 --no-dry-run
   ```
   *Lưu ý:* Khi chạy qua subshell không có TTY tương tác, cờ `--no-dry-run` tự động chọn `confirmation = "YES"`.

5. **B5 (Closeout):**
   - Đọc `report.json` tại `D:/CodexRuntime/tiktok-video/runs/run_<SERIAL>_<TIMESTAMP>/report.json` kiểm tra `"status": "SUCCESS"`.
   - Kiểm tra ô `Video Đã Đăng` trong workbook `Tik<X>.xlsx` đã tăng thành công.
   - Báo cáo git diff, kết quả test và kết quả canary.
