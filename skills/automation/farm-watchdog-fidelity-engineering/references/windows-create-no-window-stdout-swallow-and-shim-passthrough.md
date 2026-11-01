# Windows CREATE_NO_WINDOW (0x08000000) Stdout Swallow & Forwarding Shim Passthrough

## 1. Triệu Chứng & Hiện Tượng (Phantom Silence)
- Script watchdog hoặc automation chạy trực tiếp bằng tay thì in đầy đủ báo cáo ra terminal, nhưng khi chạy qua Hermes Cron (`no_agent: true`) thì Telegram hoàn toàn im lặng cả ngày.
- File log cron tại `%LOCALAPPDATA%\hermes\cron\output\<job_id>\` sinh ra đều đặn nhưng luôn có kích thước cố định ~169 – 171 bytes với nội dung `Output: (empty)`.
- State file của watchdog (như `feed_session_reported.json`, `follow_session_reported.json`) vẫn đánh dấu session đã hoàn tất (`reported_sessions`), gây ra hiện tượng **Phantom Confirmation** (xác nhận ảo) khiến các ca nuôi bị bỏ qua vĩnh viễn dù chưa từng được gửi đi.

---

## 2. Căn Nguyên Kỹ Thuật (Win32 Detached Standard Handles)

Trong các Forwarding Shim được tạo ra để đồng bộ mã nguồn giữa `%LOCALAPPDATA%\hermes\scripts\` và git repo, thường có đoạn monkey-patch chống hiện cửa sổ console trên Windows:
```python
if sys.platform == "win32":
    _orig_subp_run = subprocess.run
    def _silent_subp_run(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        return _orig_subp_run(*args, **kwargs)
    subprocess.run = _silent_subp_run
```
Sau đó shim thực thi script đích bằng:
```python
proc = subprocess.run(cmd, cwd=WORKDIR)
sys.exit(proc.returncode)
```

### Điểm Nghẽn Cốt Lõi:
1. Khi Windows tạo tiến trình con với cờ `CREATE_NO_WINDOW (0x08000000)` mà không truyền chuyển hướng luồng (`stdout=subprocess.PIPE` hoặc `capture_output=True`), hệ điều hành sẽ gắn standard handle của tiến trình con vào `INVALID_HANDLE_VALUE` hoặc ngắt kết nối với handle của tiến trình cha.
2. Toàn bộ lệnh `print(target_msg)` trong script đích bị xả vào hư không (discarded silently).
3. Tiến trình shim kết thúc với exit code `0` nhưng `stdout` trả về cho Hermes Cron là **0 byte**.
4. Hermes Cron tuân theo quy tắc: `EMPTY stdout = SILENT` $\to$ không gửi tin Telegram và ghi nhận `last_delivery_error: null`.
5. Ở nhịp kế tiếp, watchdog kiểm tra `delivery_err is None` và lầm tưởng tin nhắn đã được giao $\to$ commit session key vào state.

---

## 3. Giải Pháp Kỹ Thuật Chuẩn Hóa (Capture & Passthrough)

BẮT BUỘC trong mọi Forwarding Shim trên Windows, nếu sử dụng `CREATE_NO_WINDOW` hoặc spawn tiến trình con qua subprocess, phải kích hoạt luồng thu nhận và ghi trực tiếp ngược lại `sys.stdout`:

```python
def main(*args, **kwargs):
    if not os.path.isfile(SCRIPT):
        sys.stderr.write(f"[SHIM ERROR] Canonical script not found: {SCRIPT}\n")
        sys.exit(1)
    cmd = [PY, "-B", SCRIPT]
    if kwargs.get("mode"):
        cmd.append(f"--mode={kwargs['mode']}")
    cmd.extend(sys.argv[1:])

    # BẮT BUỘC: capture_output=True và text=True để chống nuốt stdout khi có CREATE_NO_WINDOW
    proc = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        sys.stdout.flush()
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()

    if __name__ == "__main__":
        sys.exit(proc.returncode)
    return proc.returncode
```

### Quy Trình Cứu Hộ Khi Bị Nuốt Báo Cáo (Recovery Protocol):
1. Cập nhật mã nguồn Forwarding Shim với cơ chế Passthrough chuẩn hóa (`capture_output=True, text=True` và xả lại ra `sys.stdout`/`sys.stderr`). Đồng bộ cả 3 vị trí mirror (`deploy/hermes-home/scripts`, `%LOCALAPPDATA%\hermes\scripts`, và `OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts`).
2. Mở file state (ví dụ `feed_session_reported.json`, `follow_session_reported.json`), xóa các `session_key` bị commit ảo trong ngày khỏi mảng `reported_sessions`, và BẮT BUỘC đặt `pending_delivery: null`.
3. Kích hoạt phát bù tuần tự theo cơ chế Two-Phase Commit:
   - **Tick 1 (Phiên 1):** Chạy `cronjob action='run'` -> Watchdog phát hiện Phiên 1 chưa báo cáo, in ra stdout và ghi `pending_delivery = Phiên 1`. Hermes cron giao tin lên Telegram (log cron > 1KB).
   - **Tick 2 (Chốt Phiên 1 & Phát Phiên 2):** Chạy `cronjob action='run'` lần 2 -> Watchdog thấy Hermes không báo lỗi delivery, commit Phiên 1 vào `reported_sessions`, sau đó quét tiếp Phiên 2, in ra stdout và ghi `pending_delivery = Phiên 2`. Hermes giao Phiên 2 lên Telegram.
   - **Tick 3 (Chốt Phiên 2):** Chạy nhịp cron tiếp theo để commit Phiên 2 vào `reported_sessions` và đưa `pending_delivery` về null.
