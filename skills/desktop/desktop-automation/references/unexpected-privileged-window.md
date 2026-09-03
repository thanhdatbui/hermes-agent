# Unexpected privileged window: evidence recipe

Use when an unexpected Administrator PowerShell/terminal appears, especially after a command was discussed or typed on another machine.

## Evidence sequence

1. Preserve the scene. Do not close the window, change firewall state, restart services, or kill unrelated workers before attribution is recorded.
2. Record target PID, title, start time, owner, parent PID, executable path, command line, main window handle, and child `conhost.exe`.
3. Inspect the parent chain. If the parent has exited, record that fact as an attribution blocker rather than guessing.
4. Read the PowerShell Operational log in a narrow interval around process creation. Search script-block events for the exact command and for malformed concatenations.
5. Read the user's PSReadLine history, but treat it as evidence that text was entered in a local PowerShell session—not proof of who entered it or that it succeeded.
6. Correlate Windows Firewall event IDs 2006/2097 and verify the actual profile state independently.
7. Check active logon sessions and remote-control services/sessions. A live remote service proves a possible path, not that it caused this process.
8. Report each conclusion as `confirmed`, `excluded`, or `unproven`.

## Typical interpretation

- A local PID with the local user owner confirms the window exists on that machine.
- A Telegram instruction or a command shown in a remote chat does not itself execute locally.
- A PSReadLine entry such as `...localport=20129netsh...` can explain `netsh` help output caused by a bad paste, but it cannot identify the actor.
- If process-creation auditing is unavailable and the parent process is gone, actor attribution is unproven.
- If an unelevated diagnostic shell receives Access Denied when stopping the elevated target, report the blocker and do not widen the action without explicit authorization.

## Minimal report

- `Confirmed:` local process/window, time, owner, exact command/history evidence, independent security state.
- `Excluded:` claims contradicted by local evidence.
- `Unproven:` actor, remote source, or whether a historical command succeeded when no execution result exists.
- `Blocker:` missing parent/audit data or insufficient privilege.
