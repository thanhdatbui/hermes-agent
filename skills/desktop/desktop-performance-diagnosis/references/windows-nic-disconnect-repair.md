# Windows NIC Hardware Reset & Game Disconnect Diagnosis and Repair

## 1. Symptoms & Root Cause Signatures
- **Symptom**: Sudden disconnects or packet drops during online gaming (LoL, Valorant, CS2) or while using game boosters / VPNs (GearUP, ExitLag, Tailscale), despite local internet/router working fine.
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
```

## 3. Proven Fix Procedure (Realtek PCIe GbE Example)

### Step A: Update Ancient Drivers (>2–3 years old or 2015 inbox drivers)
Download the official manufacturer installer (e.g. Realtek PCIe LAN package for Win10/11) and run silent install via elevated execution:
```powershell
Start-Process -FilePath "path\to\setup.exe" -ArgumentList "-s" -Verb RunAs
```

### Step B: Disable Aggressive Power Saving & Hardware Throttling
In `HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}\<Index>`:
- `PnPCapabilities` = `24` (DWord - Prevents OS from cutting power to the NIC)
- `*EEE` = `"0"` (Energy Efficient Ethernet Disabled)
- `*GreenEthernet` = `"0"` (Green Ethernet Disabled)
- `*PowerSavingMode` = `"0"` (Power Saving Mode Disabled)
- `*AutoDisableGigabit` = `"0"` (No auto down-negotiation)
- `ASPM` = `"0"`, `CLKREQ` = `"0"` (Disable PCIe Active State Power Management)
- `*ReceiveBuffers` = `"1024"`, `*TransmitBuffers` = `"1024"` (Expand packet ring buffers to avoid packet drops under burst traffic)

### Step C: Verification
```powershell
Get-NetAdapter | Select-Object Name, Status, LinkSpeed
Test-Connection -ComputerName 8.8.8.8, 1.1.1.1 -Count 5 | Format-Table -AutoSize
```
