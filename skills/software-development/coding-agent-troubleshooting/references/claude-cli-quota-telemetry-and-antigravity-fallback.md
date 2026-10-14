# Claude CLI Quota Telemetry & Fail-Safe Fallback to Antigravity CLI

## 1. Problem: Blindness in Claude Code CLI Usage
Unlike API tokens where balance is numerically trackable via balance endpoint, Claude Pro OAuth CLI sessions (`claude -p`) provide **zero remaining quota percentage** in `claude auth status` or `claude auth status --json`.

Instead, Claude Pro uses an internal dynamic **5-hour sliding window** and **7-day account quota**.

## 2. Ground-Truth Data Source
The desktop client for Claude (`Claude Desktop` UWP app) syncs telemetry directly from Anthropic servers to disk at:
```text
C:\Users\Kibe\AppData\Roaming\Claude\plan-usage-history.json
```
JSON Schema:
```json
{
  "version": 2,
  "samples": [
    {
      "t": 1791923514000,
      "org": "38fbe0ed-4221-4889-a443-d5a00afefb9f",
      "u": {
        "fh": 4,   // Five Hours usage percentage (85% hard gate threshold)
        "sd": 45   // Seven Days usage percentage (90% hard gate threshold)
      }
    }
  ]
}
```

## 3. Background Sync Automation
On Windows, placing an auto-launch script in the User Startup directory ensures Claude Desktop runs in the background upon login/reboot:
- **Script Path**: `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_claude_desktop.vbs`
- **Execution Target**: `shell:appsFolder\Claude_pzs8sxrjxfjjc!App`

## 4. Fail-Safe Worker Implementation (`haiku_worker.py`)
To prevent session lockout (HTTP 429), the CLI wrapper enforces:
1. **Pre-flight Quota Check**: Read `plan-usage-history.json`. If `fh >= 85%` or `sd >= 90%` or data is older than `MAX_QUOTA_STALE_HOURS` (24h), trigger automatic circuit breaker.
2. **Post-execution Limit Detection**: If output or stderr contains rate limit signatures (`hit your session limit`, `resets at...`) with non-zero exit code:
3. **Automatic Fallback to Antigravity Pool**:
   Redirect task immediately to:
   ```bash
   python D:/Taadaa/tools/ag_cli.py fix "<prompt>" [--file <file>] [--workdir <workdir>]
   ```
   This invokes the pool of 7 Google Pro accounts over dedicated 4G mobile proxies with zero extra cost and zero downtime.
