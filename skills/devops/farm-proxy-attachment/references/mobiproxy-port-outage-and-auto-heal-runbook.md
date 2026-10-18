# MobiProxy Port Outage & Auto-Healing Runbook (2026-10-18)

## 1. Problem Description: Singbox 10054 / 502 Bad Gateway
Farm Kibe devices route egress via local Singbox router instances on `192.168.110.2:20001..20080`.
Each Singbox port forwards to an upstream MobiProxy port on `test.taadaa.click:5101..5138` (32 ports across Lan 1 to Lan 4).

When an upstream 4G modem on the MobiProxy box drops connection or enters a stale state:
1. TCP socket to Singbox (`192.168.110.2:200xx`) connects, but outbound egress fails with:
   - Python: `[WinError 10054] An existing connection was forcibly closed by the remote host` or `HTTP Error 502: Bad Gateway`
   - Android Preflight: `required router proxy is unreachable for <serial>: global proxy (<proxy>) egress IP verification failed: ... dial tcp ... i/o timeout`
2. Watchdog previously misclassified this if error timestamps contained `:0`.

## 2. MobiProxy Port-to-Singbox Mapping Example
| Device | Singbox Local Port | MobiProxy Upstream Port | Modem Line |
|:---|:---|:---|:---|
| Máy 7 | `192.168.110.2:20007` | `test.taadaa.click:5107` | Lan 1 (mobi7) |
| Máy 67 | `192.168.110.2:20067` | `test.taadaa.click:5135` | Lan 4 (mobi35) |
| Máy 69 | `192.168.110.2:20069` | `test.taadaa.click:5137` | Lan 4 (mobi37) |

*Note:* ALL machines without exception run through proxy. Direct routing is strictly prohibited on the farm.

## 3. Diagnostic & Auto-Healing Procedure

### Step 1: Rapid Health Scan (Zero-Side-Effect)
Run check-only scan to pinpoint dead ports across the 32-port cluster:
```bash
python "D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py" --check-only
```
- Inspect table for ports with `Health == DEAD` (`API Stat == false` or `TCP Socket == FAIL`).

### Step 2: Auto-Heal Dead Ports
Trigger `/proxy_recreat` to reboot the specific modem line without restarting the entire box:
```bash
python "D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py" --check-and-heal
```
- The script targets only dead ports, calls `/proxy_recreat`, waits 15s for modem redial, and verifies the new live egress IP.

### Step 3: Verify End-to-End Egress Through Singbox
Test from Host Kibe:
```python
import urllib.request
proxy = 'http://192.168.110.2:20069'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))
print(opener.open('http://ifconfig.me/ip', timeout=5).read().decode().strip())
```
Must return valid public IPv4 (e.g. `116.107.x.x`).

### Step 4: Ensure Watchdog Daemon is Active
Verify cronjob `mobiproxy-auto-healer-watchdog` (Job ID: `7e5e3980dde1`) is scheduled every 5 minutes (`*/5 * * * *`). If paused, resume it:
```python
cronjob(action='resume', job_id='7e5e3980dde1')
```

## 4. On-Device Inspection O(1)
Verify device Wi-Fi and proxy configuration using:
```bash
python D:/Taadaa/tools/inspect_machine.py <N>
```
Output confirms:
- `• Wi-Fi IP: 192.168.110.x`
- `• Proxy: 192.168.110.2:200xx`
- `• Current Focus: ...`
