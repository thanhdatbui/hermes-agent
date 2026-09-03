---
name: coding-agent-troubleshooting
description: "Diagnose and fix common CLI failures for Codex and Claude Code — sandbox, PATH, auth, version conflicts."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [troubleshooting, codex, claude, sandbox, windows, debugging]
    related_skills: [codex, claude-code, hermes-orchestration-dispatcher]
---

# Coding Agent Troubleshooting

Quick-reference diagnostic patterns for Codex CLI and Claude Code failures.
Load this skill when any coding agent returns infrastructure errors (sandbox, PATH, auth, shell).

## First Step for Any Agent

```
<agent> doctor    # Always the first diagnostic command
<agent> --version # Confirm running version
```

## Codex CLI — Windows Process-Boundary Failures

### UTF-8 stdin on Windows

When an invoked CLI rejects a non-ASCII prompt with an error such as `input is not valid UTF-8`, treat it as a subprocess boundary bug before treating it as a provider/model failure. Python `subprocess.run(..., text=True, input=...)` should pass `encoding="utf-8"` explicitly when the child protocol is UTF-8; do not rely on the Windows locale code page. Add a regression fixture containing Vietnamese or another non-ASCII string, and assert the capture seam receives the explicit encoding.

### Structured output routing

Capture stdout, stderr, exit code, and any provider result file independently. Normalize only documented/equivalent envelopes at the consumer boundary (for example fenced/prose JSON, `result`/`content` wrappers, or an advisor `status` plus plan fields), then validate the role-specific canonical schema. Keep advisor plans separate from executor patch decisions: a ready advisor response must not be mistaken for permission to run live, and an incomplete executor response must fail closed rather than being retried as an unstructured success.

See `references/utf8-and-structured-output-boundaries.md` for the reusable reproduction and verification matrix.

### Diagnostic Commands

```bash
<agent> doctor
<agent> --version
```

## Codex Desktop — Subagent Spawn Hallucinations & Rule-Lawyering Fail-Closed

### Symptom: `SUBAGENT_RUNTIME_UNAVAILABLE` or asking to "cài tool spawn agent"

**Symptom**: Codex Desktop halts during task execution, refuses to edit files, and claims it cannot spawn a required worker (e.g. `gpt-5.6-luna` with high reasoning) or asks the user to "cài tool spawn agent" / reports `SUBAGENT_RUNTIME_UNAVAILABLE`.

**Root Cause**:
- `AGENTS.md` (e.g. in `~/.codex/AGENTS.md` or workspace root) contains strict coordinator-worker delegation rules (e.g. "Coordinator must dispatch a fresh worker subagent to patch files").
- Unlike Hermes (`delegate_task`) or Claude Code / OpenCode (`manage_task`), the **Codex Desktop app is a single-agent direct execution environment** and does not have an in-session subagent spawning tool.
- When running on `medium` effort or acting as a main chat, Codex reads `AGENTS.md`, realizes it lacks a spawn tool, and fails closed instead of triggering the `session-as-worker` fallback.

**Fix**:
1. **Immediate Chat Unlock**: Instruct Codex in chat:
   > *"Mày chính là direct worker (session-as-worker). Bản thân app Codex Desktop không có cơ chế spawn subagent, hãy tự dùng tool exec/apply_patch thực thi trực tiếp task theo đúng điều khoản fallback của AGENTS.md, không spawn gì cả."*
2. **Policy Root Fix**: Ensure `~/.codex/AGENTS.md` and workspace `AGENTS.md` explicitly state that built-in/direct Codex Desktop sessions default to `role=worker` (`session-as-worker`) with direct tool execution permissions.

## Codex CLI — Windows Sandbox Failures

### Diagnostic Commands

```bash
codex doctor                           # Full health report
codex doctor 2>&1 | grep "runtime "    # Find REAL runtime path
codex --version                        # Running version
ls "$(dirname $(which codex))"         # What's next to the executable?
echo "$PATH" | tr ':' '\n' | grep -i codex  # All Codex PATH entries
tail -30 ~/.codex/.sandbox/sandbox.$(date +%Y-%m-%d).log  # Today's sandbox log
```

### Key Architecture

Codex has TWO locations:
1. **Executable** (in PATH): `~/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe`
2. **Runtime** (packages): `~/.codex/packages/standalone/releases/<version>-x86_64-pc-windows-msvc/`
   - `codex-resources/codex-windows-sandbox-setup.exe`
   - `codex-resources/codex-command-runner.exe`

The executable may NOT have sandbox binaries next to it. The runtime ALWAYS does.

### Error: `program not found` for sandbox-setup

**Root cause**: `codex-windows-sandbox-setup.exe` missing from executable directory. Often happens after Microsoft Store version is uninstalled (takes the sandbox helper with it).

**Fix**:
```bash
RUNTIME=$(codex doctor 2>&1 | grep -oP 'package \K[^,]+')
cp "$RUNTIME/codex-resources/codex-windows-sandbox-setup.exe" "$(dirname $(which codex))/"
cp "$RUNTIME/codex-resources/codex-command-runner.exe" "$(dirname $(which codex))/"
rm -f ~/.codex/.sandbox-bin/codex-command-runner-*.exe  # clear stale cache
```

### Error: `unsupported protocol version 4`

**Root cause**: Sandbox binaries from a NEWER version (e.g. 0.146 alpha) paired with an OLDER codex.exe (e.g. 0.144). Protocol mismatch.

**Fix**: Copy sandbox binaries from the runtime matching the codex.exe version. See fix above — the `codex doctor` output tells you the correct runtime.

### Error: `CreateProcessAsUserW failed: 1920` or `CreateProcessWithLogonW failed: 2`

**Root cause**: Sandbox cannot access `WindowsApps\pwsh.exe` (error 1920) or cannot find `codex-command-runner.exe` (error 2).

**Root cause of 1920 (verified 2026-08-04)**: PATH resolves `pwsh.exe` to
`C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\pwsh.exe` — a **Microsoft Store
stub/symlink** (~300KB). Sandbox runs under a restricted token that cannot spawn
Store apps (`CreateProcessAsUserW`). This is NOT a codex/version issue and NOT
model-specific: it breaks `codex exec --sandbox ...` for EVERY model
(gpt-5.6-luna AND deepseek fallback) — a shell-only failure; plain text replies
still work.

**Fix for 1920** — create a pwsh wrapper from System32 PowerShell AND make it
resolve FIRST in PATH:
```bash
mkdir -p ~/.codex/shell
cp /c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe ~/.codex/shell/pwsh.exe
# verify it is actually the 5.1 binary (455KB) and NOT a symlink:
file ~/.codex/shell/pwsh.exe        # expect PE32+ executable, NOT a symlink
~/codex/shell/pwsh.exe -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
```
The critical step: PATH must prefer `~/.codex/shell` OVER WindowsApps, otherwise
codex still spawns the store stub and 1920 persists. Two options:
- Per-command (immediate, for tests/automation): `PATH="/c/Users/<user>/.codex/shell:$PATH" codex exec ...`
- Persistent: prepend `~/.codex/shell` to the **User** PATH (a User PATH entry
  beats the machine-wide WindowsApps entry), or set User PATH entry ordering so
  `~/.codex/shell` comes first.

**Verify the fix** — sandbox log should show the wrapper, not the store stub:
```bash
grep "START:" ~/.codex/.sandbox/sandbox.$(date +%Y-%m-%d).log
# GOOD:  START: C:\Users\...\.codex\shell\pwsh.exe
# BAD:   START: C:\Users\...\WindowsApps\pwsh.exe
```
A quick probe: `PATH="/c/Users/<user>/.codex/shell:$PATH" codex exec -m <model> --sandbox workspace-write "run shell: echo OK"` — should print `OK` with no 1920.

**⚠️ Side-effect of the 1920 fix — PS7/PS5.1 trap (verified 2026-08-04):**
Prepending `~/.codex/shell` to PATH makes **every** `pwsh` lookup resolve to the
PS5.1 copy, silently breaking any script with `#requires -Version 7.0`
(the Command Code audit wrapper, Claude-related PS7 tooling). Consequences:
- `pwsh -File wrapper.ps1` now fails with `ScriptRequiresUnmatchedPSVersion`
  even though a PS7 install exists.
- `powershell.exe` is ALWAYS Windows PowerShell 5.1 — never use it to invoke a
  `#requires -Version 7.0` script.
**Fix**: for PS7-requiring wrappers, call the store PS7 by absolute path
(`C:\Program Files\WindowsApps\Microsoft.PowerShell_<ver>_x64__8wekyb3d8bbwe\pwsh.exe`,
discoverable via `where pwsh` / `ls` on the WindowsApps symlink), falling back
to bare `pwsh` only when the absolute path does not exist. Do not rely on
`pwsh` in PATH after the 1920 fix.

**Fix for error 2** — copy the correct command-runner. See "program not found" fix above.

### Error: `codex update` fails with tar error

```
tar (child): Cannot connect to C: resolve failed
```

**Root cause**: Git Bash `tar` is before Windows `tar` in PATH. PowerShell inherits the MSYS PATH and `tar` interprets `C:` as a network host.

**Fix** — clean PATH before update:
```bash
PATH="/c/Windows/System32:/c/Windows/System32/WindowsPowerShell/v1.0:/c/Windows:$(dirname $(which codex))" \
  codex update
```

### Multiple Installations After Auto-Update

Check with `codex doctor` → `PATH entries`. Common locations:
- `~/AppData/Local/Programs/OpenAI/Codex/bin/` — user PATH (may be stale)
- `~/AppData/Local/OpenAI/Codex/bin/<hash>/` — auto-update target
- `C:/Program Files/WindowsApps/OpenAI.Codex_*/` — Store version (may be uninstalled)

Remove stale PATH entries via Windows System Properties → Environment Variables.

### Sandbox Log Analysis

Sandbox logs at `~/.codex/.sandbox/sandbox.YYYY-MM-DD.log`. Key patterns:
- `spawning codex-windows-sandbox-setup.exe` WITHOUT full path → **will likely fail** if not next to executable
- `spawning C:\...\69066b736e1e17a4\codex-windows-sandbox-setup.exe` WITH full path → found via runtime
- `setup binary completed` → sandbox initialized successfully
- `CreateProcessAsUserW failed: 1920` → can't access WindowsApps pwsh
- `helper copy: recopied command-runner` → cache was stale, auto-fixed
- `START: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` → using legacy PowerShell (works)
- `START: C:\Users\...\WindowsApps\pwsh.exe` → using Store PowerShell (may fail)

### MCP node_repl vs exec

`codex exec` (pwsh commands) requires working sandbox. MCP `node_repl` (file read/write via Node.js) uses a separate runtime and often works even when exec is broken. If `codex exec "echo test"` fails but codex can still read/write files, the issue is sandbox-specific, not a complete outage.

### Error: `Invalid schema for response_format ... 'oneOf' is not permitted`

Xảy ra khi `codex exec --output-schema <schema.json>` với schema JSON chứa
`oneOf` (vd `"evidence": {"oneOf": [{"type":"object"},{"type":"array"}]}`).
9Router/commandcode upstream trả `invalid_request_error` ngay lúc gửi request —
Codex chết trước khi sinh được bất kỳ output nào, `repair-output.txt` chỉ còn
2 dòng ERROR + prompt. Verify 2026-08-08 (auto-recovery ladder slot-5/6).

**Fix**: bỏ `oneOf` khỏi schema truyền qua `--output-schema`. Dùng property
rỗng `"evidence": {}` (no constraint) hoặc `"type": ["object","array"]` —
chỉ cần không dùng `oneOf`. `required`/`additionalProperties: false` vẫn OK.
Schema này dùng cho cả Codex lẫn Hermes CLI fallback nên sửa 1 chỗ cứu cả 2.

### Codex Quota Exhaustion → 9Router DeepSeek Fallback

When Codex's GPT models (gpt-5.6-luna/terra/sol) hit quota/usage limits, the CLI can fall back to a local OpenAI-compatible router WITHOUT a second agent instance. Verified on this machine:

- `~/.codex/config.toml` already defines `[model_providers.9router]`: `base_url = "http://localhost:20128/v1"`, `wire_api = "responses"`, `env_key = "NINEROUTER_API_KEY"`.
- 9Router serves `deepseek-v4-flash` over `/v1/responses` — exactly the wire format Codex CLI requires.
- A `config.pre-deepseek-*.toml` backup proves this machine previously ran Codex through provider `omni` (same 9Router endpoint).

**Smoke test before relying on the route:**
```bash
curl -s http://127.0.0.1:20128/v1/models -H "Authorization: Bearer $NINEROUTER_API_KEY"
curl -s http://127.0.0.1:20128/v1/responses -H "Authorization: Bearer $NINEROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","input":"reply exactly: OK","max_output_tokens":20}'
```
A `resp_...` id with `status: in_progress` confirms the responses wire works.

**Fallback invocation:**
```bash
codex exec -c 'model_provider="9router"' -m deepseek-v4-flash --sandbox read-only "<task>"
# write role only if tool-calling is verified:
codex exec -c 'model_provider="9router"' -m deepseek-v4-flash --sandbox workspace-write "<task>"
```

**Cleaner: named profile via `-p` (verified 2026-08-07)** — instead of repeating
`-c` overrides, drop a layer file `~/.codex/<name>.config.toml` (Codex layers it on
top of the base config; select with `codex exec -p <name> ...`). Never touches the
base `config.toml` the desktop app reads:
```toml
# ~/.codex/deepseek-test.config.toml
model = "deepseek-v4-flash"
model_provider = "9router"
model_reasoning_effort = "high"
```
`codex exec -p deepseek-test --sandbox read-only "..."` → exit 0, model replies, and
the run header prints `model: deepseek-v4-flash / provider: 9router`. Any 9router
combo id works (DB `combos` table: `deepseek-v4-flash` → `["cmc/deepseek/deepseek-v4-flash"]`,
served on `/v1/responses`, the wire Codex requires).

**Codex has NO native model fallback** — the official config reference
(`developers.openai.com/codex/config-reference`) has no `model_fallback` /
`fallback_models` key; every "fallback" hit is MCP OAuth or
`project_doc_fallback_filenames`. Closest is `notice.hide_rate_limit_model_nudge`
(app *suggests* switching models, never auto-switches). Quota fallback must live at
the orchestration level (profile / `-c` route), never in config.

**Desktop-app default — CORRECTED recipe (2026-08-07, supersedes earlier notes):**
The desktop app (MSIX `OpenAI.Codex_*`) reads the base `~/.codex/config.toml`,
BUT editing it does NOT make custom models appear in the dropdown, and it DOES
silently switch the default for ALL new chats. Verified this session:
- The dropdown is hardcoded from the OpenAI account via the `list-models-for-host`
  RPC — local files (`models_cache.json`, `cockpit-local-access-model-catalog.json`,
  provider `models = [...]` in config) do NOT drive it, and the app rewrites them
  on start.
- The desktop host (app-server `codex.exe`) connects ONLY to `api.openai.com:443`
  — with `model_provider = "omni"` it does NOT connect to 9router (no request logs
  in `%APPDATA%/9router/`), even though the session rollout JSONL records
  `"model":"deepseek-v4-flash"`. Rollout says what config WAS, not where the bytes
  went.
- **User correction (hard):** "mày setting như v nó tự động thành deepseek v4 kể cả
  t có dùng model gpt 5.6 sol" → user picked GPT in the dropdown but the base
  `model =` override silently redirected. They demanded a full revert.
**Rules:**
1. NEVER change base `model =` in `config.toml` just to "add a model" — ask scope
   first (CLI vs desktop; default vs available). For CLI-only custom-provider
   routing use a `~/.codex/<name>.config.toml` layer + `-p` (never touches the app).
2. To verify which model ACTUALLY ran, check the session rollout:
   `ls -t ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl | head -1 | xargs grep -oE '"model":"[^"]*"' | sort -u`
   and cross-check with `netstat -ano | grep <codex-host-pid>` — if the host only
   talks to api.openai.com:443 and never to the custom base_url, the custom
   provider is NOT in the request path.
3. Always backup before editing: `cp config.toml config.toml.bak-$(date +%Y%m%d-%H%M%S)`.
4. Revert = restore backup + delete the deepseek line from `[tui.model_availability_nux]`
   + restart the app. Verify with the ad-hoc pattern below.

**⚠️ `codex/` prefix → misleading 401 (verified):** with a custom provider active,
Codex sends OpenAI-registry model ids with a `codex/` prefix. `model="gpt-5.6-luna"`
+ `model_provider="omni"` → request id `codex/gpt-5.6-luna` → 9router replies
`401 Your authentication token has been invalidated` (upstream doesn't know that id;
NOT an auth problem). Non-OpenAI ids (`deepseek-v4-flash`, `cmc/*`, `oc/*`) have no
prefix and work fine. **Consequence: switching the app provider to omni/9router
breaks the gpt-5.6-luna default** — if you need both, keep `model_provider="openai"`
and use the profile/`-c` fallback route instead. Picker visibility is governed by
`[tui.model_availability_nux]` (a NUX "seen" marker, NOT a model registry).

**Workflow lesson (user correction 2026-08-07):** "cấu hình app codex thêm model" =
base config, NOT a CLI profile. Do not build `~/.codex/<name>.config.toml` when the
user asks for the app — that only works for CLI `-p` invocations and the app ignores
it. Verify the app path by running `codex exec` with NO `-p`/`-c` overrides (that is
exactly what the app reads).

**Benign warnings (do not chase):**
- `Model metadata for 'deepseek-v4-flash' not found. Defaulting to fallback metadata` — run still works.
- `codex_models_manager ... failed to refresh available models: missing field 'models'` — 9router `/v1/models` returns OpenAI list shape `{"object":"list","data":[...]}` while Codex expects `{"models":[...]}`; refresh error is cosmetic, exec runs fine.

**Verified 2026-08-04 (this machine):**
- `codex exec -c 'model_provider="9router"' -m deepseek-v4-flash` text reply: ✅ works (`DEEPSEEK_OK`)
- `-m deepseek-v4-pro` text reply: ✅ works (`PRO_OK`)
- Tool calling (shell exec, file read): ✅ works — deepseek self-invokes `pwsh -Command ...` and reads files correctly
- ⚠️ BUT sandboxed exec fails with error 1920 unless `~/.codex/shell` precedes WindowsApps in PATH (see 1920 fix above). With the PATH fix, `--sandbox workspace-write` + file read works for deepseek-v4-flash.
- 9Router serves `deepseek-v4-flash`, `deepseek-v4-pro`, `deepseek-v4-pro-max` (combo) and `cmc/deepseek/deepseek-v4-flash`, `cmc/deepseek/deepseek-v4-pro` — all `capabilities.tools=true`, `reasoning=true`, context 1M, maxOutput 384K.

**Pitfalls:**
- When the CLI reports stale OAuth/plugin credentials, do NOT start ChatGPT OAuth login — force the 9Router provider instead (`-c 'model_provider="9router"'`).
- A fallback model must NOT blindly repeat the prior model's failed command/patch (Taadaa rule: escalation/fallback requires a materially different hypothesis).
- Not every 9Router-served model is equivalent: test tool-calling/write behavior of `deepseek-v4-flash` before granting it write/live roles; read-only advisor/audit fallback is the safe default.
- `Model metadata for 'deepseek-v4-flash' not found. Defaulting to fallback metadata` is a benign warning — the run still works.
- **9Router deepseek reasoning levels (user-verified 2026-08-04 via live
  `/v1/chat/completions` on both `deepseek-v4-flash` and `deepseek-v4-pro`):
  `auto`, `low`, `medium`, `high`, `max`, `thinking` all PASS.** Pass
  `reasoning_effort` as a SEPARATE request field — do NOT append a suffix to
  the model ID (e.g. `-max` is wrong; `cmc/deepseek/deepseek-v4-flash` +
  `"reasoning_effort":"max"` is right). The model tier (`flash → pro →
  pro-max`) is a second, orthogonal knob. `providerThinking.commandcode.mode`
  is the provider default used only when no explicit effort is supplied.

Taadaa `invoke-opencode-audit.ps1` wrapper (model allowlist, failure error strings, OpenCode free-model catalog renames, UTF-16LE JSONL gotcha, verify recipe): `references/taadaa-opencode-audit-wrapper.md`.
Taadaa auto-recovery architecture + exact fallback insertion point: `references/taadaa-auto-recovery-codex-routing.md`.
Full error-1920 PATH-vs-store-stub diagnostic (which/order/file/symlink checks + verified fix): `references/windows-sandbox-error-1920-path-stub.md`.
9Router dashboard auth (bcrypt password in DB — not derivable from cli/jwt/machine-id), read-only DB schema map, and deepseek reasoning levels: `references/9router-dashboard-auth-db-reasoning.md`.
PowerShell 7 wrapper crashes (the `-or`-binds-as-one-arg trap, empty-string Mandatory param, PS7-absolute-path rule) + artifact-path gotchas: `references/powershell7-wrapper-pitfalls.md`.
Full Codex-app-default-on-9router recipe (evidence chain, `codex/`-prefix 401 trap, benign `/v1/models` noise, ad-hoc verify pattern): `references/codex-app-9router-default-model.md`.
Pytest cache contention (Errno 13), foreground timeout accumulation & anti-hang pattern: `references/pytest-cache-and-timeout-anti-hang-pattern.md`.

## Claude Code — Common Failures

### Claude Pro account — billing & model availability (verified 2026-08-14)

- **Account type check:** `claude auth status --json` → `authMethod: "claude.ai"` (firstParty OAuth, NOT "API account" despite `--text` saying "Claude API account" — the text label is misleading). Real plan lives in `~/.claude.json` → `oauthAccount.organizationType` (`claude_pro`) + `billingType` (`stripe_subscription`); `.credentials.json` keys = `['claudeAiOauth']`.
- **Pro = quota-based, NOT per-request billing.** `total_cost_usd` / `modelUsage[].costUSD` in `claude -p --output-format json` is an **API-price ESTIMATE for relative comparison only — nothing is charged to a Pro account**. The real limit is the Pro 5h rolling usage window (`organizationRateLimitTier: default_claude_ai`); exceed it → rate-limit until reset. `hasExtraUsageEnabled:false` = no overage. Do NOT tell a Pro user "each call costs $X" as if money is deducted — user (correctly) pushed back: *"0.05$ 1 lần là sao, tính giá quota mỗi reset à, acc claude của t là acc pro tính theo quota pro"*.
- **Model availability on this Pro account (smoke-tested):** `claude-sonnet-5` ✓ (works with `--model claude-sonnet-5 --effort high`), `claude-sonnet-4-6` ✓, `claude-sonnet-4-5` ✓, `claude-sonnet-4-8` ✗ (404 — does not exist). Relative API-estimate cost (same prompt): sonnet-5 ≈ $0.214 vs sonnet-4-6 ≈ $0.162 → **sonnet-5 ~32% pricier**.
- **Hermes cannot run sonnet-5 as a session model** (no `ANTHROPIC_API_KEY` in env; 9router has only `ag/claude-sonnet-4-6` + `ag/claude-opus-4-6-thinking`; `v98/claude-sonnet-5` dead 503 `service_migrated`). Only path = Claude CLI subagent: `claude -p "<task>" --model claude-sonnet-5 --effort high --max-turns 10`.

### Permission Prompts Blocking Automation

`claude -p` (print mode) skips all interactive dialogs — use it for automation. If using interactive mode with `--dangerously-skip-permissions`, the permissions dialog defaults to "No, exit". Must send Down then Enter:

```bash
tmux send-keys -t <session> Down && sleep 0.3 && tmux send-keys -t <session> Enter
```

### Tool Call Denied (Permission Mode)

If Claude says "tool call denied", check permission mode:
```bash
claude -p "task" --permission-mode bypassPermissions
# or
claude -p "task" --dangerously-skip-permissions
```

## Dispatch Fallback Pattern

When the primary coding agent is blocked by infrastructure issues (sandbox, auth, PATH):

1. **Codex blocked** → try `codex doctor` and apply fixes above
2. **Codex still blocked** → dispatch to Claude: `claude -p --dangerously-skip-permissions "<task>"`
3. **Both blocked** → report to user with diagnostic output from both `doctor` commands

This pattern is especially relevant for `hermes-orchestration-dispatcher` workflows where Codex is the primary implementer and Claude is the reviewer.
