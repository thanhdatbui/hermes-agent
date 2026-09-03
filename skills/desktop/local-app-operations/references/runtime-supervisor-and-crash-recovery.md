# Runtime supervisor and crash recovery

## When a local app “stops”

A surviving terminal, `cmd.exe`, npm parent, or shortcut is not proof that the app is alive. Verify the actual child process and listener:

1. Query the PID bound to the target port with `netstat -ano`.
2. Inspect that PID's command line and parent/child process tree with `wmic` or `Get-CimInstance`.
3. Probe the app's health endpoint, not only TCP connect.
4. Inspect the app's latest logs and the last successful/failed request.
5. Keep neighboring services on adjacent ports separate; never infer the target from an open terminal window.

Classify the incident before changing provider/account settings:

- **Process crash/restart:** target port is absent or owned by another process; upstream/provider evidence may remain healthy.
- **Admission saturation:** target remains healthy, but requests receive a local `503` such as `ALL_TARGETS_SKIPPED` or `chat_admission_busy`.
- **Upstream failure:** target remains healthy and logs show a provider response such as `429`, `403`, or `5xx`.

## Supervisor pattern for a source-launched Windows app

For a user-local app that must recover without elevation:

- Prefer the app's production launcher over a dev server for persistent operation.
- Use a single-instance watchdog with a named mutex.
- Check both the target port and a lightweight health endpoint.
- Poll at a conservative interval (for example 10 seconds), and start only the target app when unhealthy.
- Pass explicit port/environment settings to the child so a neighboring service cannot steal the default port.
- Use a bounded log with rotation; log detection, launch PID, health result, and launch failure.
- Add the watchdog to the user's Startup folder via a minimal `.vbs` launcher when Task Scheduler creation is unavailable to the current token. Do not claim a scheduled task exists unless `schtasks /query` verifies it.
- Never kill an existing healthy instance merely to test the watchdog. A real crash/restart test requires an approved maintenance window or an explicit user instruction.

## Verification

After installing or starting the supervisor, verify all of:

- the launcher file exists at the intended Startup path;
- exactly one watchdog process is running;
- the target app has one healthy listener on the intended port;
- a health probe returns `200`;
- one minimal application canary returns `2xx`;
- the watchdog log shows it is monitoring, with no duplicate-launch entries;
- the neighboring gateway/process/port is unchanged.

Do not overstate root cause when the runtime has no preserved crash stack. Report “child process exited; exact exception not captured” separately from the verified recovery mechanism.
