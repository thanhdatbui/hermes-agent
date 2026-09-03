---
name: desktop-automation
description: Best practices and safety patterns for using computer-use and desktop automation.
---

# Desktop Automation Best Practices

This skill captures learnings and pitfalls for driving the user's desktop via tools like `computer_use`.

## Safety & Style Guidelines
- **User Preference (Action-First vs. Passive Instructions):** When the user sends a screenshot of an app error, desktop toast, or sync warning, they expect the agent to immediately use tools to diagnose and remediate the issue directly — do not just explain the cause and list manual steps for the user to do unless user intervention is strictly required.
- **Autonomous Operation:** The user expects autonomous operation but prioritizes not having their active work interrupted.
- **Do Not Disrupt:** Never close windows, log out, or perform destructive actions unless explicitly requested. Always verify the element label in a SOM capture before clicking, especially near window controls.
- **Communication:** If the AI is struggling to interact with a specific app (e.g., Chrome/Browser), stop and explain why rather than repeatedly sending potentially destructive commands.

## Pitfalls & Troubleshooting
- **Windows Cloud Storage (iCloud / OneDrive) Placeholders Stall Bulk Copy/Archive:**
  - Files inside `C:\Users\<user>\iCloudDrive` or OneDrive with Files On-Demand enabled are virtual NTFS reparse points / sparse placeholders.
  - Naive file traversal (`os.walk`, `shutil.copy2`, `robocopy`, `7za`) on placeholder files forces Windows to synchronously request the file stream from the remote cloud provider, causing scripts/terminal commands to hang indefinitely until hitting timeout.
  - *Fix:* Check file offline attributes (`FILE_ATTRIBUTE_OFFLINE` / `0x1000`) or exclude cloud-synced folders from batch local archiving unless files are explicitly hydrated/pinned locally.
- **Fast Mass-File Deletion on Windows (NTFS):**
  - When removing large folders containing 50,000–200,000+ loose files (e.g. `node_modules`, `.venv`, old browser caches/profiles), Python's `shutil.rmtree` or sequential deletion can take 15–30+ minutes due to per-file userland stat overhead.
  - *Fix:* Invoke native NTFS removal via `cmd.exe /c rd /s /q "<path>"` (using list args `['cmd.exe', '/c', 'rd', '/s', '/q', path]` to avoid shell quoting traps). It runs directly in kernel space and finishes in seconds.
- **Installing & Launching Background Cloud Sync Clients (Google Drive Desktop):**
  - Install silently via winget: `winget install --id Google.GoogleDrive -e --silent --accept-source-agreements --accept-package-agreements`.
  - Launching GUI/background services from git-bash: never run `GoogleDriveFS.exe` directly in the foreground (blocks console). Use `cmd.exe /c start "" "C:\Program Files\Google\Drive File Stream\<version>\GoogleDriveFS.exe"` (or Python detached `subprocess.Popen`) to detach cleanly.
  - **Resolving Google Drive "Lost and Found" (`Bị thất lạc và đã tìm thấy`) Unsynced File Errors:**
    - Stuck files live under `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\`.
    - Check if the file exists at the target path on `G:\` (Google Drive virtual mount). If safe, back up the orphaned file to a local staging folder (e.g. `D:\backup_gdrive_lost_and_found\`) and delete/clear the file inside the `lost_and_found` folder.
    - *Crucial Restart Step:* Moving files out of `lost_and_found` while `GoogleDriveFS.exe` is running leaves the in-memory toast/sync error active. You must restart Google Drive (`taskkill /F /IM GoogleDriveFS.exe` followed by detached launch) and verify `%LOCALAPPDATA%\Google\DriveFS\Logs\drive_fs.txt` that `G:\` mounts cleanly with 0 errors to permanently dismiss the notification.
- **Multi-Cloud Backup Sync Architecture (OneDrive -> Google Drive 5TB & iCloudDrive):**
  - Use custom multi-threaded Python scanner (`os.walk` + `ThreadPoolExecutor`) rather than bare `robocopy` when syncing across cloud/virtual drives (e.g. `G:\` Google Drive File Stream, `C:\Users\<user>\iCloudDrive`). Virtual filesystem drivers experience high network latency / throttling on recursive stat queries over 10,000+ loose files.
  - Exclude temporary/lock artifacts: `.849*` (OneDrive internal lock GUIDs), `~$*`, `*.tmp`, `desktop.ini`, and dev bloat (`node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.git`).
  - Deploy as a silent watchdog in Hermes Cron (`no_agent: true`, schedule `0 */6 * * *`): runs `sync_onedrive_multicloud.py`, exits silently when up to date, reports concise summary on updates/errors.
- **Opening a file/editor for the user from the agent shell (Windows/git-bash)** — when the user must edit a file (e.g. paste a secret into `.env`) and `computer_use` is unavailable or `start` silently fails:
  - `cmd //c start "" notepad "C:\path"` can return exit 0 with **no process spawned** — never trust it; verify with `wmic process where "Name='notepad.exe'" get ProcessId`.
  - Bare `notepad.exe "path"` in the terminal tool **blocks** (GUI app holds the console) and the timeout kills the tree — never run it foreground.
  - Literal `&` backgrounding is rejected by the terminal tool. **The reliable fallback: `explorer.exe "C:\path\to\file"`** — opens the file with its default association (`.env` → Notepad) and returns immediately.
  - PowerShell via bash: **single-quote the whole `-Command '...'`** — double quotes make bash expand `$_` (e.g. `{$_.MainWindowTitle}` becomes `{3.MainWindowTitle}` → "term not recognized" spam).
  - `tasklist //FI "IMAGENAME eq X"` silently fails in git-bash (double-slash option, same as `schtasks //Query`) — use `wmic process where "Name='X'" get ...` instead.
  - `explorer.exe` can spawn duplicate windows for the same file — dedupe: `powershell -NoProfile -Command 'Get-Process notepad | Select-Object -First 1 | Stop-Process -Force'`, then confirm one remains via `Get-Process notepad | Select-Object Id,MainWindowTitle` (title shows `<file> - Notepad`).
- **Background Interaction Failures:** Background input (like `type` or keyboard shortcuts) often fails for specific window classes (e.g., `Chrome_WidgetWin_1`). 
  - *Fix:* Bring the window to front (`focus_app` or user-assisted) or explicitly request a foreground-mode action if the tool supports it.
- **Element Mapping Errors:** UI elements in SOM/AX captures can shift. Always perform a fresh `capture` immediately before a `click` or `type` action to ensure indices are valid.
- **Identifying Targets:** If an app is not found, use `list_apps` to verify the exact string expected by `cua-driver` before trying to target it with `capture` or `focus_app`.
- **`computer_use` capture returns 0×0 / empty elements while `hermes computer-use doctor` reports ALL OK** (verified 2026-08-13): the cua-driver MCP session is a zombie. Doctor only health-checks the driver binary, not the live MCP session. Confirm by checking the Hermes agent log (`~/AppData/Local/hermes/logs/agent.log`) for `session 'hermes-<id>' has ended; tool call '<...>' was rejected. Call start_session with this id to revive it`. Fix = a fresh cua-driver session (restart the gateway or kill+respawn cua-driver). Note: `Stop-Process`/`taskkill /F /IM cua-driver.exe` may be access-denied and the process survives — and the user may explicitly forbid a gateway restart while other processes are live; then fall back to a manual action on the user's machine instead of forcing it.

## Cua-driver lifecycle and protocol mismatch recovery
- `hermes computer-use doctor` is a binary/host health check, not proof that the live daemon and MCP client speak the same protocol. A 0×0 capture plus `Unknown method: metadata` or repeated CLI-fallback failures means the daemon is stale or protocol-incompatible.
- After `hermes computer-use install --upgrade`, an already-running daemon can remain on the old version. Verify the daemon PID/version separately from the Hermes `cua-driver mcp` client; do not assume the upgrade replaced the live daemon.
- Prefer the smallest restart: stop only the stale daemon, then start the registered `cua-driver-serve` task again. On Windows, `Stop-Process` can return access denied; use the driver's own stop command or the registered task/process termination path, and verify the old PID is gone before starting the new daemon. Do not kill Chrome or its user profile.
- Restarting the gateway from inside the gateway is blocked by design. If a gateway restart is genuinely required, launch it from an external shell; otherwise replace the stale CUA daemon first.
- Verification gate: run `cua-driver status`, confirm the new daemon PID, then call `computer_use capture`. Accept the repair only when the capture has non-zero dimensions and identifies the target app/window. Never report success from a click/capture request that has not been independently re-captured.

## Execution/reporting correction
- When the user says to fix it, execute the narrowest diagnostic/fix immediately; do not narrate a plan or claim a component is fixed before the verification tool result arrives.
- For Vietnamese status reports, be concise: state the root cause, the exact component changed, the live verification result, and any remaining blocker. Avoid repeated progress announcements and avoid saying “đã xong” until the final capture/state check passes.

## Application update vs. source-repository update
- First identify what the user means by “update”: a running/installed application, a source checkout, or both. Treat “update the app” as an application-operations task by default; do not start with `git status`, stash, rebase, merge, or source edits unless the user explicitly asks to update the repository/source.
- For a running local app, inspect its actual launch mechanism (shortcut/installer/updater/service), executable or command line, version/status endpoint, and package/update channel before touching the source tree. Keep application state/data separate from repository state.
- If the app is currently running, verify whether the requested updater can update in place and whether a restart is required. Do not kill or restart it merely to make a source checkout look current; preserve the live service until the app-level update path is known.
- If discovery shows only a development command such as `npm run dev`, report that it is a source checkout/dev instance rather than assuming it is the installed application. Ask or state the blocker before performing repository operations.
- When the user corrects “app, not repo,” stop repository work immediately, verify no destructive Git operation remains in progress, and return to app-level discovery. Keep the response concise and acknowledge the scope correction without defending the prior workflow.
- Do not treat a user's broad “update it” consent as permission to invent extra disruptive steps. In particular, `taskkill` is not a prerequisite for updating source/dependencies; omit it unless restarting the actual runtime is independently required and in scope.
- For a repo-backed dev instance, separate the gates: (1) identify/update the source revision, (2) install dependencies, (3) run the build, (4) start/reload the app, (5) verify the live health endpoint. Report each gate in Vietnamese and do not call the app updated until the live endpoint answers.
- If the upstream revision contains a reproducible build-breaking defect, make the smallest source correction needed for the requested app update, record the exact file/line and build result, and keep unrelated user changes backed up rather than silently merging them.

See `references/application-vs-repository-update.md` for the checklist and evidence pattern for distinguishing an installed/running app update from a source-repository update. See `references/omniroute-update-lessons.md` for the OmniRoute-specific update/build/health sequence and failure patterns. See `references/gpmlogin-local-api-cdp.md` for the GPMLogin Local API + Playwright CDP background automation recipe.

## Unexpected privileged windows and cross-machine attribution
- Trigger: the user sees an unexpected Administrator terminal, firewall help/error output, or says the command was typed on another machine.
- First distinguish **where the command was typed** from **where the visible process/window exists**. A Telegram message or remote instruction alone is not proof that the local desktop executed it; require local process and event evidence before attributing it to a bot, Hermes, or a remote machine.
- Inspect without modifying state: target PID/title/start time/owner, parent PID and surviving parent chain, child console host, PowerShell operational events, PSReadLine history, relevant firewall event records, active remote-control services/sessions, and exact command-line/script evidence. Use a narrow time window around process creation.
- Correlate the exact malformed command in history or script-block logs. A concatenated paste such as `...localport=20129netsh...` explains a `netsh` “specified value is not valid” help screen, but does not identify the actor by itself.
- Label findings `confirmed`, `excluded`, or `unproven`. If the parent has exited or process-creation auditing is unavailable, actor attribution remains unproven; do not turn timing or chat content into proof.
- If an elevated target cannot be stopped from the current unelevated shell and the user did not explicitly authorize elevation, do not broaden the action or kill unrelated workers. Report the access-denied blocker and leave the target state accurately stated.
- Verify security postconditions independently (for example, all firewall profiles still enabled) and distinguish “command history exists” from “the command succeeded.”

See `references/unexpected-privileged-window.md` for the concise evidence recipe and attribution checklist.

## Browser vs. Desktop & Zero-Disruption Automation:
  - Default for background automation of a logged-in browser is CDP because it avoids stealing focus, popping windows forward, or disturbing the user.
  - An explicit user request for `computer_use` is binding: use `computer_use` for the browser if it can see a live window; do not silently substitute CDP, browser tools, or OS keystrokes.
  - An explicit user request for `browser plugin` means browser tools only; do not silently substitute CDP or `computer_use`.
  - Do not use raw `SendKeys`/`SetForegroundWindow` as a substitute for `computer_use`, and do not raise a window unless explicitly requested.
  - If the requested surface returns an empty/0×0 capture, missing window, WAF page, or incomplete UI, preserve state and report the blocker. Do not claim the search or click succeeded and do not switch surfaces without authorization.
  - When CDP is the authorized surface, launch Chrome in the background with remote debugging: `chrome.exe --remote-debugging-port=9222 --user-data-dir="<profile_path>"` (always launched detached or via `background=True`) and verify the target/page before acting.
- **Launching GUI Apps from Terminal:** Never run interactive GUI apps (Chrome, Notepad) as foreground terminal commands — they hold the shell pipeline and freeze the agent session. Always launch detached or backgrounded.
