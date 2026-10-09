# Game Network Latency & Local Automation Interference Diagnosis

## 1. Symptom Distinction: "Delay" vs "Freeze / Stutter"
- **User says "delay" / "lag" in gaming context**: Usually refers to network latency, packet loss, or server response lag (delayed champion movement, sluggish ability casts, delayed item equip), NOT necessarily local GPU frame-drops or display input-lag.
- **Critical Pitfall**: Never rule out network issues based solely on ICMP ping to `8.8.8.8` or `1.1.1.1`. Game traffic uses UDP to distinct regional game clusters (e.g. Riot VN2 / SGP), which can suffer from ISP peering bottlenecks or packet loss that public DNS resolvers never encounter.

## 2. Extracting the Exact Game Server Target
Do not guess IP addresses. Extract the active game server IP and port directly from live game logs or command-line:

```powershell
# League / TFT: Extract ServerIP and ServerPort from game logs or process command lines
Get-ChildItem "$env:LOCALAPPDATA\TFT\Saved\Logs\TFT.log" -ErrorAction SilentlyContinue | ForEach-Object {
    Select-String -Path $_.FullName -Pattern 'ServerIP=([0-9\.]+)\s+-ServerPort=(\d+)' | Select-Object -Last 1 | ForEach-Object {
        [PSCustomObject]@{
            ServerIP   = $_.Matches.Groups[1].Value
            ServerPort = $_.Matches.Groups[2].Value
        }
    }
}

# Inspect active UDP endpoints for the game process
$gamePids = (Get-Process | Where-Object { $_.ProcessName -match 'TFTClient|League of Legends' }).Id
Get-NetUDPEndpoint | Where-Object { $_.OwningProcess -in $gamePids } | Select-Object OwningProcess, LocalAddress, LocalPort
```

## 3. Detecting Local Host Network Saturation & Buffer Drops
When automation workloads (farm operations, multi-worker ADB over Wi-Fi/TCP, video uploaders, proxy daemons) run on the same desktop:

```powershell
# 1. Check NIC Packet Discard Counters (Buffer Overflow)
Get-Counter '\Network Interface(*)\Packets Received Discarded', 
            '\Network Interface(*)\Packets Outbound Discarded', 
            '\Network Interface(*)\Bytes Total/sec' | 
    Select-Object -ExpandProperty CounterSamples | 
    Where-Object { $_.InstanceName -notmatch 'isatap|teredo|loopback' } | 
    Format-Table InstanceName, CookedValue -AutoSize

# 2. Check Connection State Churn & NAT / Tracking Table Load
Get-NetTCPConnection | Group-Object State | Select-Object Count, Name | Format-Table -AutoSize

# 3. Identify Processes Flooding TCP Sockets (TimeWait / CloseWait / Proxy Ports)
Get-NetTCPConnection | Where-Object { $_.State -eq 'TimeWait' } | 
    Group-Object RemoteAddress, RemotePort | 
    Sort-Object Count -Descending | Select-Object -First 10 Count, Name | Format-Table -AutoSize

# 4. Check Top Established TCP Owners
Get-NetTCPConnection | Where-Object { $_.State -eq 'Established' } | 
    Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 10 Count, Name | ForEach-Object {
        $proc = Get-Process -Id $_.Name -ErrorAction SilentlyContinue
        [PSCustomObject]@{ Count = $_.Count; PID = $_.Name; ProcessName = $proc.ProcessName }
    } | Format-Table -AutoSize
```

## 4. Diagnosing Route Peering & ISP Hops
```powershell
# Trace route to the exact game server IP (limit hops and timeout to stay fast)
tracert -d -w 1000 -h 15 <ServerIP>
```
- **Hop 1 (<1ms)**: Local router/gateway (MikroTik / Ruijie).
- **Hops 2-5**: ISP local aggregation (Viettel / VNPT / FPT).
- **Hops 6+**: ISP international / transit gateway (NTT, Singtel, etc.). Look for sudden latency spikes (e.g. 24ms -> 100ms+) or consecutive timeouts indicating peering congestion or packet drop.

## 5. Remediation Priority
1. **Local Concurrency Throttle**: Throttle or pause background multi-worker batch tasks (e.g. 40-worker feed sessions, bulk video uploads) during competitive gameplay to clear NIC packet discards.
2. **Gamer Routing / VPN / Booster**: If ISP transit peering is congested (hop 6+ drop), route game UDP packets through a game booster (GearUP, ExitLag) or optimized tunnel (WARP/VPN) to bypass congested ISP nodes.
