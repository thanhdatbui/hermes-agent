# Windows OpenSSH Breakaway Pattern for Remote Farm Dispatch

## Vấn Đề (OpenSSH Windows Job Object Termination Trap)
Khi host điều phối (Kibe) kích hoạt một tiến trình nền dài hạn trên remote host (Admin PC) qua lệnh OpenSSH (`admin_ssh.py`):
- OpenSSH Server trên Windows mặc định gom tất cả process con sinh ra vào chung một Windows Job Object của phiên SSH.
- Khi kết nối SSH đóng lại (kể cả đóng bình thường hay timeout), Windows tự động hủy (kill) toàn bộ tiến trình nằm trong Job Object đó.
- Cờ `subprocess.DETACHED_PROCESS` (`0x00000008`) **không đủ** để bảo vệ tiến trình khỏi việc bị kill khi SSH disconnect.

## Giải Pháp Chuẩn Hóa
BẮT BUỘC kết hợp cờ `CREATE_BREAKAWAY_FROM_JOB` (`0x01000000`):
```python
# 0x01000008 = CREATE_BREAKAWAY_FROM_JOB (0x01000000) | DETACHED_PROCESS (0x00000008)
proc = subprocess.Popen(
    [python_exe, "-u", "-X", "utf8", script_path, ...],
    cwd=workdir,
    stdout=f_out,
    stderr=subprocess.STDOUT,
    creationflags=0x01000008,
)
```
Tiến trình con sẽ tự động tách khỏi Job Object của OpenSSH và duy trì hoạt động liên tục cho đến khi hoàn thành nhiệm vụ.
