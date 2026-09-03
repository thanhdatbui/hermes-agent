# 9Router vs OmniRoute Watchdog Comparison

**Context**: Both watchdogs run on the same machine (ports 20128 and 20129). This documents their patterns for cross-reference.

---

## 9Router Watchdog (Reference Implementation)

**File**: `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1`

### Strengths
- Mutex single-instance: `Local\9Router_Supervisor_Mutex_v2`
- Clean logging with rotation (2MB)
- Stop file pattern (`watchdog.stop`)
- Health check: TCP connect + HTTP `/api/health` (same as OmniRoute)
- Structured `finally` block for mutex cleanup

### Features (Post-Port)
- Mutex single-instance: `Local\9Router_Supervisor_Mutex_v2`
- Clean logging with rotation (2MB)
- Stop file pattern (`watchdog.stop`)
- Health check: TCP connect + HTTP `/api/health`
- Structured `finally` block for mutex cleanup
- Process discovery via `Get-9RouterProcesses` (node.exe `server.js` + child processes + port 20128 owner)
- Process cleanup via `Stop-9RouterProcesses` with 5s drain loop before launch
- Safe variable naming (`$owningPid`) avoiding PowerShell's constant `$PID` collision

### Process Tree (Observed)
```
PID 25172 (watchdog) → PID 49632 (node server.js)
```

---

## OmniRoute Watchdog (Fixed Version)

**File**: `C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`

### Improvements Over 9Router
| Feature | 9Router | OmniRoute (Fixed) |
|---------|---------|-------------------|
| Process discovery | None | Command-line + children + port ownership |
| Process cleanup | None | Full tree kill + 5s grace wait |
| Startup timeout | 3s fixed | 30s configurable, 3s polling |
| Failure threshold | 1 (immediate) | 3 consecutive (30s) |
| Pre-start check | No | Yes |
| Progress logging | Minimal | Detailed (PID, elapsed, stage) |
| Mutex | v2 | v1 (separate namespace) |

### Process Tree (Observed After Fix)
```
PID 238032 (watchdog) → PID 178124 (node run-next.mjs start)
                              ├── PID 120516 (conhost.exe)
                              └── PID 241024 (esbuild.exe --service=...)
```

---

## Cross-Interference Risks

### Port Collision
- 9Router: 20128
- OmniRoute: 20129
- **No collision** — different ports

### Mutex Namespace
- 9Router: `Local\9Router_Supervisor_Mutex_v2`
- OmniRoute: `Local\OmniRoute_Supervisor_Mutex_v1`
- **No collision** — different names

### Startup Folder Entries
Both have `.vbs` launchers in `shell:startup`:
- `9router.vbs` → 9router_watchdog.ps1
- `omniroute_watchdog.vbs` → omniroute_watchdog.ps1
- **Independent** — mutexes prevent each from running twice, but don't cross-block

---

## Recommended Sync Pattern

If adding a new watchdog for another service:

1. **Unique mutex name**: `Local\<ServiceName>_Supervisor_Mutex_v1`
2. **Unique stop file**: `%APPDATA%\<service>\watchdog.stop`
3. **Unique log dir**: `%APPDATA%\<service>\logs\`
4. **Port-specific health check**: Match the service's actual health endpoint
5. **Command-line signature**: Match the exact launcher script/args
6. **Thresholds tuned to service**: Next.js cold start = 30s; simple Node = 10s; Go binary = 5s

---

## Verification Commands (Reusable)

```powershell
# Check both watchdogs running
Get-CimInstance Win32_Process | Where { $_.CommandLine -like '*watchdog.ps1*' -and $_.CommandLine -notlike '*bash*' } | Select ProcessId, CommandLine

# Check both services healthy
curl -s http://127.0.0.1:20128/api/health
curl -s http://127.0.0.1:20129/api/health

# Check port ownership
Get-NetTCPConnection -State Listen | Where LocalPort -in 20128,20129

# Check for duplicate processes
Get-CimInstance Win32_Process | Where Name -eq 'node.exe' | Select ProcessId, ParentProcessId, CommandLine
```