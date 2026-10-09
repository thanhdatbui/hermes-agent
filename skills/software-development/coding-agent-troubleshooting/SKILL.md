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

For the verified OmniRoute pool-routing, Windows sandbox workaround, background confirmation hang, and obsolete `.codex/agents/*.toml` field cleanup procedure, see `references/codex-cli-omniroute-routing-and-confirmation-hang.md`. Always distinguish a provider/quota failure from a CLI routing failure by checking the effective `provider:` line in Codex output; do not report pool exhaustion until an OmniRoute-routed smoke request has failed.

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

### Error: `You've hit your usage limit` (Codex CLI Defaults to Single OpenAI OAuth Instead of OmniRoute Pool)

**Symptom**: Calling `codex exec -m gpt-5.6-terra` (hoặc `gpt-5.6-luna`, `gpt-5.6-sol`) lập tức báo lỗi:
```
ERROR: You've hit your usage limit. To continue using Codex and get access to GPT-5.3-Codex, start a free trial of Plus today (https://chatgpt.com/explore/plus), or try again at ...
```
dù pool tài khoản Codex/OmniRoute (:20129) vẫn còn đầy hạn ngạch.

**Root cause**:
`~/.codex/config.toml` có `model_provider = "openai"`. Khi chạy `codex exec` mà không truyền tường minh `-c 'model_provider="omni"'`, Codex CLI tự động dùng token cá nhân trong `~/.codex/auth.json` (chế độ ChatGPT OAuth), hoàn toàn không kết nối tới pool tài khoản đa user của OmniRoute.

**Fix**:
1. Cấu hình mặc định vĩnh viễn trong `~/.codex/config.toml`:
   ```toml
   model_provider = "omni"
   ```
2. Nếu gọi qua lệnh CLI/script, luôn kèm cờ provider để fail-safe:
   ```bash
   codex exec -c 'model_provider="omni"' -m gpt-5.6-terra ...
   ```
3. Khắc phục cảnh báo `warning: Ignoring malformed agent role definition: ... unknown field role`:
   Trên Codex CLI 0.145.0+, schema của agent role file trong `.codex/agents/*.toml` đã bỏ trường `role`. Bỏ dòng `role = "..."` trong các file `.toml` này để xóa sạch cảnh báo deserialization.

### Background Codex Interactive Hang & False "Sleep" Trap

**Symptom**: Tiến trình khởi chạy với `terminal(command="codex exec ...", background=True, notify_on_complete=True)` bị treo hàng giờ (uptime > 7000s) mà không kết thúc. Coordinator tưởng tiến trình đang chạy ngầm bình thường nên im lặng chờ đợi, khiến User tưởng agent bị treo / bỏ cuộc ("sao nó dừng mày đéo báo, dừng theo à?").

**Root cause**:
- `codex exec` nếu không có chỉ thị dứt khoát trong prompt sẽ dừng lại ở cuối turn để hỏi xác nhận người dùng:
  `"Xác nhận cho phép tôi bắt đầu sửa và tái xuất đúng các tệp trong phạm vi đã nêu chứ?"`
- Do tiến trình bị chặn chờ `stdin` và không bao giờ thoát, cơ chế `notify_on_complete` **HOÀN TOÀN KHÔNG BAO GIỜ KÍCH HOẠT**.
- Coordinator không poll sớm mà đi ngủ theo tiến trình ngầm, dẫn đến bế tắc kéo dài.

**Fix**:
1. **Chỉ thị không tương tác trong Prompt**: Luôn chèn câu ủy quyền rõ ràng ở đầu prompt:
   `"ĐÃ ĐƯỢC ỦY QUYỀN RÕ RÀNG: thực thi sửa trực tiếp ngay lập tức, tuyệt đối không dừng lại hỏi xác nhận."`
2. **Quyền Sandbox phù hợp trên Windows**: Luôn dùng `-s danger-full-access` (hoặc `--dangerously-bypass-approvals-and-sandbox`) trong các lệnh headless/background tự động, tránh việc sandbox `read-only` của Windows văng lỗi `filename or extension is too long` hoặc lỗi 1920.
3. **Chủ động thăm dò (Proactive Polling)**: Sau khi ném vào background, Coordinator BẮT BUỘC gọi `process(action='poll')` trong 15–30s đầu tiên để kiểm tra output xem tiến trình có đang bị kẹt ở câu hỏi chờ xác nhận hay không, thay vì phó mặc hoàn toàn cho `notify_on_complete`.

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
Coordinator deadlock breakthrough via external autonomous CLI (bypassing in-session subagent dispatch limits, background execution & prompt keyword defense): `references/coordinator-deadlock-cli-breakthrough.md`.
Lỗi rách turn Gemini HTTP 400 (`Invalid function call turn sequence`), vòng lặp treo stream chunks và quy trình cứu hộ context dở dang qua session_search: xem skill `hermes-session-tuning` (`references/gemini-turn-sequence-corruption-and-session-recovery.md`).
Taadaa auto-recovery architecture + exact fallback insertion point: `references/taadaa-auto-recovery-codex-routing.md`.
Full error-1920 PATH-vs-store-stub diagnostic (which/order/file/symlink checks + verified fix): `references/windows-sandbox-error-1920-path-stub.md`.
9Router dashboard auth (bcrypt password in DB — not derivable from cli/jwt/machine-id), read-only DB schema map, and deepseek reasoning levels: `references/9router-dashboard-auth-db-reasoning.md`.
PowerShell 7 wrapper crashes (the `-or`-binds-as-one-arg trap, empty-string Mandatory param, PS7-absolute-path rule) + artifact-path gotchas: `references/powershell7-wrapper-pitfalls.md`.
Full Codex-app-default-on-9router recipe (evidence chain, `codex/`-prefix 401 trap, benign `/v1/models` noise, ad-hoc verify pattern): `references/codex-app-9router-default-model.md`.
Codex CLI on OmniRoute (:20129) & 9Router (:20128) GPT Sol routing (wire_api="responses", profiles, chatgpt-web tier vs combo): `references/codex-omniroute-sol-routing.md`.
Pytest cache contention (Errno 13), foreground timeout accumulation & anti-hang pattern: `references/pytest-cache-and-timeout-anti-hang-pattern.md`.
Claude CLI quota exhaustion, worker subagent delegation & Windows directory junction fallback: `references/claude-cli-quota-exhaustion-and-junction-fallback.md`.
Antigravity CLI (`agy`) vs IDE GUI launcher trap (`antigravity-ide.cmd chat`), missing binary diagnostics, and headless worker patterns: `references/antigravity-cli-agy-vs-ide-wrapper.md`.

## Antigravity CLI (`agy`) — Headless Subagent vs IDE GUI Wrapper Trap

### 1. The GUI Launcher Trap (`antigravity-ide.cmd`)
When attempting to hook Antigravity as an external CLI worker for Hermes, Claude Code, or Codex, never use `antigravity-ide.cmd chat -m agent`. That executable belongs to the desktop IDE (VS Code GUI fork) and only dispatches IPC to open the chat panel, exiting 0 immediately without waiting or writing output to stdout. It cannot function as an automated headless worker.

### 2. The Headless Antigravity CLI (`agy`)
The actual headless coding agent CLI provided by Google is `agy`. If `which agy` fails, the CLI is not yet installed on the host (install via Google's official install script: `https://antigravity.google/docs/cli/install` and run `agy login`).
When installed, call it like any headless CLI worker:
```bash
agy -p "<task>" --model "Gemini 3.6 Flash (Low)" --dangerously-skip-permissions
```
See `references/antigravity-cli-agy-vs-ide-wrapper.md` for full comparison matrix and troubleshooting details.

## OpenCode CLI — Windows Timeout, Encoding & Workspace Traps

### 1. Workspace Traps: Directory Scanning Hang (`read` tool timeout 120s)
When `opencode run` is invoked from a large or user-root directory (e.g. `C:\Users\<user>`), OpenCode's agent may invoke `read` on the current working directory, attempting to list/index thousands of files (`AppData`, `node_modules`, `venv`, caches), leading to complete freeze and 120s timeout.
- **Fix**: Always specify an isolated, empty sandbox directory via `--dir`:
  ```bash
  opencode run --dir "C:\Users\<user>\AppData\Local\Temp\opencode_sandbox" ...
  ```

### 2. Windows Wrapper Encoding Trap (`opencode.cmd` vs `opencode.exe`)
Calling `opencode` or `opencode.cmd` via Windows shell often converts non-ASCII Unicode prompt arguments (e.g. Vietnamese `"Done chốt phiên"`) to ANSI (`"Done ch?t phin"`), causing model hallucination or retry loops.
- **Fix**: In automated Python runners / bridges, bypass the shell wrapper and invoke the native binary directly:
  ```python
  opencode_bin = r"C:\Users\<user>\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe"
  ```

### 3. Proxy Farm Pool Timeouts
When routing OpenCode through proxy pools (e.g. `oc_farm.py`), ensure individual subprocess attempts enforce a strict sub-timeout (e.g. `timeout=35s`) per proxy rather than relying solely on the outer command timeout. This prevents dead/unresponsive proxy endpoints from holding the child process indefinitely.

## Claude Code — Common Failures

### Claude CLI turn-budget discipline

Do not add a tiny arbitrary `--max-turns` value merely for convenience. For bounded `claude -p` work, either omit `--max-turns` and use the outer terminal timeout, or derive a sufficient budget from the task contract: simple read-only inspection about 10 turns, standard implementation/review about 15, and complex multi-file work 20+ only when justified. If Claude returns `Reached max turns`, classify it as an insufficient caller budget—not a repo or product failure—then narrow the scope or rerun with a sufficient budget. Never present a max-turn exhaustion as a successful consultation, and do not blindly repeat the same prompt.

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

### Windows MSYS / Git Bash: `Argument list too long` (exit code 126) on Large Prompts/Diffs

When passing a large prompt or diff via `claude -p "$(< /path/to/file.txt)"` or command substitution on Windows, the call fails with:
`/usr/bin/bash: line X: .../claude: Argument list too long` (exit code 126) because Windows CLI argument buffer is capped at 32,767 chars.

**Fix**: Pipe prompt directly via stdin with `-` to `claude -p -`:
```bash
cat /c/path/to/prompt.txt | claude -p - --model opus --effort high
# Or in Python:
subprocess.run(["claude", "-p", "-", "--model", "opus", "--effort", "high"], input=prompt_text, text=True, encoding="utf-8")
```
> **Important**: Claude Code CLI requires `-` (dash) when consuming stdin via `--print` (`claude -p -`). Without `-`, it throws `Error: Input must be provided either through stdin or as a prompt argument when using --print`.

### Claude Code CLI: Windows MSYS Pipe Hang, Zero-Turn Review (`--tools ""`) & Orphaned Process Leaks

1. **MSYS Pipe Hang Without Dash (`cat ... | claude -p`)**:
   In Git Bash / MSYS on Windows, executing `cat file | claude -p` without trailing `-` causes the Windows-native Node.js CLI to wait indefinitely on stdin for EOF, timing out the shell. Always use `claude -p -` or read via file expansion `claude -p "$(< /path/to/file.txt)"`.

2. **Zero-Turn Review Failing With `Error: Reached max turns`**:
   When invoking `claude -p` for pure code review / audit on an already-provided diff, if `--tools ""` is omitted, Claude's model attempts to call tools (like `Read` or `Bash`) on turn 1. If combined with `--max-turns 1`, it immediately exits with `Error: Reached max turns (1)`.
   **Fix**: Pass `--tools ""` to disable tool execution so Claude responds directly as an LLM reviewer without burning turns on tool loops.

3. **Orphaned Background `claude.exe` Accumulation**:
   When foreground terminal commands time out or get cancelled, Windows Node.js processes for Claude can linger in memory indefinitely, consuming hundreds of MBs each and locking files.
   **Cleanup command**:
   ```powershell
   powershell.exe -NoProfile -Command "Get-Process -Name 'claude' -ErrorAction SilentlyContinue | Stop-Process -Force"
   ```

### Windows Python Path Trap in MSYS / Git Bash (`/c/` vs `C:/` or `/d/` vs `D:/`)

When running inline Python scripts or subagents from Git Bash:
```bash
python -c "open('/c/Users/Kibe/prompt.txt').read()" # FAILS: FileNotFoundError
python -c "open('/d/Taadaa/file.py').read()"        # FAILS: FileNotFoundError: [Errno 2] No such file or directory: '\\d\\Taadaa\\file.py'
```
Windows native Python (`python.exe`) does NOT understand MSYS mount points like `/c/` or `/d/`. It converts forward slashes to backslashes and treats `/d/...` as a relative path under the current drive (`C:\d\...`).

**Fix**:
Always use native Windows drive letters `C:/...`, `D:/...`, or `Path.home()` inside Python code on Windows:
```bash
python -c "open('C:/Users/Kibe/prompt.txt', encoding='utf-8').read()"
# Or dynamically:
python -c "from pathlib import Path; (Path.home() / 'prompt.txt').read_text(encoding='utf-8')"
```

### Windows Tool / Ripgrep Path Translation Trap (`/c/` and `/d/` vs `C:\` and `D:\`)

When invoking file-search tools (e.g. `search_files`) or Windows-native ripgrep (`rg.exe`) with POSIX/MSYS paths (e.g. `/c/Users/...` or `/d/Taadaa/...`), Windows-native `rg.exe` cannot resolve MSYS mount roots like `/c/` or `/d/`, causing:
```
Search failed: rg: /c/Users/...: IO error for operation on /c/Users/...: The system cannot find the path specified. (os error 3)
```
Repeating `search_files` with MSYS paths hits the same translation and triggers loop warnings (`same_tool_failure_warning`).

**Fix**:
- Always pass native Windows drive letters (e.g. `C:/...`, `C:\...`, `D:\...`) to `search_files` and ripgrep.
- When inspecting or searching within a specific file, use `read_file(path=r"C:\path\to\file")` with offset/limit instead of broad searches.
- For targeted pattern lookup inside a file, run a one-line Python script or single-file `grep -n` via terminal.

### Windows Host Terminal Guardrails & Subagent Call-Budget Discipline

On this Windows host, the terminal execution environment enforces strict security & safety guardrails:
1. **Foreground Timeout Required**: Every foreground `terminal` call must include `timeout` (<= 60s), or it is rejected with:
   `[GUARD_FOREGROUND_TIMEOUT_MISSING] Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True.`
2. **Recursive Grep Blocked**: Running `grep -rn` across directory trees is rejected with `[GUARD_RECURSIVE_GREP]`. Use single-file `grep -n <pattern> <file>` or targeted `search_files`.
3. **Python Filesystem Walkers Blocked**: Running inline python scripts that recursively walk the filesystem (`os.walk`, `rglob`, `glob(recursive=True)`) is blocked with `[GUARD_PYTHON_WALKER]`.
4. **Subagent Budget Discipline**: When dispatched as a subagent with a tight turn budget (e.g. <= 10 calls):
   - Never waste turns on broad exploratory scans or unconstrained searches.
   - Jump directly to the known target file (`read_file`), make the focused edit (`write_file` or `patch`), and run the targeted test (`pytest <file> -v` with explicit `timeout=30`).

### Claude Code CLI Hang / High Timeout in Massive Repositories (>500MB / Monoliths)

When running `claude -p "<task>" --allowedTools "Read,Bash"` inside large codebases with heavy runs/reports directories (e.g. `D:\Taadaa\tiktok-luot nuoi acc`):
- `claude` attempts to index, ripgrep, or inspect the entire project directory tree during turn execution, causing commands to hang and hit bash timeouts (300s).
- **Fix**: Pre-extract exact code blocks or anchors via bash/python first and pass targeted snippets directly into stdin via pipe:
  ```bash
  python -c "from pathlib import Path; print('\n'.join(Path('D:/repo/file.py').read_text(encoding='utf-8').splitlines()[100:200]))" | claude -p "Phân tích đoạn code sau: ..."
  ```
  This reduces Claude CLI execution time from >300s (timeout) to ~30s.

### Claude Code CLI: Terminal Redirection Operator Guard Collision

When invoking `claude -p "..."` via agent terminal where commands pass through shell-safety filters, redirect characters inside the prompt string trigger false-positive blocks:
`TERMINAL BLOCKED: Cấm dùng toán tử điều hướng ghi file '>' trong terminal: 'claude -p "..."'`
**Root Cause**: Shell command guard regexes often check `re.search(r"(?:^|[^0-9])>{1,2}\s*[^\s;&|]+", cmd)` to prevent file overwrites (`> file`). Strings like `->`, `> 3 files`, `>= 85`, `<= 15`, or `<script>` inside prompt arguments match this pattern.
**Fix**:
- Replace all `>` and `<` in the prompt string with verbal words (e.g. `sang`, `tren 3`, `tu 85 tro len`, `khong qua 15`, `duoi 30s`).
- Never put arrows (`->`) or inequality signs (`>=`, `<=`) directly in the shell argument string.

### Claude Code CLI: Foreground Timeout Guard (60s Cap) vs Background Execution

Agent terminal environments often enforce a hard cap on foreground timeouts (e.g. `GUARD_FOREGROUND_TIMEOUT_EXCEEDED: timeout=180s > 60s`).
Because Claude Code CLI with reasoning or multi-turn exploration frequently takes 60–120s, foreground calls with high timeouts will be blocked, while low timeouts (<= 60s) result in exit 124 timeout kills.
**Fix**:
Always run non-trivial Claude CLI tasks in background mode with completion notification:
`terminal(command="claude -p '...'", background=True, notify_on_complete=True, timeout=300)`

### Claude Code CLI: Stateless `-p` (Print Mode) Across Invocations

Each `claude -p` call starts a fresh, isolated session. It does NOT retain conversational history or drafts from prior `-p` executions in the same agent chat.
**Symptom**: Asking Claude to "ghi nội dung draft vừa soạn vào file" results in: *"Mình chưa ghi gì cả: trong phiên này không có bản draft nào... Đây là tin nhắn đầu tiên của phiên."*
**Fix**:
- Every print-mode prompt must be 100% self-contained, providing the exact text or modifications explicitly.
- Alternatively, pass `--continue` (`-c`) to resume the most recent conversation in that workdir, or `--resume <session_id>`.

### Claude Code CLI: Non-Interactive File Edits Require `--dangerously-skip-permissions`

In print mode (`-p`), Claude CLI may refuse to edit files or ask for confirmation unless permissions are bypassed.
**Fix**:
Pass `--dangerously-skip-permissions` when delegating autonomous file edits:
`claude --dangerously-skip-permissions -p "Sửa file X..."`

### Claude Code CLI: Backgrounding Subprocess Trap (`run_in_background=True` & Premature Exit)

When delegating long-running CLI or shell commands (e.g. farm runners, PowerShell batch scripts, compilation, test suites) via `claude -p`, if the prompt asks to "stream output" or leaves execution mode unspecified, Claude Code's model may invoke its `Bash` tool with `run_in_background: true`.
- **Symptom**: Claude prints `"The command is running in the background (ID ...). This tool can't stream output live, so I'll show you the full log once it finishes."` and immediately exits print mode with exit code 0 after only 5–10s.
- **Consequence on Windows**: When Claude's CLI process terminates, the Windows process group / subshell terminates along with it, abruptly killing the background Python/PowerShell runner mid-execution (e.g. while waiting for device UI or app startup), leaving orphaned device locks or incomplete reports.
- **Fix**: Always constrain execution explicitly in the prompt:
  ```bash
  claude -p --dangerously-skip-permissions "Run this command synchronously in foreground with run_in_background=false, timeout=600000ms: <command>. Wait until it exits completely, then show the entire output. Do NOT background the process."
  ```

### Dispatch Deadlocks, Dirty-Worker Salvage & CLI Escalation

When internal subagent dispatch reaches limits or a worker exits after leaving a dirty target:
- **Never declare L3 BLOCKED solely for an internal orchestration deadlock or dirty worktree.** L3 is reserved for a genuine external blocker (hardware failure, missing credentials, paid third-party action) or an unresolved ownership conflict after reconciliation.
- First perform read-only salvage triage: capture scoped status/diff, split paths and hunks, record hash/mtime and determine whether the worker/lease/process/action is still active. A worker-owned dirty hunk that is stable and non-overlapping with the exact requested diff is preserved, not reverted, and may be rescued only after shutdown/reconciliation gates pass.
- If the dirty hunk overlaps the requested edit or ownership cannot be separated, stop edits as `SCOPE_CONFLICT`; do not use Claude CLI or any fallback to overwrite it. Reconcile or quarantine first, then issue a new exact contract.
- Re-check ownership and hashes immediately before any write. Never use reset, checkout, clean, stash-drop, or revert as a cleanup shortcut. Worker self-report and exit code are not completion proof.
- After salvage, Claude CLI may be used only through its existing authenticated, exact-scope fallback contract; it is a transport/executor route, not permission to bypass leases, scope, L2 budget, offline test, canary, or closeout gates.
- See `references/dispatch-deadlock-and-cli-escalation.md`.




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
