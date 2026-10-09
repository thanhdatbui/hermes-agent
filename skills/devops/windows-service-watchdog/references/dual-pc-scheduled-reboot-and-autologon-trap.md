# Dual-PC Scheduled Reboot Orchestration & Windows AutoAdminLogon Trap

## Context & Farm Hardware Topology
In long-running Android phone farm environments (e.g. Taadaa Phone Farm with 160+ Samsung S7 devices across multi-port USB hubs and box phones), USB bus controllers and hub chipsets experience gradual packet loss, transport hangs, or memory leaks after multiple days of continuous ADB operation.
Periodic full-system reboot of host PCs (Controller `Kibe` and Remote Host `Admin`) resets the PCI/USB host controllers and restores clean ADB transport sockets.

---

## 1. Multi-Host Reboot Order & Network Dependency
- **Topology:** Controller PC (`Kibe`) orchestrates the farm and controls the remote PC (`Admin`, `192.168.110.119`) over SSH (`ssh admin-farm`).
- **Orchestration Order Invariant:**
  - Controller **MUST** trigger the remote host's reboot first:
    ```bash
    ssh admin-farm "shutdown /r /t 30 /f /c 'Scheduled nightly farm maintenance reboot'"
    ```
  - Verify remote SSH command dispatch succeeds.
  - Controller schedules its own local reboot with a grace delay (e.g. 60–90 seconds) allowing in-flight SSH sockets to close cleanly:
    ```powershell
    shutdown /r /t 60 /f /c "Scheduled nightly farm maintenance reboot"
    ```
  - **Fatal Anti-Pattern:** Rebooting Controller first or simultaneously without verification orphans the remote host, causing half-cluster drift where remote jobs crash due to lost controller connections while remote USB hubs remain un-reset.

---

## 2. Farm Dead-Zone Maintenance Window
Farm operational schedules must strictly govern scheduled reboots:
- **Ca 4 (Đêm):** 00:00 - 02:30/03:00 (Feed & upload session).
- **End-of-day cache clear:** 03:00 - 04:00 (`end-of-day-clear-tiktok-cache`).
- **Ca 1 (Sáng) Preflight & Feed:** 05:45 - 06:00.
- **Safe Maintenance Window (Dead Zone):** **04:30 - 05:00 AM**.
  - All 160 devices are idle.
  - No active device locks or running feed runners.
  - Generous buffer (~45 minutes) before Ca 1 preflight wakes up at 05:45 AM.

---

## 3. The Windows AutoAdminLogon & Interactive Task Trap
### The Trap
On Windows, Task Scheduler tasks configured with:
```powershell
LogonType = Interactive (MSFT_TaskPrincipal2)
```
(Such as `Hermes_Gateway`, `Hermes_Gateway_Watchdog`, `Taadaa_ADB_User_Remote`, and UI/browser automation scripts) will **NOT execute** upon system boot unless an interactive Windows user session is logged in.

If a machine has:
```powershell
HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\AutoAdminLogon = 0
```
Upon reboot, the OS stops at the Windows Lock / Sign-in screen. While background Windows Services (`sshd`) start, the interactive user session never spawns. Consequently:
- `Hermes_Gateway` never launches.
- Farm watchdogs and startup loops (`shell:startup` scripts, `.vbs` launchers) never run.
- Remote ADB daemon does not bind interactive keys.

### The Fix
Verify `AutoAdminLogon` on all participating hosts before enabling scheduled reboot:
```powershell
# Check current configuration
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' | Select-Object AutoAdminLogon, DefaultUserName, DefaultPassword

# CRITICAL for Windows 10/11: Disable Windows Hello Passwordless enforcement first!
# If DevicePasswordLessBuildVersion = 2, Windows ignores AutoAdminLogon and prompts for PIN.
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\PasswordLess\Device' -Name 'DevicePasswordLessBuildVersion' -Value 0 -Type DWord

# Enable auto logon: CRITICAL - If user has password (even if PasswordRequired=No), DefaultPassword MUST be set in registry!
# If DefaultPassword is missing, Windows halts at login prompt asking for password on boot.
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'AutoAdminLogon' -Value '1' -Type String
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'DefaultUserName' -Value '<TargetUser>' -Type String
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'DefaultPassword' -Value '<TargetPassword>' -Type String
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'DefaultDomainName' -Value '<TargetComputerOrDomain>' -Type String
# Optional: force auto logon after logoff or disconnect
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'ForceAutoLogon' -Value '1'
```
To test whether a local user has a password non-interactively via PowerShell:
```powershell
Add-Type -AssemblyName System.DirectoryServices.AccountManagement
$pc = New-Object System.DirectoryServices.AccountManagement.PrincipalContext([System.DirectoryServices.AccountManagement.ContextType]::Machine)
$pc.ValidateCredentials('<TargetUser>', '<CandidatePassword>') # Returns True/False
```

---

## 4. Canonical Implementation & Cron Registration (Taadaa Farm)
- **Coordinator Script:** `D:\Taadaa\tools\farm_scheduled_reboot.py` (synced to `%LOCALAPPDATA%\hermes\scripts\`, `deploy\hermes-home\scripts\`, and `OneDrive_Shared`).
- **Preflight Guards:**
  1. `is_in_safe_window()`: Enforces Dead Zone `04:15 - 05:40 AM`.
  2. `get_active_automation_processes()`: Scans `psutil` for running feed/render scripts (`run_tiktok.py`, `random_batch_render.py`). Aborts if busy.
  3. `get_active_device_locks()`: Scans `~/.codex/device-locks/`. Aborts if any owner PID is alive.
  4. `check_admin_ssh_liveness()`: Verifies Admin SSH reachability. If Admin is offline, aborts Kibe reboot to preserve cluster parity.
- **Cronjob Configuration:**
  * Job name: `farm-scheduled-pc-reboot`
  * Schedule: `45 4 * * 1,3,6` (04:45 AM on Mon, Wed, Sat — every 2-3 days).
  * Deliver: `telegram:-5373649734` (Farm Alert) with `no_agent=True`.
