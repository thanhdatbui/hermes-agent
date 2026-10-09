# Windows NIC Hardware Reset & Game Disconnect Diagnosis and Repair

## 1. Symptoms & Root Cause Signatures
- **Symptom**: Sudden disconnects, micro-freezes, or packet drops during online gaming (LoL, Valorant, CS2) or while using game boosters / VPNs (GearUP, ExitLag, Tailscale), despite local internet/router working fine.
- **Root Cause Signature in Windows Event Log**:
  - Provider: `Microsoft-Windows-NDIS`, Event ID: `10400`
  - Message: *"The network interface '<Name>' has begun resetting. Reason: The network driver detected that its hardware has stopped responding to commands. This network interface has reset N time(s)..."*
  - Accompanied by DNS client timeouts (Event ID: `1014`).

## 2. Diagnosis Commands (PowerShell via Windows Shell)
```powershell
# 1. Check recent NDIS hardware resets & DNS timeouts (last 6 hours)
$since = (Get-Date).AddHours(-6)
Get-WinEvent -FilterHashtable @{LogName="System"; StartTime=$since} -ErrorAction SilentlyContinue | 
    Where-Object { $_.Id -in @(10400, 1014, 27, 32) -or $_.ProviderName -match "NDIS|e1dexpress|rt640x64|Tcpip" } | 
    Select-Object TimeCreated, Id, ProviderName, Message | Format-List

# 2. Check current driver version & date
Get-WmiObject Win32_PnPSignedDriver | Where-Object { $_.DeviceName -like "*Realtek*GbE*" -or $_.DeviceName -like "*Intel*Ethernet*" } | 
    Select-Object DeviceName, DriverVersion, DriverDate | Format-List

# 3. Check current Advanced Properties
Get-NetAdapterAdvancedProperty -Name "<AdapterName>" | 
    Where-Object { $_.RegistryKeyword -in @('*EEE', 'EnableGreenEthernet', 'GigaLite', 'PowerSavingMode', 'AdvancedEEE', 'AutoDisableGigabit') } | 
    Select-Object DisplayName, DisplayValue, RegistryKeyword, RegistryValue | Format-Table -AutoSize
```

## 3. Proven Fix Procedure (Realtek PCIe GbE Controller)

### Step A: Update Ancient Drivers (>2–3 years old or 2015 inbox drivers)
Download the official manufacturer installer (e.g. Realtek PCIe LAN package for Win10/11) and run silent install via elevated execution:
```powershell
Start-Process -FilePath "path\to\setup.exe" -ArgumentList "-s" -Verb RunAs
```

### Step B: Disable Aggressive Power Saving & Power Management
In `HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}\<Index>`:
- **`PnPCapabilities` = `0` (DWORD)**: Disables "Allow the computer to turn off this device to save power". *(Note: `24` / `0x18` is the default where bit 3 `0x08` power-down is enabled; `0` clears it completely).*
- **`EnableGreenEthernet` & `*GreenEthernet` = `"0"`**: Disables Green Ethernet.
- **`GigaLite` = `"0"`**: Disables Gigabit Lite down-negotiation.
- **`PowerSavingMode` & `*PowerSavingMode` = `"0"`**: Disables Power Saving Mode.
- **`*EEE` & `AdvancedEEE` = `"0"`**: Disables Energy-Efficient Ethernet.
- **`AutoDisableGigabit` & `*AutoDisableGigabit` = `"0"`**: Disables Auto Disable Gigabit.
- **`PowerDownPll` = `"0"`**: Disables PLL power-down.
- **`ASPM` = `"0"`, `CLKREQ` = `"0"`**: Disables PCIe Active State Power Management.
- **`*ReceiveBuffers` = `"1024"`, `*TransmitBuffers` = `"1024"`**: Expands packet ring buffers to avoid packet drops under burst traffic.

### Step C: Automated Remediation Script (Run Elevated)
```powershell
$adapterName = "Slot04 x16" # Change to target adapter name
$baseKey = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"

# Apply Advanced Properties via Cmdlet
Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Green Ethernet' -DisplayValue 'Disabled' -NoRestart -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Gigabit Lite' -DisplayValue 'Disabled' -NoRestart -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Power Saving Mode' -DisplayValue 'Disabled' -NoRestart -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Energy-Efficient Ethernet' -DisplayValue 'Disabled' -NoRestart -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Advanced EEE' -DisplayValue 'Disabled' -NoRestart -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Auto Disable Gigabit' -DisplayValue 'Disabled' -NoRestart -ErrorAction SilentlyContinue

# Apply Registry overrides to all Realtek keys
Get-ChildItem $baseKey | ForEach-Object {
    $p = $_.PSPath
    $desc = (Get-ItemProperty $p -ErrorAction SilentlyContinue).DriverDesc
    if ($desc -like "*Realtek*") {
        Set-ItemProperty -Path $p -Name "PnPCapabilities" -Value ([int]0) -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "EnableGreenEthernet" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "GigaLite" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "PowerSavingMode" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "*EEE" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "*GreenEthernet" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "*PowerSavingMode" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "*AutoDisableGigabit" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "AutoDisableGigabit" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "AdvancedEEE" -Value "0" -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $p -Name "PowerDownPll" -Value "0" -Force -ErrorAction SilentlyContinue
    }
}

# Restart adapter to reload driver cleanly
Restart-NetAdapter -Name $adapterName -Confirm:$false
```

### Step D: Pitfalls & Elevation Notes
- **WMI Error 31**: `Set-NetAdapterPowerManagement -AllowComputerToTurnOffDevice Disabled` fails on many Realtek drivers with `Windows System Error 31` ("A device attached to the system is not functioning"). Always set registry `PnPCapabilities = 0` directly.
- **Medium Integrity / Standard Token**: When running in a non-elevated shell session, launch the PowerShell script using `Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'path\to\script.ps1' -PassThru`.

### Step E: Verification
```powershell
Get-NetAdapter | Select-Object Name, Status, LinkSpeed
Test-Connection -ComputerName 192.168.110.2, 8.8.8.8 -Count 4 | Format-Table -AutoSize
```

## 4. Intermediate Switch & Router Topology Diagnosis (`PC -> Switch -> Router`)
When inserting an intermediate unmanaged/managed switch between PC and Router (e.g. `PC -> Switch -> Ruijie/MikroTik`):
1. **PHY Sleep / Clock Desync**: Unmanaged switches do not actively negotiate fast wakeups. When NIC power-saving (Green Ethernet / EEE) drops PHY power on idle, subsequent traffic bursts fail to re-sync fast enough, triggering NDIS 10400 driver resets.
2. **MikroTik RouterOS v7 Diagnostics**:
   - Check port link flapping & DHCP logs: `/log print where topics~"link" or topics~"dhcp" or topics~"warning"`
   - Check interface drops/errors: `/interface/ethernet/print stats` and `/interface/print stats-detail` (watch `link-downs`, `rx-drop`, `tx-drop`).
   - Check bridge STP loop blocking: `/interface/bridge/port/print`
3. **Ruijie / Reyee Diagnostics**:
   - Check Port Status: ensure port negotiates 1000 Mbps Full Duplex without CRC error / packet drops.
   - Check RLDP (Loop Detection) & Broadcast Storm Control logs to ensure port is not temporarily err-disabled due to switch broadcast frames.
   - Verify Switch IP does not conflict with Gateway (`192.168.110.1` / `192.168.110.2`).

## 5. Multi-Gateway / Dual-Router Farm Topology & Gateway Misrouting Diagnosis
In a hybrid automation farm setup where two routers coexist on the same Layer 2 subnet (`192.168.110.x`):
- **Gateway 1 (`192.168.110.1`)**: Primary consumer ISP (e.g. Ruijie EW3200GX-PRO with FPT direct 1 Gbps) — intended for Host PC, gaming (LoL/TFT/Valorant), personal devices, and direct unproxied Internet.
- **Gateway 2 (`192.168.110.2`)**: Farm infrastructure router (e.g. MikroTik RouterOS v7 with Viettel multi-session PPPoE) — intended for phone farm proxies (`:10001..10035`), local Sing-box containers (`:20001..20080`), and dedicated bot upstream proxies (`TELEGRAM_PROXY`).

### A. Symptom Signature: Game Delay / High Latency on Host PC
- User reports game "delay / lag mạng" (e.g. TFT/LoL inputs delayed, shop freezes, packet drops, game server traceroute failing from hop 6–15), while local ping to both `.1` and `.2` is `0ms`.
- Root cause: Host PC's Default Gateway (`0.0.0.0/0`) has been hijacked or dynamically leased from Gateway 2 (MikroTik / Viettel) instead of Gateway 1 (Ruijie / FPT).
- Consequence: Gaming and desktop traffic gets dumped onto the farm's multi-WAN router, competing with thousands of farm TCP sockets (`TimeWait` bursts, packet discards on NIC) and routing through the farm ISP's international route.

### B. Diagnostic Pre-flight (PowerShell)
```powershell
# 1. Check current Default Gateway and Route
Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object NextHop, RouteMetric, InterfaceAlias

# 2. Check Host Egress Public IP & ISP
(Invoke-RestMethod -Uri 'https://ipinfo.io/json' -TimeoutSec 5) | Select-Object ip, org, city

# 3. Check DHCP Server that assigned Host IP
Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPAddress -ne $null } | Select-Object Description, DHCPServer, DefaultIPGateway
```
If `NextHop` or `DefaultIPGateway` is `192.168.110.2` and `org` shows the farm line ISP (e.g. Viettel) instead of the gaming line ISP (e.g. FPT), the host is misrouted!

### C. Remediation & Decoupling Rule
1. **Host Default Gateway**: MUST point to `192.168.110.1` (Ruijie / FPT). Either set static gateway or configure static IP on Host PC:
   ```powershell
   # Elevated PowerShell
   Set-NetIPAddress -InterfaceAlias "Slot04 x16" -IPAddress 192.168.110.123 -PrefixLength 24 -DefaultGateway 192.168.110.1
   Set-DnsClientServerAddress -InterfaceAlias "Slot04 x16" -ServerAddresses ("8.8.8.8", "1.1.1.1")
   ```
2. **Local App Proxies Remain Untouched**: Applications needing the secondary line (such as Hermes Telegram Gateway) communicate directly over the local L2 subnet:
   - `TELEGRAM_PROXY=http://admin%401:admin%401@192.168.110.2:10001`
   - Since `192.168.110.2` is in the same local subnet (`192.168.110.0/24`), traffic to port 10001/200xx does NOT pass through the default gateway. Changing the Host default gateway to `192.168.110.1` gives gaming direct 1 Gbps FPT while keeping 100% of proxy and farm functionality intact.

