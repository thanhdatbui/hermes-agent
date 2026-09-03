# Admin Telegram Gateway: layer checklist

Use this reference when an existing Windows Admin has Hermes installed and the goal is a Telegram bot, not the Desktop app.

## Gates

1. **Telegram credentials**: token entered locally via `hermes gateway setup`; allowed user ID set; home channel confirmed. Never paste or print token.
2. **Gateway transport**: `hermes gateway status`; log must show Telegram connected, `set_my_commands OK`, and gateway running.
3. **Provider resolution**: `model.provider` must resolve to a configured named provider. For an OpenAI-compatible 9Router endpoint, use the current keyed schema:
   ```yaml
   providers:
     9router:
       api: http://<kibe-ip>:20128/v1
       key_env: NINEROUTER_API_KEY
       transport: chat_completions
       default_model: gpt-5.6-luna
   model:
     provider: custom:9router
     default: gpt-5.6-luna
   ```
   Apply with `hermes config set`, then `hermes config check`; do not hand-edit unless the CLI cannot represent the value.
4. **Native Image Routing (Direct Pixels)**:
   Set `hermes config set agent.image_input_mode native` and delete `auxiliary.vision` block to ensure vision models (Gemini 3.7 / GPT-5.6-luna) inspect image payloads directly from 9Router without tripping 401/403 auth errors via `vision_analyze`.
5. **Recurring Skill Sync Cron**:
   - `hermes cron create "every 30m" --name "sync-hermes-skills-to-git" --no-agent --script "sync-skills-to-repo.ps1"`
   - Note: Schedule must be `"every 30m"` for recurring runs. Script must reside inside `C:\Users\<User>\AppData\Local\hermes\scripts\`.
6. **Round trip**: `/start` may be ignored as a platform ping. Verify with `/model` or a normal `ping`, and require a real assistant response before declaring success.

## Interaction & Telegram UX rule

1. **Prompt Reading**: Read the exact current wizard prompt from the user screenshot before replying. If the user asks to have the installed Hermes app configure itself, give one bounded self-contained instruction rather than repeatedly relaying one prompt at a time. Once a concrete error appears, stop repeating setup and address that error directly.
2. **One-Touch Copy Formatting**: In Telegram replies, always wrap commands or sample prompts in dedicated, standalone fenced code blocks (` ```text `). Do not mix explanation prose inside the block so mobile Telegram clients display the 1-tap "Copy" button clearly.

## Diagnosing a silent / unresponsive bot (Remote & Host Ladder)

When the remote Telegram bot suddenly stops replying to messages (`alo?`, prompts ignored):

1. **Remote Probe (from Primary PC)**:
   - Ping target PC over Tailscale/LAN (`ping 100.120.89.125`) to verify network liveness.
   - Verify shared LLM proxies on Primary PC (9Router `:20128` / OmniRoute `:20129`) are listening and healthy.
2. **In-Chat Recovery (Telegram)**:
   - Try `/stop` in the target topic/chat to cancel an ongoing hung tool iteration or long API wait.
   - Try `/new` to clear the current session context if state was corrupted or deadlocked.
3. **Host Diagnostics (Admin PowerShell)**:
   - Check process state: `hermes gateway status`.
   - Inspect recent log: `Get-Content "$env:LOCALAPPDATA\hermes\logs\gateway.log" -Tail 60`.
   - Look for:
     - **Context bloat / SQLite FTS corruption crash**: `Persisted transcript lagged live cached history ... (disk=718, memory=719); preserving live conversation context (possible FTS write corruption)`. Occurs when sessions exceed 700+ messages and concurrent turns hit DB/memory limits. Fix: start gateway + `/new` to prune the active topic context.
     - **Process exit / Uncaught error**: If status shows `No gateway process detected`.
4. **Hard Recovery**:
   - Graceful restart: `hermes gateway restart`.
   - Stuck process kill & start: `taskkill /F /IM pythonw.exe` then `hermes gateway start`.

## 24/7 Gateway Watchdog & Auto-Heal (Windows Scheduled Task)

`hermes gateway install` on Windows ONLY registers an `AtLogOn` task (starts once when user logs in). If the Gateway process crashes mid-day from OOM/DB lock/network drop, Windows will NOT revive it automatically.

Deploy a persistent 2-minute recurring watchdog task on the Admin machine:

```powershell
$scriptDir = "$env:LOCALAPPDATA\hermes\scripts"
if (-not (Test-Path $scriptDir)) { New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null }
$watchdogScript = "$scriptDir\watchdog-gateway.ps1"

$content = @'
$hermesExe = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\hermes.exe"
$gw = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' or Name = 'python.exe'" | Where-Object { $_.CommandLine -match "hermes_cli\.main\s+(gateway\s+run|serve)" }
if (-not $gw) {
    Start-Process -FilePath $hermesExe -ArgumentList @("gateway", "start") -WindowStyle Hidden
}
'@
Set-Content -Path $watchdogScript -Value $content -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"`"$watchdogScript`"`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "Hermes_Gateway_Watchdog" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
```
