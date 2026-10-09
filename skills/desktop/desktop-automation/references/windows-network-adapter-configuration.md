# Windows Network Adapter & Default Gateway Reconfiguration

Patterns, pitfalls, and verification for reconfiguring network interfaces, switching default gateways, and managing routing on Windows hosts from an unelevated Hermes shell (git-bash / MSYS).

---

## 1. Context & Elevation Prerequisites

Hermes terminal commands execute under git-bash / MSYS as standard user tokens (`IsInRole(Administrator) -> False`). Modifying network adapters, static IPs, gateways, or routing tables requires local Administrator privilege.

### Elevation Preflight Check
```powershell
# Check current shell elevation
powershell.exe -NoProfile -Command "([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"

# Check UAC silent auto-elevation policy
powershell.exe -NoProfile -Command "Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System -Name ConsentPromptBehaviorAdmin"
```
- If `ConsentPromptBehaviorAdmin` is `0`, elevated child processes run silently without modal UAC dialog prompts.

### Headless RunAs Execution Pattern
Never invoke long, escaped multi-line commands inside `Start-Process -ArgumentList`. Write a discrete `.ps1` script with transcript logging, execute with `-Wait`, then read the log:
```powershell
powershell.exe -NoProfile -Command "Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'C:\Users\<user>\script.ps1'"
```

---

## 2. Safe Gateway & IP Reconfiguration Workflow

### Goal
Switch the default gateway (e.g. between dual ISPs on the same LAN subnet) without dropping the interface IP or severing local inter-device communication.

### Configuration Script Template
```powershell
$ErrorActionPreference = 'Stop'
$logFile = "C:\Users\<user>\set_gateway.log"
Start-Transcript -Path $logFile -Force

try {
    $alias = "Slot04 x16"
    $ip = "192.168.110.123"
    $mask = "255.255.255.0"
    $newGateway = "192.168.110.1"
    $gwMetric = 10

    # Atomic static IP and gateway update via netsh
    netsh interface ip set address name="$alias" static $ip $mask $newGateway $gwMetric
    
    # Configure DNS
    netsh interface ip set dnsservers name="$alias" static 8.8.8.8 primary
    netsh interface ip add dnsservers name="$alias" 1.1.1.1 index=2
    
    # Dump active default routes for verification
    Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Format-Table -AutoSize
} finally {
    Stop-Transcript
}
```

### Safety Rules
1. **Never drop the IP:** Do not use `netsh ... source=dhcp` followed by `set address` if the machine is remote or accessed over the network. Setting static IP directly keeps connection alive.
2. **Subnet Route Preservation:** Even when the default gateway (`0.0.0.0/0`) changes to Router A (`192.168.110.1`), local traffic to Router B (`192.168.110.2`) or other machines on the `/24` subnet routes directly without going through the gateway.
3. **Artifact Cleanup:** Always delete temporary `.ps1` and `.log` files after verification.

---

## 3. Verification Checklist

1. **Verify Default Route:**
   ```powershell
   powershell.exe -NoProfile -Command "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Format-Table -AutoSize"
   ```
   *Expected:* NextHop points to the target gateway IP with the assigned route metric.

2. **Ping Gateway:**
   ```bash
   ping -n 4 192.168.110.1
   ```
   *Expected:* 0% packet loss, RTT < 1ms.

3. **Verify Public IP & Egress ISP:**
   ```bash
   curl -s https://ipinfo.io/json
   ```
   *Expected:* Public IP and ASN / Org reflect the new ISP line.

4. **Verify Internal Cross-Gateway Services (e.g. Telegram Proxy / MikroTik):**
   ```powershell
   powershell.exe -NoProfile -Command "Test-NetConnection -ComputerName 192.168.110.2 -Port 10001"
   ```
   *Expected:* `TcpTestSucceeded : True` (direct subnet routing works).

5. **Verify Hop Trace & External Latency:**
   ```bash
   tracert -d -h 6 8.8.8.8
   ping -n 4 8.8.8.8
   ```
   *Expected:* Hop 1 is the new gateway; subsequent hops traverse the target ISP core network.
