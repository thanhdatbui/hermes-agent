# Safe Idle Gateway Restart & Telegram Proxy Tunneling

## 1. Cơ chế chặn Self-Restart từ bên trong Session

Hermes Gateway áp dụng cơ chế 3 lớp phòng vệ chống tự restart từ session con:
- `tools/terminal_tool.py`: Chặn các lệnh chứa `gateway restart|stop` khi có `_HERMES_GATEWAY=1`.
- `hermes_cli/gateway.py`: Kiểm tra `_HERMES_GATEWAY == "1"` và thoát ngay nếu gọi CLI trực tiếp.
- `cron/lifecycle_guard.py`: Chặn cron job chứa lệnh restart gateway.

**Lý do:** Tiến trình Gateway (`pythonw.exe`) là cha của toàn bộ session và terminal subprocess. Tự kill cha sẽ làm đứt ngang subprocess trước khi lệnh kế tiếp kịp chạy, và có thể kích hoạt crash loop nếu có task watchdog bên ngoài.

---

## 2. One-Shot Idle Watcher Pattern (Tự động Restart khi Bot Rảnh)

Khi người dùng yêu cầu restart Gateway sau khi sửa cấu hình (`.env`, proxy, port...) mà không muốn làm đứt các session AI đang suy nghĩ dở ở các group khác:

### A. Cơ chế đọc trạng thái Runtime
Hermes Gateway ghi liên tục trạng thái thời gian thực ra:
- Đường dẫn: `%LOCALAPPDATA%\hermes\gateway_state.json`
- Cấu trúc:
  ```json
  {
    "updated_at": "2026-09-05T03:22:50.178877+00:00",
    "gateway_state": "running",
    "active_agents": 0,
    "pid": 234872
  }
  ```
- `active_agents`: Số lượng agent turn đang chạy đồng thời trên toàn bộ các kênh (DM, Group, Topic). Khi `active_agents == 0`, toàn bộ bot rảnh.

### B. Mẫu script One-Shot Watcher (`restart-when-idle.ps1`)
Lưu tại `%LOCALAPPDATA%\hermes\scripts\restart-when-idle.ps1`:
```powershell
Remove-Item Env:\_HERMES_GATEWAY -ErrorAction SilentlyContinue
$env:_HERMES_GATEWAY = $null

$stateFile = "$env:LOCALAPPDATA\hermes\gateway_state.json"
$logFile   = "$env:LOCALAPPDATA\hermes\logs\idle_restart.log"

function Log-Msg($msg) {
    "[$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

$requiredIdleChecks = 8  # 8 lần x 2s = 16s debounce liên tục
$idleCount = 0

while ($true) {
    Start-Sleep -Seconds 2
    if (!(Test-Path $stateFile)) { continue }
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        $targetPid = $state.pid
        $activeWork = [int]$state.active_agents
        $gwState = $state.gateway_state
    } catch { continue }

    $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if (!$proc) { break }

    if ($gwState -eq "running" -and $activeWork -eq 0) {
        $idleCount++
        if ($idleCount -ge $requiredIdleChecks) {
            Log-Msg "Gateway idle liên tục 16s. Tiến hành restart PID $targetPid..."
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            
            # Khởi động lại qua pythonw chính xác từ uv
            $pythonwExe = "$env:APPDATA\uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe"
            Start-Process $pythonwExe -ArgumentList "-m hermes_cli.main gateway run" -WindowStyle Hidden
            Log-Msg "Gateway đã khởi động lại. Watcher kết thúc."
            exit 0  # One-shot: tự thoát hoàn toàn
        }
    } else {
        $idleCount = 0
    }
}
```

### C. Cách kích hoạt ngầm độc lập
Gọi từ PowerShell ngoài hoặc qua subagent:
```powershell
Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File $env:LOCALAPPDATA\hermes\scripts\restart-when-idle.ps1" -WindowStyle Hidden
```

### D. Bất biến an toàn (Zero-Impact Invariants)
- **Phone Farm:** Script farm chạy bằng `python.exe`. Gateway chạy bằng `pythonw.exe`. Dừng `pythonw.exe` hoàn toàn không ảnh hưởng tới các batch feed, upload, follow đang chạy trên máy.
- **Session AI:** Chỉ restart khi `active_agents == 0` liên tục 16s, đảm bảo không có turn nào bị ngắt ngang.
- **Dữ liệu:** SQLite `state.db` lưu trữ tin nhắn bền vững, không mất mát context.

### E. Kiểm tra & Giám sát sau Restart (Post-Restart Verification)
Sau khi kích hoạt watcher để restart Gateway khi idle, tiến hành nghiệm thu theo 4 nguồn log/state:
1. **Kiểm tra tiến trình Watcher:** `Get-Process -Id <pid_watcher>` trả về NotFound/HasExited chứng minh watcher đã hoàn thành nhiệm vụ và tự thoát sạch (`exit 0`).
2. **Log Watcher (`%LOCALAPPDATA%\hermes\logs\idle_restart.log`):**
   - Xác nhận chuỗi debounce idle đủ 8/8 lần (16s): `Phát hiện idle (8/8)... Gateway idle liên tục 16s. Thực hiện restart...`
   - Xác nhận mốc hoàn tất: `Gateway đã được khởi động lại thành công. Watcher kết thúc.`
3. **Log Khởi động (`%LOCALAPPDATA%\hermes\logs\gateway-exit-diag.log`):**
   - Chứa dòng JSON `{"tag": "gateway.start", "pid": <PID_mới>, ...}` với timestamp UTC chính xác khi `pythonw.exe` khởi chạy.
4. **State thời gian thực (`%LOCALAPPDATA%\hermes\gateway_state.json`):**
   - `pid`: Khớp PID mới của Gateway.
   - `gateway_state`: `"running"`.
   - `platforms.telegram.state`: `"connected"` (kèm `updated_at` mới).
   - `active_agents`: Số lượng turn đang xử lý hiện tại.
5. *Lưu ý về `gateway.log`:* Ngay sau restart, `gateway.log` có thể chưa flush dòng mới nếu chưa có tin nhắn inbound hoặc event định kỳ. Không dùng timestamp của `gateway.log` để kết luận gateway chưa chạy mà đối chiếu trực tiếp qua `gateway_state.json` và `gateway-exit-diag.log`.

---

## 3. Cấu hình Telegram Proxy với ký tự đặc biệt (`TELEGRAM_PROXY`)

Khi tuyến cáp ISP FPT bị bóp hoặc drop gói ngầm tới Telegram (silent TCP CLOSE-WAIT stall), chuyển riêng kết nối Telegram Bot sang proxy WAN Viettel qua biến môi trường:
- File cấu hình: `%LOCALAPPDATA%\hermes\.env`
- Biến: `TELEGRAM_PROXY=http://admin%401:admin%401@192.168.110.2:10001`
- **Quy tắc URL Encode Credential:** Nếu username hoặc password có chứa ký tự `@`, bắt buộc phải encode thành `%40` (ví dụ `admin@1` $\rightarrow$ `admin%401`). Thư viện `httpx` của Python tuân thủ RFC 3986 sẽ tự decode thành header `Proxy-Authorization: Basic ***` hợp lệ, tránh lỗi `407 Proxy Authentication Required`.

### Pre-flight Verification Probe
Trước khi đưa proxy vào sử dụng, kiểm tra qua 2 bước:
1. **Kiểm tra HTTP CONNECT tunnel tới Telegram:**
   ```bash
   curl -s -I -x "http://admin%401:admin%401@192.168.110.2:10001" https://api.telegram.org/
   ```
   Tiêu chí: Trả về `HTTP/1.0 200 Connection established` (hoặc redirect 302 từ Telegram root).
2. **Kiểm tra Python httpx:**
   ```bash
   python -c "import httpx; r = httpx.get('https://api.telegram.org/', proxy='http://admin%401:admin%401@192.168.110.2:10001', timeout=15); print(r.status_code)"
   ```
   Tiêu chí: Status code 302/404, không timeout hoặc 407.
