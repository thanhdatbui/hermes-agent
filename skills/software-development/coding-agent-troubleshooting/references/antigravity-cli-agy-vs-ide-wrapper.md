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

### 2. Missing `agy` Binary on Windows Host
- **Check**: Run `which agy` or `where agy`.
- If missing, Antigravity CLI has not been installed on the host. Do NOT try to substitute `antigravity-ide.cmd` or local cockpit files.
- **Install**: Install the official `agy` package from Google (`https://antigravity.google/docs/cli/install`), then execute `agy login` to bind Google Cloud Code credentials.

### 3. Headless Worker Invocation Pattern
Once `agy` is installed, invoke it as an external CLI worker with:
```bash
agy -p "<prompt>" --model "Gemini 3.6 Flash (Low)" --dangerously-skip-permissions
```
- Multi-turn continuation: `agy -c -p "<follow-up prompt>"`
- Set timeout on caller: Always pass `timeout=...` in subprocess/terminal runner.
