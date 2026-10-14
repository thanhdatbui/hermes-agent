# Antigravity CLI (`agy`) vs Antigravity IDE GUI Launcher

## Diagnostic Summary

When integrating Google's Antigravity as an autonomous worker, subagent, or fallback CLI alongside Claude Code, Codex, and OpenCode, agents frequently confuse the desktop IDE launcher with the standalone headless CLI tool.

| Attribute | Antigravity IDE Launcher | Antigravity CLI (`agy`) |
| :--- | :--- | :--- |
| **Binary path** | `...\Antigravity IDE\bin\antigravity-ide.cmd` | `agy` (or `agy.cmd` / `agy.exe` on PATH) |
| **Origin** | Antigravity Desktop IDE (VS Code fork) | Google Antigravity CLI (`curl -fsSL https://antigravity.google/cli/install.sh \| bash`) |
| **Execution mode** | GUI-first IPC dispatch | Headless non-interactive CLI |
| **Return behavior** | Exits 0 immediately after sending IPC to IDE window | Runs synchronously, prints agent thoughts/actions/output to stdout |
| **Headless flag** | None (`chat` mode still requires active GUI session) | `-p "<prompt>"` / `--print` |
| **Automation flags** | Limited | `--dangerously-skip-permissions`, `--model <id>`, `-c` (continue) |
| **Usable as Subagent Worker?** | ❌ NO (Cannot capture output or diffs programmatically) | ✅ YES (Seamless subprocess execution like `claude -p` or `codex exec`) |

## Common Traps & Pitfalls

### 1. The False-Positive Bridge Trap (`antigravity-ide.cmd chat`)
- **Symptom**: Agent creates a wrapper script calling `antigravity-ide.cmd chat -m agent "<prompt>"`, sees exit code 0, and reports "Connected 100% and verified".
- **Reality**: The command only opens or focuses a chat tab in the desktop IDE application window. It does NOT wait for the model to finish, does NOT capture code modifications, and returns zero output to stdout/stderr. Any orchestrator calling this will blindly stall or hallucinate success.

### 2. Missing `agy` Binary on Windows Host & Direct Windows Download
- **Check**: Run `which agy` or `where agy`.
- If missing, Antigravity CLI has not been installed on the host. Do NOT try to substitute `antigravity-ide.cmd` or local cockpit files.
- **Windows Install Recipe (No npm/curl needed)**:
  Query Google's official release manifest:
  `https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/windows_amd64.json`
  Download `cli_windows_x64.exe` (e.g. from `https://storage.googleapis.com/antigravity-public/antigravity-cli/.../windows-x64/cli_windows_x64.exe`), verify SHA512, and save as `agy.exe` inside a directory on user PATH (e.g. `C:\Users\<user>\AppData\Local\Programs\Antigravity IDE\bin\agy.exe`).
- **Auth**: If Antigravity IDE or Google Cloud Code is already authenticated on the machine, `agy` inherits credentials automatically without needing manual `agy login`.

### 3. Headless Worker Invocation Pattern & Flag-Ordering Trap
⚠️ **CRITICAL FLAG-ORDERING TRAP**: In `agy` CLI, `-p` consumes the immediately following token as the prompt string. If you write `agy -p "<prompt>" --dangerously-skip-permissions`, `agy` errors with:
`Error: -p took "--dangerously-skip-permissions" as its prompt, so the intended prompt was left as an argument and ignored.`

**Correct Flag Ordering**:
Flags (`--dangerously-skip-permissions`, `--model`, `--add-dir`) MUST be passed BEFORE `-p`:
```bash
agy --dangerously-skip-permissions --model "gemini-3.8-flash-high" -p "<task>"
```
- Multi-turn continuation: `agy --dangerously-skip-permissions -c -p "<follow-up prompt>"`
- Target file context: Pass `--add-dir <directory_of_file>` so `agy` can edit workspace files.
- Verified Bridge Script: See `D:/Taadaa/tools/ag_cli.py`:
  * `python D:/Taadaa/tools/ag_cli.py ask "<prompt>"` (read-only / analysis)
  * `python D:/Taadaa/tools/ag_cli.py fix "<prompt>" --file <file>` (modifications)
  * `python D:/Taadaa/tools/ag_cli.py models` (available models: `gemini-3.8-flash-high`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`)

### 4. Quota & Auth Source Architecture (`~/.gemini/`)
- **Credentials Location**: On Windows, `agy.exe` stores its active OAuth session in `%USERPROFILE%\.gemini\`:
  * `~/.gemini/google_accounts.json`: Tracks `active` email vs `old` list (e.g. `{"active": "user@gmail.com", "old": [...]}`).
  * `~/.gemini/oauth_creds.json`: Contains active Google OAuth `access_token`, `refresh_token`, and JWT `id_token`.
  * `~/.gemini/projects.json`: Maps directory paths to Google Cloud Code project IDs (e.g. `"d:\\taadaa": "taadaa"`).
- **Quota Separation**: `agy` CLI consumes the personal Google One AI / Gemini Advanced quota of the active account in `~/.gemini/google_accounts.json`. It is completely decoupled from OmniRoute (`:20129`), Cockpit, or multi-account farm pools.
- **Quick Account Inspection**:
  ```bash
  python -c "import json; print(json.load(open(r'C:\Users\Kibe\.gemini\google_accounts.json'))['active'])"
  ```

### 5. Cockpit Tools vs agy CLI Quota Isolation
- **Codex CLI vs agy CLI in Cockpit**: Cockpit Tools (`cockpit-cliproxy.exe` port `60818`) performs automated token-takeover and pool rotation for Codex CLI via `~/.codex/auth.json`. However, it does NOT hook or proxy `agy.exe`.
- **Instance Separation**: Cockpit Tools manages Antigravity desktop IDE profiles via `instances.json` and `current_account.json` (e.g. `thanhdatbui19951@gmail.com`). Switching accounts inside Cockpit Tools GUI does NOT change the account used by `agy.exe`.
- **Decoupled Quotas**: `agy.exe` directly reads `~/.gemini/oauth_creds.json` (e.g. `jinrakal@gmail.com`). To change the account used by `agy.exe`, run `agy login` from terminal, or route through OmniRoute (`:20129`) if pool rotation across multiple accounts is needed.
