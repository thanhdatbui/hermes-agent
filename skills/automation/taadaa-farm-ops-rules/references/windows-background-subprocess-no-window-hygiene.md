# Tiêu chuẩn dập tắt cửa sổ Console/CMD nháy & nhảy Taskbar trên Windows (Background Subprocess Hygiene)

## Hiện tượng & Triệu chứng
- Khi hệ thống chạy các pipeline nền (render video, download media, sync cron, probe ffmpeg/ffprobe, tool CLI ngoài):
- Trên màn hình desktop xuất hiện các bảng đen cmd / console window nhấp nháy liên tục (vài giây đến vài chục giây một lần).
- Cửa sổ cmd nhảy ra taskbar rồi biến mất, gây mất focus, phân tâm hoặc gián đoạn thao tác của user.

## Nguyên nhân gốc rễ (Root Cause)
- Trên Windows, khi script Python (kể cả chạy dưới `pythonw.exe` hoặc service nền) gọi lệnh console subsystem qua `subprocess.run(...)` hoặc `subprocess.Popen(...)` mà **không gán cờ ẩn cửa sổ**, OS sẽ spawn tiến trình con kèm cửa sổ console mới (`conhost.exe`).

## Chuẩn giải pháp (Canonical Fix)
BẮT BUỘC chèn `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)` (giá trị Windows `0x08000000`) cho mọi lời gọi tiến trình ngoài CLI (ffmpeg, ffprobe, git, yt-dlp, curl, PowerShell, ...):

```python
import subprocess
import sys

# Khởi tạo kwargs an toàn đa nền tảng
kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}

# Truyền vào subprocess.run
result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)

# Hoặc truyền vào subprocess.Popen
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
```

## Pitfalls khi Dispatch Worker
1. **Quá tải scope (Over-scoping) trên Worker**:
   - Nếu gom cả 4 file lớn/monolith vào 1 worker duy nhất với budget 15 tool calls, worker sẽ mất 10-12 turn chỉ để inspect file và đọc AST/imports, dẫn tới cạn budget khi chưa kịp ghi đĩa (0 files modified).
   - **Kỷ luật**: Phải phân rã (Gate 1 & Gate 5) thành các batch nhỏ (tối đa 2 file/worker), cấp sẵn anchor và exact contract, cấm worker lặp lại inspect.
2. **Quên import `sys`**:
   - Một số script tiện ích chỉ `import subprocess` mà không có `import sys`. Nếu viết `if sys.platform == "win32"` mà quên chèn `import sys` sẽ gây `NameError: name 'sys' is not defined`.
   - Bắt buộc kiểm tra header import hoặc dùng `getattr(subprocess, "CREATE_NO_WINDOW", 0)` trực tiếp nếu không muốn phụ thuộc `sys`.
