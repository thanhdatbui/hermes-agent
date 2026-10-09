# Coordinator Dispatch Decomposition & Windows Subprocess Window Invariant

## 1. Coordinator Dispatch Decomposition (Anti-Timeout Discipline)
- **Cạm bẫy (Pitfall)**: Coordinator phát hiện một mẫu lỗi chung (pattern) trên 4+ file nằm rải rác ở nhiều repo/thư mục (`automation-core/scripts`, `hermes/scripts`), liền gộp chung cả 4 file vào 1 Worker prompt duy nhất.
- **Hậu quả**: Worker subagent cố gắng đọc, định vị và patch cả 4 file cùng lúc, nhanh chóng cạn budget iterations hoặc dính timeout 600s (`status=timeout, api_calls=15, 601.45s`).
- **Quy tắc điều phối bắt buộc (Gate 1 & Gate 3)**:
  1. Phân rã tối đa **1 đến 2 files per Worker subagent**.
  2. Cung cấp Patch Contract đóng với `old_string` -> `new_string` chính xác tuyệt đối (`grep -o ... | wc -l == 1`).
  3. Lệnh test focused < 30s (`python -m py_compile <path>`).

## 2. Invariant: Windows Subprocess Console Window Storm
- **Triệu chứng**: Người dùng thấy hàng loạt cửa sổ Command Prompt màu đen mang tiêu đề `C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc `adb.exe` chớp nháy liên hồi trên màn hình (console storm).
- **Nguyên nhân**: Script chạy ngầm từ `pythonw.exe` (Hermes Gateway, cron runner) gọi `subprocess.run()` hoặc `Popen()` tới console binary (`adb.exe`, `curl.exe`, `python.exe`) mà thiếu cờ `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`). Khi chạy đa luồng (`max_workers=20-30`), hàng chục cửa sổ bật tắt mỗi giây.
- **Quy chuẩn bắt buộc**:
  - Dùng helper:
    ```python
    def subp_run(*args, **kwargs):
        if os.name == "nt" and "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        return subprocess.run(*args, **kwargs)
    ```
  - Hoặc truyền cờ:
    ```python
    WIN_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    subprocess.run(cmd, ..., **WIN_KWARGS)
    ```
