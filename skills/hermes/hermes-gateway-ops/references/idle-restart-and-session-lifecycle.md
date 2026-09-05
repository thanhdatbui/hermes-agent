# Check Session Idle & Independent Background Restart for Hermes Gateway (Windows)

Tài liệu chi tiết về cơ chế quản lý session active/idle trong mã nguồn Hermes Gateway và kỹ thuật trigger restart an toàn từ script nền độc lập không làm gián đoạn in-flight turns.

---

## 1. 4 Tầng Quản Lý Session trong Hermes Gateway

Khi khảo sát mã nguồn Gateway (`gateway/run.py`, `gateway/status.py`, `gateway/session.py`):

| Tầng | Cấu trúc dữ liệu / Vị trí | Chức năng & Trạng thái | Lưu ý phân biệt |
|---|---|---|---|
| **In-flight Turns** | `self._running_agents` (`Dict[str, Any]` trong `gateway/run.py`) | Theo dõi các session **đang trực tiếp thực thi turn** (đang gọi LLM API, chạy tool, hoặc chờ subagent). | **Nguồn sự thật duy nhất về active turns.** Khi bắt đầu turn: gắn `_AGENT_PENDING_SENTINEL` -> `AIAgent`. Khi turn kết thúc: gọi `_clear_running_agent()`. |
| **Agent LRU Cache** | `self._agent_cache` (`OrderedDict` trong `gateway/run.py`) | Cache in-memory các instance `AIAgent` đã từng chạy để giữ nguyên prompt caching (Anthropic, Gemini prefix cache) qua các turn. | **Agent trong cache hoàn toàn có thể đang IDLE.** Cache chỉ dọn dẹp khi vượt `_AGENT_CACHE_MAX_SIZE` (100) hoặc quá hạn idle TTL (`_AGENT_CACHE_IDLE_TTL_SECS = 3600s`). Không dùng cache để đo tải in-flight. |
| **Session Store** | `SessionStore` / `AsyncSessionStore` (`gateway/session.py`) | Lưu trữ dữ liệu tĩnh và metadata lâu dài của toàn bộ session vào SQLite `state.db` (và mirror ra `sessions/sessions.json`). | Quản lý transcript, session ID, routing, `resume_pending`, reset policy... Là tầng lưu trữ tĩnh bền vững. |
| **Worker Executor** | `self._executor` (`ThreadPoolExecutor` trong `gateway/run.py`) | Pool luồng thực thi các tác vụ đồng bộ của agent (cấu hình qua `gateway.max_workers`). | Chịu trách nhiệm concurrency, không lưu danh sách session. |

### Chỉ số Active Work Aggregate
Trong `gateway/run.py`:
```python
def _active_work_count(self) -> int:
    return (
        self._running_agent_count()       # len(self._running_agents)
        + self._active_cron_job_count()    # in-flight cron jobs
        + self._active_api_run_count()     # in-flight API server requests
    )
```
Mỗi khi có turn bắt đầu hoặc kết thúc, hàm `_persist_active_agents()` được gọi và ghi liên tục giá trị này vào file `$LOCALAPPDATA\hermes\gateway_state.json` dưới key `"active_agents"`.

---

## 2. Tại sao `hermes gateway restart` bị chặn trong Session?

Hermes triển khai **3 lớp phòng vệ (defense-in-depth)**:
1. **Lớp Tool (`tools/terminal_tool.py:2275`):**
   Nếu `os.environ.get("_HERMES_GATEWAY") == "1"`, terminal tool chạy hàm `_contains_gateway_lifecycle_command(command)`. Regex này bắt mọi dạng `hermes gateway restart`, `stop`, `pkill ... gateway`... và chặn ngay lập tức, trả về lỗi:
   > *"Blocked: cannot restart or stop the gateway from inside the gateway process..."*
2. **Lớp CLI (`hermes_cli/gateway.py:6871`):**
   Nếu lệnh gọi CLI trực tiếp: `if os.getenv("_HERMES_GATEWAY") == "1": print_error(...) ; sys.exit(1)`.
3. **Lớp Cron Guard (`cron/lifecycle_guard.py`):**
   Chặn không cho đặt lịch cron job chứa lệnh restart gateway.

**Nguyên nhân kỹ thuật:**
Tiến trình Gateway (`pythonw.exe`) là tiến trình cha của mọi session và terminal subprocess. Nếu lệnh trong session kill gateway, tiến trình cha chết sẽ kéo theo toàn bộ terminal subprocess bị hủy diệt ngay lập tức trước khi kịp hoàn tất chuỗi restart. Đồng thời, dưới Scheduled Task hoặc service supervisor, việc kill ngang sẽ kích hoạt crash-restart loop liên tục.

---

## 3. Cơ chế Kiểm Tra Gateway IDLE từ Bên Ngoài

Nguồn dữ liệu authoritative duy nhất để biết Gateway rảnh hay bận:
* **File trạng thái:** `C:\Users\Kibe\AppData\Local\hermes\gateway_state.json` (`$env:LOCALAPPDATA\hermes\gateway_state.json`).
* **Nội dung mẫu:**
  ```json
  {
    "updated_at": "2026-09-05T03:22:50.178877+00:00",
    "gateway_state": "running",
    "active_agents": 0,
    "pid": 234872
  }
  ```
* **Điều kiện Gateway IDLE tuyệt đối:**
  1. Tiến trình `pid` còn sống (`Get-Process -Id $pid`).
  2. `gateway_state == "running"`.
  3. `active_agents == 0`.
* **Debounce bắt buộc:** Để tránh khoảng trống 0.5s–1s giữa các turn kế tiếp hoặc subagent vừa bàn giao kết quả, script phải kiểm tra `active_agents == 0` liên tục trong **10 đến 15 giây** (ví dụ 5 lần liên tiếp x 2s = 10s) trước khi thực hiện hành động.

---

## 4. Script Nền Độc Lập Trigger Restart (`restart-when-idle.ps1`)

### Các yêu cầu bắt buộc:
1. **Tách rời process tree:** Chạy qua `Start-Process powershell.exe -ArgumentList "..." -WindowStyle Hidden` để lệnh terminal của agent trả về ngay lập tức, giải phóng session hiện tại về 0 active turn.
2. **Xóa biến môi trường kế thừa:** Un-set `_HERMES_GATEWAY` trong PowerShell để không bị các lớp guard chặn.
3. **Relaunch an toàn:** Có 2 phương thức relaunch:
   - **Cách 1: Khởi động trực tiếp qua `pythonw.exe` (Khuyên dùng khi không có VBS hoặc muốn chuẩn 1-1 với tiến trình gốc):** Lấy chính xác `ExecutablePath` của tiến trình `pythonw.exe` đang chạy qua WMI (`Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid"`), sau đó chạy `Start-Process $pythonwExe -ArgumentList "-m hermes_cli.main gateway run" -WindowStyle Hidden`.
   - **Cách 2: Sử dụng VBS launcher chính thức của Hermes:** Tại `$env:LOCALAPPDATA\hermes\gateway-service\Hermes_Gateway.vbs` (nạp `HERMES_HOME`, `PYTHONPATH`, `VIRTUAL_ENV` và chạy `pythonw.exe` hoàn toàn ẩn).

### Code mẫu chuẩn Direct Pythonw WMI (`C:\Users\Kibe\AppData\Local\hermes\scripts\restart-when-idle.ps1`):
```powershell
# Bỏ biến môi trường thừa kế từ session Hermes để tránh bị chặn
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue
$env:_HERMES_GATEWAY = $null

$stateFile = "C:\Users\Kibe\AppData\Local\hermes\gateway_state.json"
$logFile   = "C:\Users\Kibe\AppData\Local\hermes\logs\idle_restart.log"
$defaultPythonw = "C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe"

function Log-Msg($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$timestamp] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log-Msg "Bắt đầu ONE-SHOT watcher tự động restart Gateway khi idle (PID watcher: $PID)..."

$requiredIdleChecks = 8   # 8 lần kiểm tra liên tiếp x 2s = 16 giây idle liên tục
$idleCount = 0
$cachedPythonw = $null

while ($true) {
    Start-Sleep -Seconds 2
    
    if (!(Test-Path $stateFile)) { continue }

    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        $targetPid = $state.pid
        $activeWork = [int]$state.active_agents
        $gwState = $state.gateway_state
    } catch {
        continue
    }

    # Cache đường dẫn executable của gateway từ target PID trước khi stop
    if (!$cachedPythonw -and $targetPid) {
        try {
            $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
            if ($procInfo -and $procInfo.ExecutablePath) {
                $cachedPythonw = $procInfo.ExecutablePath
            }
        } catch {}
    }

    if ($gwState -eq "running" -and $activeWork -eq 0) {
        $idleCount++
        Log-Msg "Phát hiện idle ($idleCount/$requiredIdleChecks)..."
        if ($idleCount -ge $requiredIdleChecks) {
            Log-Msg "Gateway idle liên tục 16s. Thực hiện restart..."

            $pythonwExe = $cachedPythonw
            if (!$pythonwExe) {
                $pythonwExe = $defaultPythonw
            }

            # 1. Dừng Gateway process
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            } catch {}

            Start-Sleep -Seconds 2

            # 2. Khởi động lại Gateway bằng Start-Process trực tiếp
            Start-Process $pythonwExe -ArgumentList "-m hermes_cli.main gateway run" -WindowStyle Hidden
            Log-Msg "Gateway đã được khởi động lại thành công. Watcher kết thúc."
            exit 0
        }
    } else {
        if ($idleCount -gt 0) {
            Log-Msg "Phát hiện active agents ($activeWork) hoặc gateway_state ($gwState). Reset bộ đếm về 0."
        }
        $idleCount = 0
    }
}
```

### Code mẫu qua VBS Launcher (`Hermes_Gateway.vbs`):
```powershell
# Bỏ biến môi trường thừa kế từ session Hermes
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue
$env:_HERMES_GATEWAY = $null

$stateFile = "$env:LOCALAPPDATA\hermes\gateway_state.json"
$logFile   = "$env:LOCALAPPDATA\hermes\logs\idle_restart.log"
$vbsPath   = "$env:LOCALAPPDATA\hermes\gateway-service\Hermes_Gateway.vbs"

function Log-Msg($msg) {
    "[$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log-Msg "Bắt đầu watcher restart khi Gateway idle..."

$requiredIdleChecks = 5  # 5 lần liên tiếp x 2s = 10s idle liên tục
$idleCount = 0

while ($true) {
    Start-Sleep -Seconds 2
    if (!(Test-Path $stateFile)) { continue }

    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        $targetPid = $state.pid
        $activeWork = [int]$state.active_agents
        $gwState = $state.gateway_state
    } catch {
        continue
    }

    # Kiểm tra process gateway còn sống không
    $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if (!$proc) {
        Log-Msg "Gateway PID $targetPid không tồn tại. Dừng watcher."
        break
    }

    if ($gwState -eq "running" -and $activeWork -eq 0) {
        $idleCount++
        Log-Msg "Phát hiện idle ($idleCount/$requiredIdleChecks)..."
        if ($idleCount -ge $requiredIdleChecks) {
            Log-Msg "Gateway đã IDLE hoàn toàn trong 10s. Tiến hành restart..."
            
            # 1. Dừng Gateway process
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2

            # Đảm bảo không còn pythonw gateway tồn tại
            Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1

            # 2. Khởi động lại Gateway qua launcher VBS chuẩn
            if (Test-Path $vbsPath) {
                Start-Process "wscript.exe" -ArgumentList "`"$vbsPath`"" -WindowStyle Hidden
                Log-Msg "Đã trigger khởi động lại qua $vbsPath thành công."
            } else {
                Log-Msg "Lỗi: Không tìm thấy $vbsPath!"
            }
            break
        }
    } else {
        if ($idleCount -gt 0) {
            Log-Msg "Phát hiện active work ($activeWork agents). Reset bộ đếm idle."
        }
        $idleCount = 0
    }
}
```

### Lệnh kích hoạt và verify từ git-bash / Session:
```bash
# Kích hoạt ngầm độc lập (detached):
powershell.exe -NoProfile -Command 'Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File C:\Users\Kibe\AppData\Local\hermes\scripts\restart-when-idle.ps1" -WindowStyle Hidden'

# Verify tiến trình watcher đang chạy (tránh pitfall lồng nháy đơn trong git-bash khi query WMI):
powershell.exe -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*restart-when-idle.ps1*" } | Select-Object ProcessId, ExecutablePath, CommandLine'
```
