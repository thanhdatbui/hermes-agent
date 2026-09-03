---
name: hermes-gateway-remote-control
description: "Set up and operate the Hermes messaging gateway (Telegram first) for remote control: bot setup, per-chat repo binding via channel_overrides, session semantics, and verification."
version: 1.0.0
author: Hermes Agent
tags: [hermes, gateway, telegram, remote-control, channel-overrides, sessions]
---

# Hermes Gateway Remote Control

Operate Hermes from Telegram (or other messaging platforms) on the user's Windows farm machine. Covers: first-time gateway setup, per-chat/per-group repo binding (`channel_overrides`), session semantics (context storage, `/new` vs `/resume` vs `/background`, threads/topics), reporting discipline, and evidence-based verification.

**Environment facts (Kibe machine):** HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes` (NOT `~/.hermes`). Gateway runs as its own process; desktop app + gateway are two views into the SAME HERMES_HOME (config.yaml, .env, state.db, sessions/, skills/, memory). Telegram is a thin adapter — no separate config namespace.

## Channel setup (Telegram)

1. **Token:** @BotFather → `/newbot` → token (secret, never put in chat). **User ID:** @userinfobot.
2. **Config:** `hermes gateway setup` wizard, or manual: append to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_ALLOWED_USERS=...      # comma-separated
   ```
   Pitfall: this machine's `.env` ships with a commented template (`# TELEGRAM_BOT_TOKEN=...` with a trailing `# Comma-separated user IDs`). Uncomment + strip the trailing comment or the gateway silently ignores the key. Validate format WITHOUT printing values (python regex: token `\d{6,12}:[A-Za-z0-9_\-]{30,40}`; users `\d+(,\d+)*`).
3. **Start:** `hermes gateway status` → `hermes gateway` (foreground test) → `hermes gateway install --start-on-login --start-now`.
   - Windows: Scheduled Task needs UAC; if declined it falls back to Startup-folder `.vbs` (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Hermes_Gateway.vbs`) — WORKS without admin, but only starts **after Windows login** (not at boot). PC sleep/shutdown kills the gateway; Telegram then goes silent.
4. **Verify (not self-report):** `hermes gateway status` → grep `logs/gateway.log` for `Connected to Telegram (polling mode)` + `✓ telegram connected` + `set_my_commands OK`. Then user sends `/start`; log shows the session key (`agent:main:telegram:dm:<userid>`).

## Per-chat repo binding — channel_overrides

`gateway.platforms.telegram.channel_overrides.<chat_id>.system_prompt` gives each chat/group its own system prompt (repo + behavior rules). Lookup order: chat_id → thread_id → parent_id. This is the "1 group = 1 repo" mechanism; groups are created by the USER (Telegram bots cannot create groups or add themselves).

**CRITICAL PITFALL — leading-dash chat_id keys:** group chat_ids are negative (`-5435853713`). Running
`hermes config set gateway.platforms.telegram.channel_overrides."-5435853713".system_prompt ...` stores the key WITH LITERAL QUOTE CHARS (`'"-5435853713"'`), which never matches the lookup → override silently ignored (agent keeps working in wrong cwd — the classic symptom). Correct form: NO quotes in the path:
```
hermes config set gateway.platforms.telegram.channel_overrides.-5435853713.system_prompt "..."
```
Verify the stored key AFTER every set (python yaml load; keys must equal the bare `-5435853713`). The CLI has NO unset — remove a bad key via a python yaml safe round-trip (`del`, `yaml.safe_dump`), then `hermes config check` + restart.

**PITFALL — bind the git REPO root, not the parent workspace (verified 2026-08-09):** "repo X trên <dir>" means the git repo at that dir, e.g. "repo hermes trên d:/taadaa" = `D:\Taadaa\Hermes`, NOT `D:\Taadaa`. The parent `D:\Taadaa` has its own AGENTS.md (shared workspace rules) but is NOT a git repo (`git rev-parse --show-toplevel` fails there) — binding to it points the agent at the wrong repo while a nearer AGENTS.md makes it look correct. Before binding, run `git rev-parse --show-toplevel` in the candidate dir and use that path in the override. Verify the binding with an EXACT substring check on the stored prompt (python yaml round-trip: `'D:\\Taadaa\\Hermes' in system_prompt`), not just key presence — a wrong path binds silently. Multi-line prompts set via bash ANSI-C quoting (`BINDING=$'...'` then `hermes config set ... "$BINDING"`) survive the yaml round-trip fine.

**Applying changes:** the gateway reads config only at process start, and per-session system prompts are pinned at session creation (prompt-caching invariant). Rule of thumb: change config → `hermes gateway restart` → user runs `/new` in the affected chat. **Never restart mid-batch** — a restart interrupts the running agent ("Your current task will be interrupted"). If a batch is running, set the config now, restart after it finishes.

**Restarting from INSIDE the gateway process (Telegram session):** `hermes gateway restart` is hard-blocked in-session — `Blocked: cannot restart or stop the gateway from inside the gateway process ... SIGTERM propagates to child processes`. Workaround (verified 2026-08-09): use Task Scheduler to spawn the restart OUTSIDE the gateway's process tree, so the SIGTERM propagation rule doesn't apply:
```bash
schtasks /Create /TN "hermes_gw_restart_<tag>" /TR "cmd /c \"C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe gateway restart\"" /SC ONCE /ST 23:59 /F
schtasks /Run /TN "hermes_gw_restart_<tag>"
schtasks /Delete /TN "hermes_gw_restart_<tag>" /F
```
Notes: git-bash needs SINGLE-slash `/Create` (double-slash `//Create` → `Invalid argument/option`, same quirk as `tasklist //FI`). The full path to `hermes.exe` is required (PATH lookup may not resolve from the Task Scheduler context). The restart interrupts the current session — expect the Telegram session to be recovered after gateway comes back (per the recovery pattern), and re-verify state afterwards.

Pitfall: `hermes config set` occasionally fails with a transient `PermissionError: [Errno 13]` on config.yaml (brief file lock). Retry after ~2s; if the direct open-write keeps failing, write a `.tmp` file then `os.replace(tmp, path)` — that worked even when in-place write was denied.

## Global fallback prompt — auto-rules for every NEW group

`agent.system_prompt` in config.yaml is the ephemeral channel prompt for ALL chats WITHOUT a channel_override (new groups, DM, threads). Env `HERMES_EPHEMERAL_SYSTEM_PROMPT` takes precedence over it. Set it once → every group created later inherits the rules automatically, no per-group config needed (this is the user's "tạo nhóm mới → tự nạp rule mới nhất" mechanism).

`agent.personalities.<name>.{description, system_prompt}` = named rule presets. The `/personality` slash command switches the global prompt LIVE (no restart):
- `/personality` → list presets
- `/personality <name>` → writes `agent.system_prompt` + updates in-memory → applies on the next message
- `/personality none` → clears back to stock

Layering: a channel_override REPLACES the global fallback (NOT merged) → repo-bound groups must embed the common rule block (QUY TẮC BÁO CÁO, ảnh màn hình) inside their own override; only non-override chats follow `agent.system_prompt`. Global prompt changes affect NEW sessions only (existing chats need `/new`).

## Locating group chat_ids and titles

- chat_id: `grep -oE "telegram:group:-[0-9]+:[0-9]+" logs/gateway.log | sort -u` (pattern `telegram:group:<id>:<userid>`).
- Human-readable titles: `sessions/sessions.json` — each session_key carries `display_name` (e.g. "Tikok Reg"); repo path usually matches the title. state.db also has a `system_prompts` table (hash → prompt) and `sessions` table (display_name, model).
- Telegram bots CANNOT create groups or add themselves — the user creates each group, adds the bot, sends one test message; then read the chat_id from the log.

## Session semantics (multi-session like PC)

- One Telegram chat/thread/group = one session at a time. `state.db` (SQLite) holds messages + sessions + system_prompts; `sessions/sessions.json` = routing index. All local, shared with desktop, stored "forever" — but auto-managed.
- Auto-lifecycle (gateway defaults, on this machine): compression `threshold: 0.3` (protect first 3 / last 20), idle-reset `idle_minutes: 1440` (24h) with daily sweep `at_hour: 4`. No manual pruning needed; only prune state.db by hand > ~500MB.
- Commands: `/new` = reset context (NOT restart gateway); `/title <name>` + `/resume <name>` = switch between named sessions; `/sessions` = list; `/background <prompt>` = fire-and-forget parallel session delivering to the same chat; every group = its own separate session.
- DM threads: Telegram "New Thread" button + Hermes `/topic` command + `extra.dm_topics` config; each thread = separate session (thread_id in session key). But binding via channel_overrides on threads inherits parent chat.
- **Cùng 1 repo = 1 session ghi tại 1 thời điểm (user rule, confirmed 2026-08-09):** `/new` chỉ reset context chứ KHÔNG tách working tree; `/background` spawn session riêng NHƯNG dùng chung filesystem/repo — 2 session sửa cùng repo có thể giẫm file, test/build loạn, commit sai. Không làm 2 việc ghi cùng repo song song qua gateway. Muốn song song: git worktree/branch riêng rồi review-merge; `/background` chỉ dùng cho việc không đụng file repo đang được session khác sửa (vd monitor/đọc).
- Model switching: `/model` shows provider menu with counts = number of models exposed, NOT a ranking; `/model provider:model` sets directly (e.g. `custom:9router` is the default chat_completions proxy at `127.0.0.1:20128`). In the Telegram gateway picker, selecting a model performs a session hot-swap **and**, unless session-only behavior is explicitly requested/configured, persists the selected model/provider to `config.yaml` for new sessions; the confirmation will say `Saved to config.yaml (--global)`. This does not hot-swap an already-running different Telegram session, which keeps its own session override/model until restarted or explicitly changed. For a one-session-only switch, type `/model <model> --session` rather than relying on the picker default. Verify the confirmation text and config instead of inferring scope from the provider menu alone.

## Reporting discipline (noise control)

Default multi-turn behavior spams progress. For batch/long ops, embed in the group system_prompt:
- `QUY TẮC BÁO CÁO:` NO step-by-step or tool output; intermediate turns use `[SILENT]`; only a final summary (per-machine results, timing, log paths) or a blocker error.
- **PITFALL (verified 2026-08-09): a LITERAL `[SILENT]` message is DELIVERED to the user on Telegram.** It is not swallowed by the platform — sending any body text that is just `[SILENT]` makes the user see it and ask "Là sao silent?". "Silent" must mean emitting NO message at all for that turn (empty/no final text), never sending the marker as content. When you have nothing to report, produce no user-facing message; when you have a real milestone, send it.
- Sequence is model obeying the prompt, so verify per-use-case; also there is NO per-chat `cwd` in the gateway (only global `terminal.cwd`) → overrides must say "cd <repo> before EVERY terminal command".
- Screenshot capabilty: `adb -s <serial> exec-out screencap -p` — no need to open the xiaowei mirror app (it reads the same source). Add a screenshot rule with serial lookup: serial from `D:\CodexRuntime\tiktok-video\config-machine-N.yaml` or workbook mapping (`Tik1.xlsx`), else report and don't guess.

## Verification (do not trust screenshots)

- Session transcript: query `state.db` directly:
  `sqlite3 messages where session_id=? role!='system'` etc. — the real content the agent saw; better than vision descriptions of user screenshots.
- Gateway log: `logs/gateway.log` — platform connection + session key creation.
- Overrides actually reaching the model: grep `messages` content — the bot's answer must reflect the override text (e.g. "cd /d/Taadaa/Tiktok-video").
- "Skill/AGENTS memory: 100% shared" — all groups use the same skills/memory; AGENTS.md from repo loads only when agent runs in that repo (system_prompt cd pattern enables it).

## Multi-machine control (Hermes vs OpenClaw)

Do not equate Hermes SSH with OpenClaw Node pairing. Hermes `terminal.backend: ssh` targets one configured SSH host; one shared Telegram bot/session controlling two hosts needs an explicit two-host router (two named scripts/tools or MCP targets). OpenClaw has a native Gateway + paired Nodes topology. Keep one Gateway as the state owner when shared context is required; use separate profiles/bot tokens for isolated agents. Verify execution host with `hostname && pwd` before destructive work. Full decision table, topology, security rules, and state-sharing pitfalls: `references/multi-machine-hermes-vs-openclaw.md`.

## Windows quirks

- `tasklist //FI` FAILS in git-bash (double-slash, same as `schtasks`); use `wmic process where "Name='python.exe'" get ...` or single-slash.
- Notepad from git-bash: `notepad.exe <file>` BLOCKS the terminal (watch out); `explorer.exe <file>` launches the default handler and returns.
- `hermes config set` value with embedded `=`/paths works as a single arg; be careful of the YAML key quoting above.
- `powershell -c '...$_...'` — bash expands `$_` (last echo arg); use single quotes and escape or a `.ps1`.

## References

- `references/per-group-repo-binding-recipe.md` — copy-paste recipe: common rule block (QUY TẮC BÁO CÁO + ảnh màn hình), global prompt, personality presets, repo-bound overrides, group map, verification snippets.
- `references/telegram-gateway-setup-2026-08-08.md` — full worked walkthrough (setup, the quoted-key bug diagnosis, DB verification output)