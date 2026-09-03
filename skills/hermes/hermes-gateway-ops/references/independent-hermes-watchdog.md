# Independent Hermes Gateway Watchdog

Use this reference when an Android VPN/proxy watcher is being retired but Hermes Gateway must remain self-healing.

## Design contract

- The proxy/VPN watcher and Hermes recovery are separate services.
- The Hermes watchdog performs only process discovery, logging, and Gateway startup. It must not call ADB, ViChanger, `tun0`, proxy assignment, or `gan_proxy_fleet`.
- Inspect both `python.exe` and `pythonw.exe`; the Windows Gateway commonly runs as `pythonw.exe -m hermes_cli.main gateway run`.
- Prefer `hermes gateway start` when the process is absent. A watchdog should not use `gateway restart` for ordinary absence detection because restart can interrupt a healthy-but-misdetected live session.
- Use a bounded child-process wait and an execution-time limit on the Scheduled Task.

## Portable script shape

```powershell
[CmdletBinding()]
param(
    [string]$HermesExecutable = (Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent\venv\Scripts\hermes.exe'),
    [string]$LogPath = (Join-Path $env:LOCALAPPDATA 'hermes-gateway-watchdog\watchdog.log')
)

$snapshot = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' or Name = 'pythonw.exe'")
$gateway = $snapshot | Where-Object {
    $_.CommandLine -and ([string]$_.CommandLine -match '(?i)hermes_cli\.main\s+(gateway\s+run|serve)')
} | Select-Object -First 1
```

Log `GATEWAY_OK` and exit 0 when found. When absent, validate the executable, call `Start-Process ... -ArgumentList @('gateway', 'start')`, wait at most 45 seconds, log the exit code, and return a non-zero code on failure.

## Scheduled Task registration

Register an independent task such as `\Hermes_Gateway_Watchdog` with:

- `AtLogon` trigger for startup;
- recurring `PT2M` trigger for crash recovery;
- hidden, non-interactive PowerShell;
- `MultipleInstancesPolicy=IgnoreNew`;
- `ExecutionTimeLimit=PT5M`;
- `StartWhenAvailable=true`;
- exact repository script path in the action.

For long PowerShell command lines, write a UTF-16 Task Scheduler XML file and call `schtasks /Create /TN "\\Hermes_Gateway_Watchdog" /XML <file> /F`. Use a temporary XML file outside the repository and delete it afterward. The task action may pass machine-local executable/log paths, but the committed script should default through `$env:LOCALAPPDATA` rather than hardcoding an operator's home or runtime drive.

## Verification ladder

1. PowerShell parser returns `PARSE OK`.
2. Direct smoke test while Gateway is already healthy returns exit 0 and `GATEWAY_OK`; it must not restart the Gateway.
3. Run the Scheduled Task once and verify `Last Result: 0`, `Enabled`, and `Ready`.
4. Query the task XML and confirm the action points to the intended repo file, has both logon and 2-minute repetition triggers, and contains no VPN/proxy action.
5. Scan the committed script for forbidden integration markers (`gan_proxy`, `proxy-watcher`, `vichanger`, `tun0`, `adb`) and for hardcoded operator paths.
6. Do not simulate Gateway death or restart it while a live farm batch is running; the healthy-path smoke and task invocation are sufficient for the first deployment gate.

## Repository handoff

When the watchdog is committed in a tooling repo, stage only the watchdog source. Preserve unrelated dirty files. The Scheduled Task is machine-local runtime state and should be verified separately, not committed as a secret-bearing or operator-specific artifact. Report the repository path, task name, script path, parse/smoke/task results, and whether a live Gateway restart was intentionally deferred.
