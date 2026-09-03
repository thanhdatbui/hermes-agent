# PowerShell 5.1 pitfalls + tray debugging (2026-08-11 session)

Transcript-level detail for debugging `proxy-watcher-only-tray.ps1` / `GanProxyWatcherTray`
on Windows PowerShell 5.1. Commits: `138ebc2` (crash + pattern) + `5519ae9` (pythonw) on automation-core master.

## Empty-array unroll → $null (bug 1)

```powershell
function Get-Snap { try { return @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction Stop) } catch { return @() } }
$s = Get-Snap
$null -eq $s   # TRUE when no python.exe exists — @() unrolled to nothing on return
```

Empty array output from a function = no output = `$null` at the caller.
`[Parameter(Mandatory = $true)]` then throws:
`Cannot bind argument to parameter 'Snapshot' because it is null.`

Fix (comma-unroll keeps it an array, even empty):

```powershell
function Get-PythonProcessSnapshot {
    try {
        $snap = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' or Name = 'pythonw.exe'" -ErrorAction Stop)
        return ,$snap
    } catch { return ,@() }
}
```

## Mandatory [object[]] rejects EMPTY arrays too (bug 2)

After fixing the null, the next error:
`Cannot bind argument to parameter 'Snapshot' because it is an empty array.`
(`ParameterArgumentValidationErrorEmptyArrayNotAllowed`)

`AllowEmptyArray` is NOT available in Windows PowerShell 5.1 — adding it gives:
`Property 'AllowEmptyArray' cannot be found for type 'System.Management.Automation.CmdletBindingAttribute'`
(PS 5.1 ParameterAttribute only has AllowEmptyString / AllowEmptyCollection / AllowNull).

Fix: drop `Mandatory` from the array parameter — comma-unroll upstream already guarantees it is
never `$null`, and `Where-Object` over an empty array is a no-op (returns nothing, no error).

```powershell
function Get-ProcessFromSnapshot {
    param(
        [object[]]$Snapshot,                              # no Mandatory
        [Parameter(Mandatory = $true)][string]$Pattern
    )
    $entry = $Snapshot | Where-Object { $_.CommandLine -and ([string]$_.CommandLine -match $Pattern) } | Select-Object -First 1
    ...
}
```

## Hermes guard must match BOTH name and pattern (bug 3 — the session-killer)

Gateway real process: `pythonw.exe -m hermes_cli.main gateway run` (from `Hermes_Gateway.vbs`).

Two independent guard bugs made `Test-HermesGatewayAlive` always false:
1. Pattern was `hermes_cli\.main\s+serve` — actual is `gateway run`.
2. Snapshot filter was `Name = 'python.exe'` — gateway is `pythonw.exe` (windowless GUI subsystem).

Result: `hermes-health.log` shows `HERMES_DOWN ... streak=2` → `HERMES_RESTART_ATTEMPT` → `hermes.exe gateway restart` every 10 min.
Each restart kills the running agent session mid-turn ("gateway shut down" / "Operation interrupted").

Fixed check:
```powershell
$gw = Get-ProcessFromSnapshot -Snapshot $snapshot -Pattern '(?i)hermes_cli\.main\s+(gateway\s+run|serve)'
# snapshot filter: "Name = 'python.exe' or Name = 'pythonw.exe'"
```

Diagnosis path when sessions keep dying: `tail D:\CodexRuntime\codex_gmail_debug-gan-proxy\hermes-health.log`
look for `HERMES_RESTART_ATTEMPT` repeats (10-min cadence = guard false-negative), not network.

## Windows process-tree forensics via git-bash

- `wmic process where "name='powershell.exe'" get processid,parentprocessid,creationdate,commandline /format:list` —
  output blocks per process; **format:csv prints Node,CommandLine,ProcessId in that order** (cut -f3 for PID, NOT -f2).
- PowerShell `-Command "... \"Name='python.exe'\" ..."` quoting trap: inside a bash single-quoted string,
  don't double the single quotes for WMI filters — write `-Filter "Name = 'python.exe'"` literally and let PS
  double-quote wrap it; doubling (`''python.exe''`) produces a literal `''` and WMI rejects the query.
  Reliable: `powershell -NoProfile -Command 'Get-CimInstance Win32_Process -Filter "Name = ''python.exe''"'` fails;
  use `wmic process where "Name='python.exe'"` (bash handles it) or Get-CimInstance with backtick-escaped quotes.
- Windows does NOT reparent orphans: a dead parent's children keep the stale PPID. Same-PPID + same-second
  creation = same parent spawned both (launcher chain vs siblings).
- PID reuse: matching a PID to an old listing is unreliable; always re-check with CreationDate.
- Your own probe commands (bash → powershell children) run under the gateway process tree (ppid = gateway PID,
  e.g. 436) and match the same `-like '*proxy-watcher-only-tray*'` filters → count inflation. Filter by
  ProcessName (`powershell.exe` running the .ps1) + start time, or grep out your own probe.

## schtasks /run semantics

- `schtasks /run /tn "X"` while X is running → no-op: `INFO: scheduled task "X" is currently running.`
  It does NOT restart or re-fire the task.
- Repeated `/run` attempts + kills create overlapping partial chains (wrapper without tray, etc.).
  Clean procedure: kill ALL matching processes (tray + gan_proxy_fleet python trees), verify 0 leftovers,
  then `/run` once, sleep 15, verify single tree: tray (ppid = Task Scheduler ~2996) → wrapper → python → python312.
- Task `Last Result` decoding: `-1073741510` = 0xC000013A (console close / Ctrl+C — user killed it);
  `1` = script threw at startup; `267009`/`267014` = task-terminated family (0x41301/0x41306).

## Launcher chain vs duplicate watcher

Legit tree: `tray powershell → wrapper powershell (run-proxy-watcher.ps1) → python-envs\Scripts\python.exe →
Python312\python.exe` (child), all with the SAME `gan_proxy_fleet.py watch --all --workers 80 ...` cmdline.
`watch` acquires `watcher-singleton.lock` (msvcrt LK_NBLCK) → only ONE watch loop runs; a second watcher
fails closed with `RuntimeError: watcher singleton is already held`.
Always check PPIDs before declaring "2 watchers = duplicate".

## Why all machines FINAL_BLOCKED (no error message)

`FINAL_BLOCKED` with empty `error` for every mapped machine + few devices in `adb devices` = farm offline;
watch cycle ends fail-closed (exit 2), tray respawns in 15s, next cycle retries. This is the steady-state
cycle when phones are unplugged/off. Cadence ~6.5 min per cycle. Do not "fix" it.
Only investigate when machines ARE in `adb devices` but stay unblocked without VPN events.

## Reboot-readiness check (does it auto-start after restart?)

1. `schtasks /query /tn "\GanProxyWatcherTray" /v /fo LIST` → `Scheduled Task State: Enabled` + `Schedule Type: At logon time`.
2. File on disk has all fixes: `grep -cF "Name = 'python.exe' or Name = 'pythonw.exe'"` (1), `grep -cF "gateway\s+run|serve"` (1), `grep -c "return ,\$snap"` (1).
3. Tray self-heals if D: not mounted at logon: `Start-ProxyWatcher` returns an error string (path checks) instead of throwing; the 15 s `Ensure-ProxyWatcher` timer keeps retrying with a 15 s restart-after cooldown.