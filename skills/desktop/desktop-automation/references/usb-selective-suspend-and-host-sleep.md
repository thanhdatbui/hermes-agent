# USB Root Hub Selective Suspend and ADB Host Sleep Rules

## Context & Background
On Windows hosts acting as controller for Android phone farms or high-density USB devices (e.g. 80 Samsung S7s connected via cascading USB hubs), Windows power management frequently resets USB controller buses upon Host Sleep/Wake or RDP reconnect.

## Root Causes & Mechanics
1. **USB Host Controller Selective Suspend**:
   - `USB Root Hub 3.0` has power-saving enabled by default (`MSPower_DeviceEnable.Enable = $true`).
   - When the host computer sleeps (Standby S3) or becomes idle, Windows turns off power to the Root Hub, dropping the USB bus across all downstream hubs and attached phones.
   - Upon wake-up, dozens of USB devices re-enumerate at once. This massive concurrent surge crashes or restarts the background `adb server`.
   - The fresh `adb server` issues concurrent `AUTH_TOKEN` handshakes to all phones. If `/data/misc/adb/adb_keys` on device is bloated (>5KB) or busy, the phones timeout and display the interactive "Allow USB debugging" RSA authorization dialog.

2. **Remediation Pattern for Windows Host**:
   - Disable USB power management across all Root Hubs programmatically via WMI:
     ```powershell
     $targets = Get-CimInstance MSPower_DeviceEnable -Namespace root\wmi | Where-Object { $_.InstanceName -like '*USB\ROOT_HUB*' }
     foreach ($t in $targets) {
         $t.Enable = $false
         Set-CimInstance -CimInstance $t
     }
     ```
   - Disable AC standby and hibernate on farm hosts:
     ```cmd
     powercfg /change standby-timeout-ac 0
     powercfg /change hibernate-timeout-ac 0
     ```

3. **Android Device Screen Timeout Side-Effect**:
   - Device screen turning off (`Display Power: state=OFF` / Dozing) does NOT drop USB ADB connections.
   - However, farm controller software (e.g. Xiaowei / Tiểu Vi) frequently pushes `settings put system screen_off_timeout 2147483647` (`Integer.MAX_VALUE`, ~24.8 days) across all devices to keep screens awake during live mirror viewing.
   - To safely restore automatic screen-off without breaking ADB:
     ```bash
     adb shell settings put system screen_off_timeout 60000  # 1 minute
     adb shell settings put global stay_on_while_plugged_in 0
     ```
