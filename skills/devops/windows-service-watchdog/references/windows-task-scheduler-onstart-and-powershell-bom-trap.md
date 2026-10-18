# Windows Task Scheduler On-Start Recovery & PowerShell UTF-8 BOM Trap

## Overview
This reference documents two critical Windows operational failure modes discovered during farm background service management:
1. **Unattended Reboot Recovery Breakdown**: How disabling a flickering watchdog severed post-reboot recovery, and the correct `/sc onstart` + 15m headless watchdog pattern.
2. **PowerShell 5.1 UTF-8 BOM Injection**: How PowerShell's default UTF-8 encoding corrupts proxy lists and config files, breaking `yt-dlp` and HTTP parsers with silent `Failed to parse` errors.

---

## 1. Unattended Reboot Recovery Breakdown

### The Failure Chain
1. A watchdog script ran every 2 minutes via PowerShell to ensure the background gateway service stayed alive.
2. Because PowerShell is a CUI binary, it briefly allocated a conhost console context every 2 minutes, causing slight screen flicker / focus micro-stutters during borderless full-screen gaming (Warcraft 3 / TFT).
3. To stop the flicker, a previous session executed:
   ```powershell
   Disable-ScheduledTask -TaskName 'Gateway_Watchdog'
   ```
4. On Windows, the main service had only a logon trigger (`MSFT_TaskLogonTrigger`).
5. Scheduled host reboots (05:20 / 17:20) left the machine at the Windows lock screen without interactive user logon.
6. Result:
   - Neither the Windows Startup folder (`AppData\Roaming\...\Startup`) nor Logon-triggered tasks ever executed.
   - The gateway service never woke up; all scheduled cron jobs remained stopped.
   - Long-running background workers (downloader, batch renderer) died during reboot and were never revived.

### The Correct Zero-Flicker Architecture
Never disable recovery watchdogs to solve screen flicker. Instead, deploy the Dual-Trigger Headless Pattern directly in Windows Task Scheduler:

1. **Trigger on Boot (`/sc onstart`)**: Ensures immediate execution as soon as the OS boots, regardless of user login.
2. **Periodic Health Check (`/sc minute /mo 15`)**: Ensures recovery if a process crashes mid-day from network/DB exceptions or OOM.
3. **Headless Execution (`wscript.exe //B //Nologo`)**: Uses Windows Script Host GUI subsystem with `SW_HIDE (0)` to prevent any console window allocation from frame 0.

#### Command Pattern (cmd / schtasks):
```cmd
:: Downloader: Boot survival + 15m periodic check
schtasks /create /tn "Taadaa_Admin_Downloader_Boot" /tr "wscript.exe //B //Nologo C:\Users\Admin\start_downloader_watchdog.vbs" /sc onstart /ru "Admin" /f
schtasks /create /tn "Taadaa_Admin_Downloader_15m" /tr "wscript.exe //B //Nologo C:\Users\Admin\start_downloader_watchdog.vbs" /sc minute /mo 15 /ru "Admin" /f

:: Renderer: Boot survival + 15m periodic check
schtasks /create /tn "Taadaa_Admin_Render_Boot" /tr "wscript.exe //B //Nologo C:\Users\Admin\start_render_watchdog.vbs" /sc onstart /ru "Admin" /f
schtasks /create /tn "Taadaa_Admin_Render_15m" /tr "wscript.exe //B //Nologo C:\Users\Admin\start_render_watchdog.vbs" /sc minute /mo 15 /ru "Admin" /f

:: Gateway / Scheduler: Boot survival
schtasks /create /tn "Taadaa_Admin_Gateway_Boot" /tr "wscript.exe //B //Nologo C:\Taadaa_Service\start_gateway.vbs" /sc onstart /ru "Admin" /f
```

#### Companion VBS Launcher (`C:\Users\Admin\start_downloader_watchdog.vbs`):
```vbscript
Option Explicit
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
' WindowStyle = 0 (Hidden), WaitOnReturn = False
WshShell.Run """C:\Python311\python.exe"" ""C:\Users\Admin\watchdog_admin_downloader.py""", 0, False
Set WshShell = Nothing
```

---

## 2. PowerShell 5.1 UTF-8 BOM Injection Trap

### The Problem
In Windows PowerShell 5.1 (the default built-in PowerShell on Windows 10/11 and Windows Server), running:
```powershell
Set-Content -Path "proxy_pool.txt" -Value $lines -Encoding UTF8
# OR
Out-File -FilePath "proxy_pool.txt" -Encoding UTF8
```
unconditionally prepends the 3-byte Byte Order Mark (BOM):
`0xEF, 0xBB, 0xBF` (`\xef\xbb\xbf` or `\ufeff`).

### Downstream Impact
- Tools expecting pure ASCII/UTF-8 lines (like `yt-dlp`, `curl`, `requests`, `urllib`, `ffmpeg`) read the first line with the BOM attached to the hostname:
  ```text
  Raw line 1: \xef\xbb\xbf192.168.110.2:10001:admin@1:admin@1
  yt-dlp proxy URI: http://admin%401:admin%401@\ufeff192.168.110.2:10001
  Result: ERROR: Failed to parse: http://admin%401:admin%401@\ufeff192.168.110.2:10001
  ```
- Because only line 1 contains the BOM, if line 1 fails, the entire proxy pool or request fails on its primary connection.
- In terminal output, the BOM is invisible (`192.168.110.2`), making diagnosis difficult unless inspecting raw byte arrays:
  ```powershell
  Get-Content -Encoding Byte -TotalCount 5 "proxy_pool.txt"
  # Output: 239, 187, 191, 49, 57  <-- 239, 187, 191 IS THE BOM!
  ```

### Safe File Writing Patterns on Windows

#### Option A: Python (Recommended & Standard)
Python 3 writes pure UTF-8 without BOM by default:
```python
with open("proxy_pool.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
```

#### Option B: PowerShell 5.1 with ASCII (for URLs/IPs/Configs)
If the file contains standard ASCII text (IPs, ports, credentials without non-Latin characters):
```powershell
Set-Content -Path "proxy_pool.txt" -Value $lines -Encoding Ascii
```

#### Option C: PowerShell .NET UTF-8 without BOM
If UTF-8 with special characters is strictly required:
```powershell
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllLines("C:\path\to\file.txt", $lines, $utf8NoBom)
```

#### Verification Check:
Always verify the first 5 bytes after modifying critical config/proxy files:
```python
with open("proxy_pool.txt", "rb") as f:
    assert list(f.read(3)) != [239, 187, 191], "FATAL: UTF-8 BOM detected!"
```
