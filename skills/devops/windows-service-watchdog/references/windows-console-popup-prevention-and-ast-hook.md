# Windows Background Console Window Prevention & AST Pre-Tool Hook Pattern

## Incident Context
Khi chạy background tasks / cronjobs / subprocesses trên Windows, nếu gọi trực tiếp `cmd.exe`, file `.bat`, hoặc `python.exe` / `powershell.exe` mà thiếu cờ ẩn cửa sổ (`CREATE_NO_WINDOW` / `-WindowStyle Hidden`), Windows sẽ mặc định cấp console window tương tác. Cửa sổ console này nhảy lên desktop cướp active focus của người dùng (gây giật lag, alt-tab fullscreen games như TFT, LoL, War3).

## Core Invariants
1. **Never rely on prompt reminders alone:** Dặn dò trong prompt không ngăn được agent hoặc script con vô tình gọi subprocess mở console. Bắt buộc dùng mechanical pre-tool hook để chặn đứng ở runtime.
2. **Launchers allowed:** Chỉ cho phép `pythonw.exe` hoặc `powershell.exe -WindowStyle Hidden`. Cấm `cmd.exe`, file `.bat` trần, hoặc bare `python.exe` trong context background.
3. **AST Static Scan for Python Scripts:**
   - Khi tham số là file `.py`, pre-tool hook phải parse AST toàn bộ file script.
   - Bắt buộc mọi lệnh `subprocess.run`, `subprocess.Popen`, `subprocess.call`... phải có tham số `creationflags` chứa `CREATE_NO_WINDOW` (`0x08000000`).
   - Cấm `os.system()` và `os.popen()` vì hai hàm này trên Windows không có cơ chế truyền `creationflags`.
4. **Avoid Prompt Splitting False Positives:**
   - Đối với công cụ `cronjob`, chỉ scan tham số `script` (command string thực thi), tuyệt đối KHÔNG parse trường `prompt` bằng `shlex.split` vì các câu văn tự nhiên chứa dấu nháy đơn (`'`) hoặc từ như "Start..." sẽ gây `ValueError` hoặc chặn nhầm (false-positive).
5. **Auditing & Telemetry:** Mọi sự kiện block phải được ghi append-only vào log tập trung (ví dụ `runtime/audit_logs/console_block_audit.jsonl`) kèm timestamp UTC và nguyên nhân vi phạm rõ ràng.
