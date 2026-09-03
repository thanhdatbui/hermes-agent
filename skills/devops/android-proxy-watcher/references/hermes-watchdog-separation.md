# Separating Hermes watchdog from the VPN watcher

Use when the machine no longer uses the Android VPN/proxy path but still needs Hermes Gateway auto-recovery.

## Safe split

1. Confirm the existing proxy/VPN tray is disabled or will be disabled. Do not re-enable it just to preserve the Hermes guard.
2. Check for live farm work before any Gateway restart. A live feed/upload/workflow batch is a hard blocker for restart; configuration and task registration may proceed without restarting Gateway.
3. Create a standalone watchdog that only:
   - enumerates `python.exe` and `pythonw.exe`;
   - matches `hermes_cli.main gateway run` (optionally legacy `serve`);
   - logs `GATEWAY_OK` when present;
   - invokes `hermes gateway start` only when absent.
4. Prefer `start` over `restart` in a recurring watchdog. `restart` can interrupt an otherwise healthy process during a false negative or can kill a live session/batch. Let Hermes' own start/status handling decide whether a service is already running.
5. Register a dedicated Windows Scheduled Task with:
   - an interactive logon trigger;
   - a recurring time trigger, normally every 2 minutes;
   - `MultipleInstancesPolicy=IgnoreNew`;
   - a short execution limit (for example 5 minutes);
   - `StartWhenAvailable=true` and battery-independent settings;
   - a task action containing only PowerShell + the standalone watchdog path (no `gan_proxy_fleet`, ViChanger, ADB, `tun0`, or proxy mapping arguments).

## Windows task XML pitfall

When using `schtasks /Create /XML` from Git Bash/Python, write the temporary XML as UTF-16. Avoid inline shell quoting for Windows paths: Bash can reinterpret backslashes or control sequences such as `\v` and `\a`, producing malformed XML. Build the XML in Python as a raw string or with escaped backslashes, validate it with an XML parser, encode it with `utf-16`, create the task, and delete the temporary file.

## Verification ladder

- PowerShell parser returns `PARSE OK` for the watchdog script.
- Direct smoke run while Gateway is alive returns exit code 0 and writes `GATEWAY_OK`; it must not start/restart Gateway.
- `schtasks /Query /TN "\\Hermes_Gateway_Watchdog" /FO LIST /V` shows `Enabled`, `Ready`, 2-minute repetition, and `Last Result: 0` after `schtasks /Run`.
- `schtasks /Query /TN "\\GanProxyWatcherTray" /FO LIST /V` remains `Disabled`.
- Process inspection shows the independent `pythonw.exe -m hermes_cli.main gateway run` but no `gan_proxy_fleet.py` process.
- Static scan of the standalone script finds no VPN/proxy watcher references.

Do not simulate a Gateway crash or call `hermes gateway restart` during a live farm batch merely to prove the recovery branch. Registering the task and proving the healthy branch is sufficient until a safe maintenance window.
