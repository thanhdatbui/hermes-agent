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

---

## Dual-Cluster / Multi-Host Parity & Gaming Protection Invariant

### 1. Invariant Chống Phá Game (Gaming Focus Protection)
- Người dùng thường xuyên chơi game toàn màn hình (TFT / League of Legends / game đồ họa) trên các máy farm (Kibe hoặc Admin-PC).
- Bất kỳ cửa sổ CMD/conhost nào bật lên dù chỉ 50ms cũng khiến Windows giật focus, khựng hình hoặc văng alt-tab ra ngoài màn hình nền, gây ức chế tột độ.
- **Kỷ luật thiết kế cron/watchdog:** TUYỆT ĐỐI CẤM thiết kế hoặc triển khai bất kỳ cronjob/watchdog nào chạy chu kỳ ngắn (1m, 2m, 5m, 15m) mà gọi trực tiếp `powershell.exe`, `cmd.exe`, `.bat` hay `python.exe` trong phiên tương tác mà không qua wrapper `wscript.exe` (`SW_HIDE / 0`) hoặc `pythonw.exe`.

### 2. Dual-Cluster Parity (Kibe ↔ Admin-PC `admin-farm`)
- Khi một máy (ví dụ Kibe) đã được vá triệt để với `sitecustomize.py` và Task Scheduler VBS wrapper, **BẮT BUỘC phải đồng bộ và kiểm tra sang máy còn lại (Admin-PC `admin-farm`)**.
- Các vị trí bắt buộc đồng bộ trên Admin-PC:
  * Python global: `C:\Users\Admin\AppData\Local\Programs\Python\Python311\Lib\site-packages\sitecustomize.py`
  * Farm automation venv: `D:\Taadaa\python-envs\automation\Lib\site-packages\sitecustomize.py`
  * Task Scheduler trên Admin: Mọi task định kỳ gọi watchdog phải trỏ sang `wscript.exe run_hidden.vbs`, cấm gọi trực tiếp `powershell.exe -WindowStyle Hidden` hay `.bat`.
  * Remote SSH commands từ Kibe sang Admin: Đảm bảo không kích hoạt tiến trình tạo GUI/console conhost trên desktop tương tác của Admin.

### 3. Triage Sai Host & Giao Thức Cấp Cứu Khi User Đang Chơi Game
- **Bẫy chẩn đoán sai host (Misattributing Host-Local Cron to Remote Controller):**
  * Trong mô hình Dual-Master (cả Kibe và Admin đều chạy bot Hermes và `jobs.json` riêng), khi User báo "máy Admin nhảy bảng cmd rồi tắt liền", **thủ phạm thường là chính Hermes nội bộ trên Admin** (chạy `taikhoan_sync_cron_launcher.py`, `hermes_stale_watchdog.py`, `feed_session_watchdog.py` mỗi 2–5 phút), CHỨ KHÔNG PHẢI lệnh SSH từ Kibe.
  * Tự ý pause cron trên Kibe rồi tuyên bố "đã xong" sẽ khiến User ức chế tột độ khi 2 phút sau cmd tiếp tục nhảy trên Admin.
- **Quy trình xử lý khẩn cấp 2 bước (Action-First Gaming Incident):**
  1. **Bước 1 (Cứu nguy tức thời 3s):** Đưa ngay lệnh 1 dòng PowerShell dập tắt nóng Hermes/Python trên đúng máy User đang chơi:
     `Stop-Process -Name hermes -Force -ErrorAction SilentlyContinue`
     hoặc chạy script kill nhanh (`stop_admin_cron_game.bat`). KHÔNG đoán mò, KHÔNG giải thích dông dài khi User đang trong trận game.
  2. **Bước 2 (Vá triệt để vĩnh viễn sau trận):** Hướng dẫn chạy `python D:/Taadaa/tools/install_silent_sitecustomize.py` trên máy đó để nạp cờ `CREATE_NO_WINDOW` vào toàn bộ Python environments (`Python311`, `Python312`, `automation`, `hermes-agent\venv`).

### 4. Bẫy Task Scheduler Hardware Guard (`Taadaa_Safe_USB_Guard_15m` / `safe_usb_guard.py`)
- **Dấu hiệu nhận biết ("cron check usb ấy"):**
  * Cửa sổ CMD bung lên đều đặn mỗi 15 phút trên máy Admin, in nhanh các dòng:
    `[GUARD PASS] Khong co may nao dang ban giu lock (Fleet ranh).`
    `[SKIP] ADB va bus USB van dang khoe manh, khong can reset.`
    rồi tắt ngay sau 1–2 giây, làm văng hoặc mất focus game toàn màn hình.
- **Nguyên nhân:**
  * Tác vụ Windows Task Scheduler được đăng ký gọi trực tiếp `python.exe C:\Taadaa_Service\safe_usb_guard.py` dưới phiên đăng nhập tương tác (`Session 1`) thay vì `pythonw.exe`.
- **Cứu nguy tức thời trong 1 giây:**
  ```cmd
  schtasks /change /tn "Taadaa_Safe_USB_Guard_15m" /disable
  ```
- **Khắc phục vĩnh viễn:**
  Đổi action sang `pythonw.exe` để chạy câm lặng 100% trong background:
  ```cmd
  schtasks /change /tn "Taadaa_Safe_USB_Guard_15m" /tr "pythonw.exe C:\Taadaa_Service\safe_usb_guard.py"
  schtasks /change /tn "Taadaa_Safe_USB_Guard_15m" /enable
  ```

---

### 5. Bẫy Tác Vụ Dọn Đĩa & Đồng Bộ Cloud (Disk Janitor / GDrive Sync / f_src Cleanup)
- **Dấu hiệu nhận biết:**
  * Bảng `cmd.exe` chớp lên giữa màn hình in dòng thu hồi bộ nhớ / đồng bộ:
    `f_src-151 -> GDrive & Freed 45 files (190.27 MB)`
    hoặc các thông điệp `Freed X files`, `Dọn dẹp ổ D`, `Sync cloud hoàn tất` rồi tự tắt sau vài giây.
- **Tác động:**
  * Windows cấp phát console window mới ngay trong phiên tương tác (Session 1), kích hoạt `SetForegroundWindow`, giật focus chuột/phím và văng các game toàn màn hình (TFT, LMHT, War3).
- **Nguyên tắc xử lý:**
  1. **Triage Action-First:** Ngay lập tức giải thích đúng bản chất kỹ thuật (tác vụ dọn đĩa / đồng bộ cloud vừa chạy xong), xác nhận cửa sổ đã tắt, không tranh cãi hay ngụy biện.
  2. **Zero-Window Invariant cho Disk Cleanup:** Mọi script dọn dẹp (xóa raw clip, dọn Downloads, đồng bộ Google Drive/OneDrive) khi được gọi tự động (sau render, sau ca nuôi, hoặc qua cron) bắt buộc phải:
     - Dùng `pythonw.exe` thay vì `python.exe` hoặc `.bat`.
     - Nếu gọi subprocess (rclone, ffmpeg, powershell), bắt buộc truyền `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`).
     - Định tuyến stdout/stderr vào file log hoặc `DEVNULL`, cấm in ra console.
  3. **Cơ chế ngắt khẩn cấp khi người dùng chơi game:** Nếu người dùng đang trong trận căng thẳng, luôn cung cấp phương án dập tắt tạm thời toàn bộ cron/watchdog nền (`tắt cron` / `Stop-Process`) để bảo vệ 100% không gian chơi game.

---

### 6. Kỷ Luật Pre-Deployment "Zero-Console" Cho Code Mới (Anti-Regression Invariant)
- **Vấn đề cốt lõi:** User nhiều lần phàn nàn: *"sao mỗi lần mày code cái mới mày lại vi phạm v"*. Nguyên nhân do Agent/Worker khi tạo script mới (watchdog, sync, cleanup, runner) chỉ tập trung vào việc code chạy được logic mà bỏ qua kiểm tra phương thức kích hoạt tiến trình trên môi trường Windows.
- **Quy tắc bắt buộc khi code mới trên Windows:**
  1. **CẤM `.bat` / `.cmd` gọi ngầm:** Tuyệt đối không tạo file `.bat` để cho cronjob hoặc background task gọi trực tiếp. Luôn bọc qua VBScript `WScript.Shell.Run(..., 0, False)` hoặc gọi trực tiếp binary với cờ ẩn.
  2. **CẤM `subprocess` trần không cờ:** Mọi lệnh `subprocess.run`, `subprocess.Popen`, `subprocess.check_call` gọi binary console (`adb.exe`, `git.exe`, `python.exe`, `curl.exe`) BẮT BUỘC phải có `creationflags=subprocess.CREATE_NO_WINDOW` (hoặc `0x08000000`).
  3. **CẤM `os.system()`:** `os.system()` luôn bật `cmd.exe` với console hiển thị trên Windows; thay thế 100% bằng `subprocess.run(..., creationflags=0x08000000)`.
  4. **Kỷ luật khi User yêu cầu tắt cron:** Lập tức gọi `cronjob(action='pause')` cho tất cả cronjob đang active song song, kiểm tra sạch cửa sổ bằng `computer_use(action='list_windows')`, sau đó mới trả lời ngắn gọn. Tuyệt đối không đôi co, tranh luận hay giải thích dông dài trước khi hành động dập tắt hoàn tất.
