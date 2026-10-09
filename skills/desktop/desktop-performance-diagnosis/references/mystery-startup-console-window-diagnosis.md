# Diagnosing Mystery Startup Console Windows and Background PowerShell Spawns

## Symptom Profile
- On Windows startup or login, a blank or flashing PowerShell / CMD console window pops up on the desktop (e.g. title: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`).
- The window interior may be completely empty / transparent / clear, or flash repeatedly every few seconds.
- User question: *"máy mới bật lên nó nhảy cái này là gì vậy?"* (When machine boots, this window pops up, what is it?).

## Root Causes
1. **Third-Party Background/Companion Apps (e.g. Electron overlays, game aids, hardware utilities):**
   - Apps registered in Startup (`HKCU\...\Run` or shell:startup) polling for target processes (e.g. game clients like `LeagueClientUx*`, Steam, Discord) by executing CLI commands like:
     `powershell -c Get-CimInstance -className Win32_Process | Where-Object Name -Like "LeagueClientUx*" | Select-Object CommandLine | Format-List`
   - In Node.js / Electron, developers using `child_process.exec()` often omit `{ windowsHide: true }`, causing Windows to allocate a visible console window (`conhost.exe` / `powershell.exe`).
   - If the target application is not running, the query returns null/empty output, leaving a blank window visible on screen.
2. **Scheduled Tasks / Logon Triggers:**
   - Tasks running scripts via `powershell.exe` or `cmd.exe` without `-WindowStyle Hidden` or wrapped in `.bat` instead of `.vbs` (`wscript.exe`).

## Diagnostic Fast-Path (Read-Only)

### 1. Correlate Boot and Logon Time
```powershell
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime
```

### 2. Check Startup Registry and Folders
```powershell
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' -and $_.Triggers.ToString() -match 'Logon' }
```

### 3. Extract Exact Executed Command from Windows Event Log (Gold Standard)
Windows PowerShell automatically logs engine startup events with the full command line in the Application log:
```powershell
Get-WinEvent -FilterHashtable @{LogName='Windows PowerShell'; StartTime=(Get-Date).AddMinutes(-30)} -ErrorAction SilentlyContinue |
    Where-Object { $_.Id -eq 400 } |
    ForEach-Object {
        if ($_.Message -match 'HostApplication=([^\r\n]+)') {
            [PSCustomObject]@{
                TimeCreated     = $_.TimeCreated
                HostApplication = $matches[1]
            }
        }
    } | Select-Object -First 10 | Format-List
```
*Look for recurrent commands executed right around boot/logon time.*

### 4. Trace the Parent Process PID
If the process is currently running or recurring:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Select-Object ProcessId, ParentProcessId, CommandLine
```
Then resolve the parent PID to find the launching app:
```powershell
Get-CimInstance Win32_Process -Filter "ProcessId = <ParentProcessId>" | Select-Object ProcessId, Name, CommandLine, Path
```

### 5. Inspect Application Source Code (Electron / ASAR)
If the parent is an Electron app (e.g. in `resources\app.asar`), grep inside the unpacked archive or search string literals:
```powershell
Select-String -Path "<AppDir>\resources\app.asar" -Pattern "<CommandSnippet>" | Select-Object -First 5
```

## Remediation
1. **Immediate user resolution:**
   - Disable the companion app from Windows Startup: Open **Task Manager** -> **Startup** tab -> select the app -> **Disable** (or toggle off "Start with Windows" in the app's settings).
2. **Script / automation resolution:**
   - If spawned by internal batch scripts: wrap with `wscript.exe //B //Nologo script.vbs` or pass `-WindowStyle Hidden -NonInteractive`.
   - In Node.js / Electron child process calls: always specify `{ windowsHide: true }`.
