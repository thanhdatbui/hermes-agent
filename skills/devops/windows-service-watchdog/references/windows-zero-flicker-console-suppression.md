# Triệt Tiêu Nháy Cửa Sổ Console / Conhost Trên Windows (Cron, Watchdog, Background Automation)

## Hiện tượng và Nguyên nhân gốc rễ (Root Cause)

Trên Windows, khi chạy các tác vụ nền lặp chu kỳ ngắn (Task Scheduler 2-5 phút, Hermes Cron, Watchdogs), người dùng thường xuyên bị "nháy cửa sổ đen cmd/conhost" làm giật focus hoặc giật màn hình khi đang chơi game / làm việc.

Có 2 nguyên nhân cốt lõi ở cấp độ Windows Subsystem:
1. **Console Subsystem (CUI) Binary Launch:**
   - `powershell.exe`, `cmd.exe`, `python.exe`, `adb.exe`, `git.exe` đều có `Subsystem: IMAGE_SUBSYSTEM_WINDOWS_CUI`.
   - Khi được gọi từ Task Scheduler hoặc tiến trình không có console, Windows CSRSS/conhost **bắt buộc phải cấp phát một console window mới** trước khi đọc tham số dòng lệnh.
   - Thêm cờ `-WindowStyle Hidden` vào PowerShell **không ngăn được conhost bung cửa sổ**: cửa sổ vẫn hiện lên 50-200ms trước khi PowerShell xử lý tham số và gọi `ShowWindow(hWnd, SW_HIDE)`.
2. **Subprocess Chaining trong Python/PowerShell:**
   - Khi một script Python chạy ngầm (ví dụ qua `pythonw.exe` hoặc Task Scheduler ẩn) nhưng bên trong gọi `subprocess.run(["adb", ...])`, `subprocess.Popen(["git", ...])` hoặc PowerShell script gọi `Start-Process powershell.exe ... -WindowStyle Hidden`, nếu không truyền cờ `CREATE_NO_WINDOW (0x08000000)`, Windows tiếp tục bật conhost mới cho process con.

---

## Giải pháp 3 Tầng Triệt Để (Zero-Flicker Architecture)

### Tầng 1: VBScript GUI Wrapper cho Task Scheduler (Triệt tiêu cấp Launcher)
`wscript.exe` là Win32 GUI Subsystem (`IMAGE_SUBSYSTEM_WINDOWS_GUI`), do đó không sở hữu console và không bao giờ bật conhost. Khi dùng `WScript.Shell.Run` với cờ `intWindowStyle = 0` (`SW_HIDE`), tiến trình con được tạo với `STARTUPINFO.wShowWindow = SW_HIDE` từ Frame 0.

**Template `run-hidden.vbs`:**
```vbscript
Option Explicit
Dim objShell
Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""D:\Path\To\your-watchdog.ps1""", 0, False
Set objShell = Nothing
```

**Cập nhật Task Scheduler:**
```cmd
schtasks /change /tn "Your_Task_Name" /tr "wscript.exe \"D:\Path\To\run-hidden.vbs\""
```

---

### Tầng 2: Loại bỏ Sub-process Spawning bên trong Script (In-process Execution)
Tránh dùng script con để query thông tin nếu có thể thực hiện in-process.

**Ví dụ trong PowerShell Watchdog:**
Thay vì spawn process con:
```powershell
# BAD: Bật powershell.exe mới gây flash conhost
$p = Start-Process powershell.exe -ArgumentList @('-EncodedCommand', $encoded) -WindowStyle Hidden -PassThru
```
Thực hiện truy vấn trực tiếp bằng in-process CIM / WMI:
```powershell
# GOOD: Hoàn toàn in-process, không sinh thêm conhost
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$processes = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' or Name = 'pythonw.exe'" -ErrorAction Stop)
foreach ($proc in $processes) {
    if ($proc.CommandLine -match 'target_signature') {
        $owner = Invoke-CimMethod -InputObject $proc -MethodName GetOwner -ErrorAction SilentlyContinue
        if ($owner.ReturnValue -eq 0 -and ("{0}\{1}" -f $owner.Domain, $owner.User) -eq $currentIdentity) {
            # Xử lý matching...
        }
    }
}
```

---

### Tầng 3: Triệt tiêu Subprocess trong Python (`sitecustomize.py` + explicit flags)

#### Cách 3A: Cài đặt Hook Tự Động Global (`sitecustomize.py`)
Đặt file `sitecustomize.py` vào thư mục `site-packages` của các môi trường Python (Python global, virtual environments). Sử dụng cờ guard `_hermes_no_window_patched` và bọc `try...except` để đảm bảo tính idempotent và không làm vỡ quá trình khởi động Python.

**LƯU Ý CỐT LÕI (Bẫy DETACHED_PROCESS 0x08):**
Trên Windows, khi `DETACHED_PROCESS` (`0x00000008`) được truyền kèm với binary console (`python.exe`), Windows sẽ cấp phát một console mới (`conhost.exe`) tách biệt với tiến trình cha, dẫn đến việc xuất hiện cửa sổ CMD đen trên desktop. Do đó, hook `sitecustomize.py` bắt buộc phải **strip cờ `0x08`** đồng thời ép cứng `CREATE_NO_WINDOW` (`0x08000000`):

```python
import sys
if sys.platform == "win32":
    try:
        import subprocess
        if not getattr(subprocess, "_hermes_no_window_patched", False):
            subprocess._hermes_no_window_patched = True
            _orig_popen_init = subprocess.Popen.__init__
            def _silent_popen_init(self, *args, **kwargs):
                flags = kwargs.get("creationflags", 0)
                # Strip DETACHED_PROCESS (0x08) and enforce CREATE_NO_WINDOW (0x08000000)
                kwargs["creationflags"] = (flags & ~0x00000008) | 0x08000000
                _orig_popen_init(self, *args, **kwargs)
            subprocess.Popen.__init__ = _silent_popen_init
    except Exception:
        pass
```

**Các môi trường Python trọng yếu cần rà soát trên máy Windows host:**
- Hermes runtime venv: `%LOCALAPPDATA%\hermes\hermes-agent\venv\Lib\site-packages\sitecustomize.py`
- Farm automation env: `D:\Taadaa\python-envs\automation\Lib\site-packages\sitecustomize.py`
- Video/Codex runtime env: `D:\CodexRuntime\tiktok-video\venv-core024\Lib\site-packages\sitecustomize.py`
- Global Python: `%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\sitecustomize.py` (hoặc Python tương ứng trong PATH)

#### Cách 3B: Hardcode trong code Python gọi Subprocess
Luôn truyền `creationflags=0x08000000` (hoặc `subprocess.CREATE_NO_WINDOW`):
```python
import subprocess
import sys

creation_flags = 0x08000000 if sys.platform == "win32" else 0

result = subprocess.run(
    ["adb", "devices"],
    capture_output=True,
    text=True,
    creationflags=creation_flags
)
```

Hoặc pattern helper gọn nhẹ cho các standalone scripts:
```python
import os
import subprocess

WIN_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

# Sử dụng:
res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **WIN_KWARGS)
```

---

## Case Study Thực Tế: Console Window Storm do Batch Cronjob đa luồng

### Triệu chứng (User Alert)
- Màn hình desktop liên tục nháy/chớp các cửa sổ cmd màu đen xếp chồng lên nhau (`C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc `python.exe`), gây giật lag và ức chế ("Clgt nó đang nháy nháy liên tục").

### Nguyên nhân
- Cronjob chạy nền (`pythonw.exe`) kích hoạt tác vụ dọn dẹp hoặc watchdog hàng loạt qua ThreadPoolExecutor (`MAX_WORKERS = 20..30`) trên 70-140 thiết bị (ví dụ `cron_clear_tiktok_cache.py` gọi `clear-tiktok-cache.py`, `farm_idle_screen_and_app_healer.py`).
- Các script con tự viết raw `subprocess.run([ADB, "-s", serial, ...])` mà bỏ quên cờ `creationflags=subprocess.CREATE_NO_WINDOW`.
- Hàng chục lệnh ADB (`input keyevent`, `am force-stop`, `dumpsys`) được bắn ra mỗi giây, khiến Windows liên tục bung và tắt cửa sổ conhost trong 50-200ms, tạo thành "cơn bão nháy cửa sổ".

### Chẩn đoán O(1) & Khắc phục
1. **Truy tìm nguồn gọi**:
   ```powershell
   Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'adb' } | Select-Object ProcessId, ParentProcessId, Name, CommandLine
   ```
   Lần theo `ParentProcessId` để xác định chính xác script Python đang spawn `adb.exe`.
2. **Khắc phục**:
   Bổ sung `{"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}` vào mọi lời gọi `subprocess.run` / `Popen` trong các script liên quan.
