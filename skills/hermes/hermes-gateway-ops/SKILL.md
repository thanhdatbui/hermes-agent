---
name: hermes-gateway-ops
description: Configure, run, verify, and extend the Hermes messaging gateway (Telegram setup, channel_overrides chat→repo binding, multi-session semantics, Windows install/terminal quirks).
---

# Hermes Gateway Ops

Trigger: set up or operate the messaging gateway (Telegram first), bind a chat/group to a repo via `channel_overrides`, explain multi-session on Telegram, verify a bot is online, or debug gateway config.

## CLI commands

```bash
hermes gateway setup          # wizard interactive — chọn platform, nhập token/user ID, tự ghi config, offer start/restart
hermes gateway                # chạy foreground (WSL/Docker/Termux khuyên dùng foreground)
hermes gateway start|stop|restart|status
hermes gateway install [--start-now] [--start-on-login] [--system] [--force]
hermes gateway list           # trạng thái tất cả profiles
hermes gateway enroll         # relay connector (experimental)
```

Gateway = **1 background process** chạy TẤT CẢ platform đã cấu hình cùng lúc + cron scheduler (tick 60s) + session store per chat + voice (STT/TTS). Token/secret → `.env`, KHÔNG bao giờ vào config.yaml; behavioral settings → config.yaml. Bots cần model provider + tool providers (TTS, web). Token lộ → BotFather `/revoke`.

## Setup (Telegram)

1. Bot: @BotFather → `/newbot` → token `123456789:ABC...` — **secret, never paste into chat** (user enters it in wizard or .env themselves).
2. User ID: @userinfobot → numeric ID.
3. Config: `hermes gateway setup` (wizard) OR edit `.env` at `$HERMES_HOME/.env` (Windows: `C:\Users\Kibe\AppData\Local\hermes\.env`):
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_ALLOWED_USERS=111111,222222   # comma-separated IDs
   ```
4. Existing-install / self-setup workflow:
   - If Hermes is already installed and the user wants a Telegram bot connected to that machine, do not restart installation or force a one-prompt-at-a-time relay when the user asks Hermes to configure itself. Give one bounded self-contained prompt to the installed Hermes app, or let `hermes gateway setup` complete in one run.
   - If the wizard is open, inspect the exact current prompt and answer only that prompt; never guess the next prompt. Typical sequence: choose Telegram → enter token locally → enter allowlisted user ID → confirm home channel → choose `26` (Done) → accept start/auto-start if requested.
   - Keep tokens/API keys out of chat, screenshots, logs, and reports. Do not replace a working shared 9Router key with a dummy key; keep `http://<kibe-lan-ip>:20128/v1` and validate `/v1/models` with the active key.
5. Cron creation syntax (CLI):
   - `hermes cron create "every 30m" --name "<name>" --no-agent --script "<script-filename>"`: Schedule must be positional, not `--schedule`. Scripts must be inside `~/.hermes/scripts/` (relative filename only, no absolute paths). Use `"every 30m"` for recurring forever jobs (plain `"30m"` creates a one-shot `0/1` job).
6. Vision direct routing (Native):
   - Multimodal models (Gemini 3.7 / GPT-4o / Claude) MUST use `hermes config set agent.image_input_mode native`, clear `auxiliary.vision`, and explicitly disable the vision tool via `hermes tools disable vision --platform cli` + `hermes tools disable vision --platform telegram`. This ensures raw pixels go directly to the main model without `vision_analyze` being injected into the tool schema. Verify with `hermes tools --summary`.
7. Start & Auto-Recovery:
   - Foreground test: `hermes gateway`
   - Auto-start (Windows): `hermes gateway install --start-on-login --start-now` → creates Scheduled Task ONLOGON; if UAC is skipped it **falls back to a Startup-folder `.vbs`** — still works, no admin needed.
   - **24/7 Watchdog (Crash auto-recovery):** `hermes gateway install` only runs once at logon. On secondary/headless nodes (e.g. Admin machine) without a tray watcher, install a 2-minute recurring Scheduled Task watchdog (`Hermes_Gateway_Watchdog` executing `$LOCALAPPDATA\hermes\scripts\watchdog-gateway.ps1`) to revive the process if killed by OOM, SQLite FTS transcript bloat (>700 msgs), or network timeouts. See `references/admin-telegram-gateway.md`.
   - `hermes gateway restart` drains cleanly (auto-approved by smart approval).
   - When Android VPN/proxy is retired, decouple Hermes liveness recovery from the proxy tray. Use the standalone watchdog and verification ladder in `references/independent-hermes-watchdog.md`; default to `hermes gateway start` on absence, not a periodic restart.
   - **Hard-review fallback:** for a code change that requires independent review, do not stop at a transient/credential-specific failure from the primary reviewer. Use the configured fallback chain; for a hard case, call `gpt-5.6-sol` through the 9Router HTTP endpoint with `stream:false`, `tools:[]`, and `tool_choice:none`. Review the exact staged/post-rebase candidate, not a remembered diff. A changed commit SHA invalidates the previous verdict and requires a fresh review.
   - **Repo/task split:** keep the committed watchdog source in the tooling repository, while the Windows Scheduled Task remains machine-local runtime state. Preserve unrelated dirty paths; stage only the watchdog source. If the local checkout is dirty and the remote advanced, use a clean temporary worktree from `origin/main`, cherry-pick the exact validated commit, re-run parse/smoke/review on the new SHA, then push and verify `git ls-remote`.
7. Verify: `hermes gateway status`; log `%LOCALAPPDATA%\\hermes\\logs\\gateway.log` for `[Telegram] Connected to Telegram (polling mode)` + `✓ telegram connected` + `set_my_commands OK`. A log line such as `Ignoring /start platform ping` is a normal guard for Telegram platform pings, not proof that the bot is broken; test with `/model` or a normal message. Session key format: `agent:main:telegram:dm:<uid>` / `telegram:group:<chat_id>:<uid>`.

Gateway runs the SAME profile/config as the desktop (`config.yaml`), so the `/model` switcher on Telegram shows every provider configured on the machine — **numbers in parens = model count per provider** (`total_models`), not priority, NOT provider order (source-verified 2026-08-09 `plugins/platforms/telegram/adapter.py:5150` `_build_provider_keyboard`: `label = f"{p['name']} ({count})"`). A large count (for example 493–495 on an OmniRoute endpoint) is the live `/v1/models` catalog exposed by that endpoint, not the number of models the user needs to configure or the number of Gemini variants; verify raw row count, unique IDs, and target-model presence before interpreting it. `✔` = provider hiện tại của session. For a configured named provider, avoid the picker and use the explicit session-scoped form: `/model <exact-model-id> --provider <provider-name> --session` (for example `/model antigravity/gemini-3.7-flash-high --provider omni --session`). Do not use `/model <model>` alone when the current provider could resolve it elsewhere, and never add `--global` unless explicitly requested.

For an existing install where the runtime says `Unknown provider 'custom:<name>'`, do not reopen Desktop onboarding or repeat Telegram setup. Check the named provider entry first. Current runtime-compatible keyed schema uses `providers.<name>.api`, `key_env`, `transport: chat_completions` (for OpenAI-compatible endpoints), and `default_model`, with `model.provider: custom:<name>` and `model.default: <model>`. Apply through `hermes config set`, run `hermes config check`, then restart only if the gateway must reload config and verify a real Telegram reply.

## Tool/iteration budget authority (Windows)

When a user says the tool-call budget was raised, verify all three layers; do not assume `delegation.max_iterations` controls the parent chat:

```bash
hermes config set agent.max_turns 100
hermes config set delegation.max_iterations 100
hermes config set code_execution.max_tool_calls 100
hermes config check
hermes config show   # must report Max turns: 100
```

- `agent.max_turns` controls the parent/session tool-calling loop.
- `delegation.max_iterations` controls delegated child budgets.
- `code_execution.max_tool_calls` controls execute-code batching.
- On Windows, inspect `HERMES_MAX_ITERATIONS`: a stale process/user environment value can override or mask YAML during a running process. Persistent user env can be set with `setx HERMES_MAX_ITERATIONS 100`; verify via the Windows user environment/registry, not only the current shell (the current process may still show the old value). In git-bash, `reg query HKCU\Environment` fails with `Invalid key name` (escaping) — verify with python: `python -c "import winreg; k=winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment'); print(winreg.QueryValueEx(k,'HERMES_MAX_ITERATIONS')[0])"`. The `.env` ghost variant (if any) is auto-removed by `hermes doctor --fix`; the HKCU/process variant is not.
- A running gateway/session does not reload its environment or budget in place. Apply the change only on a new session/process. **Do not restart the gateway while a live farm batch is running**; schedule the restart after the batch and verify `hermes gateway status` plus `hermes config show`.
- Distinguish Hermes config from an outer harness hard cap: if the exact error is `You've reached the maximum number of tool-calling iterations allowed`, YAML may be correct while the current platform/session still has an independent cap. Report this separately; do not claim the config alone guarantees the outer cap.
- `hermes config get` is not a valid command in this CLI; use `show`, `set`, `check`.

## .env pitfalls (verified 2026-08-08)

- The .env often ships with **commented template lines** (`# TELEGRAM_BOT_TOKEN=...`). Users paste values onto them but keep the `#` → gateway silently ignores them. Uncomment both lines.
- Users paste the value **including the template's trailing comment** (`# Comma-separated user IDs` becomes part of the value → 54 chars, invalid). Strip with `value.split('#')[0].strip()`.
- Never print secret values; validate shape only (regex + char counts):
  - token: `^\d{6,12}:[A-Za-z0-9_-]{30,40}$`
  - users: `^\d+(,\d+)*$`
- Fix via byte-safe Python (preserve CRLF, keep everything else untouched), then re-validate.

## Windows terminal quirks (git-bash) — GUI launches

- `cmd //c start notepad` and bare `notepad.exe file` are **unreliable** (bare notepad blocks the shell and gets killed on timeout).
- **Working method: `explorer.exe "C:\path\to\file"`** — opens via default association (Notepad for .env) and the process survives.
- `tasklist //FI` is broken in git-bash (like `schtasks //Query`) → use `wmic process where "Name='x.exe'" get ProcessId,CommandLine`.
- PowerShell `-Command "..."` with `$_` gets bash-mangled (`$_` expands to last arg) → **always single-quote** the PS command: `powershell -NoProfile -Command 'Get-Process notepad | ...'`.

## channel_overrides — bind a chat/group to a repo

The built-in mechanism for "1 group = 1 repo": per-channel `system_prompt` (+ optional model/provider). Lookup matches **chat_id, then thread_id**. The binding is instruction-level (agent is told to `cd` into the repo every command), not a hard shell cwd pin — good enough for practical use; hard isolation would need separate gateway/profile per repo.

```yaml
gateway:
  platforms:
    telegram:
      channel_overrides:
        "-5435853713":            # group chat_id (quotes OK ở FILE yaml; còn CLI path thì KHÔNG nháy — xem bên dưới)
          system_prompt: "Bạn phụ trách repo D:\\Taadaa\\Tiktok-video (main). Trước MỌI lệnh terminal phải cd /d/Taadaa/Tiktok-video; tuân theo AGENTS.md/HANDOFF.md/PROJECT_RULES.md; không sửa file ngoài repo; không đọc credential/workbook."
```

- Set via CLI — **numeric key phải KHÔNG nháy** (đã dính bẫy và sửa thật 2026-08-08):
  `hermes config set gateway.platforms.telegram.channel_overrides.-5435853713.system_prompt "..."` → `hermes gateway restart`.
- PITFALL (lỗi thật trong session): set path kèm nháy như `...channel_overrides."-5435853713".system_prompt` → CLI ghi key literal `"-5435853713"` (cả dấu nháy là một phần key) → override **âm thầm không bao giờ khớp** (bot không nhận system_prompt). Kiểm tra key: `list(ov.keys())` qua python yaml — nếu thấy key/có nháy là sai. Sửa: set lại key không nháy, rồi xóa key nháy bằng python yaml load→safe_dump round-trip + `hermes config check` (CLI không có unset), xác nhận còn đúng `['-5435853713']`.
- **New system_prompt only applies to NEW sessions — user must run `/new` in the channel** (prompt is baked at session creation; an existing session keeps its old prompt).
- Get the chat_id: `grep -oE "telegram:(group|forum|dm):[0-9-]+" gateway.log | sort -u`.
- `hermes config get` does NOT exist — use `hermes config show`.

## High-concurrency gateway & SQLite state.db tuning (multi-session lag)

Khi chat đồng thời nhiều session/group/thread, Gateway có thể bị nghẽn ở 2 tầng nếu chưa tinh chỉnh:

1. **Gateway ThreadPoolExecutor concurrency (`max_workers`):**
   - Mặc định code gốc gán cứng `max_workers=10` trong `gateway/run.py` (`_get_executor`). Khi >10 session cùng chạy turn/tool, session thứ 11+ phải xếp hàng chờ trong thread pool.
   - Cơ chế tối ưu: Cho phép đọc động từ `config.yaml` qua `gateway.max_workers` (nâng lên 25–30).
   - Set qua config: `hermes config set gateway.max_workers 25`.

2. **Tranh chấp SQLite write lock (`state.db: database is locked`):**
   - `state.db` chạy WAL mode nhưng `_WRITE_MAX_RETRIES=15` (~1.5s total retry) và `timeout=1.0s` trong `hermes_state.py` dễ bị fail khi nhiều session cùng lưu transcript hoặc routing save.
   - Sửa trong `hermes_state.py`: Nâng `_WRITE_MAX_RETRIES = 50`, dải jitter `_WRITE_RETRY_MIN_S = 0.030` / `_WRITE_RETRY_MAX_S = 0.200`, và timeout kết nối lên `timeout = 5.0` trong `_connect_and_init()`.
   - Áp dụng trên cả runtime `%LOCALAPPDATA%\hermes\hermes-agent\venv\Lib\site-packages\` và source checkout.

## Verification: override đã tới model chưa (state.db)

Không dựa vào tự báo cáo của bot — đọc transcript thật:
- `$HERMES_HOME/state.db` (SQLite): bảng `messages` có `session_id, role, content` — query session của chat lấy assistant answer + tool output, xác nhận agent làm đúng system_prompt (vd tự cd đúng repo trước lệnh).
- `system_prompts` table chỉ có `hash, prompt` (KHÔNG có cột session_id) — đừng query nó theo session_id.
- Session key → session_id: `$HERMES_HOME/sessions/sessions.json` (map session_key → session_id; group key dạng `agent:main:telegram:group:<chat_id>:<user_id>`).

## Session reset, expiry, and resume recovery

Use this when a Telegram chat suddenly shows `Session automatically reset`, says the daily schedule is 04:00, or the agent appears to have lost its old context.

1. **Inspect before changing anything.** Read the effective config with `hermes config show` and read the exact YAML block with `read_file`/a redacted file view. `hermes config get` is not a valid command in this CLI. The relevant keys are:
   ```yaml
   session_reset:
     mode: both       # idle, daily, both, or none
     idle_minutes: 1440
     at_hour: 4
   ```
   `mode: both` means idle expiry **and** a daily reset at `at_hour`; it is not merely a display notice.
2. **Disable unwanted automatic resets immediately** with the supported setter, never by hand-editing YAML:
   ```bash
   hermes config set session_reset.mode none
   hermes config check
   grep -n -A4 '^session_reset:' "$HERMES_HOME/config.yaml"
   ```
   Leaving the old `idle_minutes`/`at_hour` values is harmless while mode is `none`; keep them as dormant defaults unless the user asks to remove them.
3. **Distinguish reset from compression.** A reset creates/finalizes a session with `end_reason=session_reset`; context compression is a separate hygiene path and may preserve the same session ID. Verify with `gateway.log` and SQLite `state.db`, not the bot's self-report:
   ```sql
   SELECT id, chat_id, thread_id, title, started_at, ended_at, end_reason,
          message_count, expiry_finalized
   FROM sessions WHERE source='telegram' ORDER BY started_at DESC;
   ```
   Match `chat_id` plus `thread_id`; a group topic and the non-topic group are different sessions.
4. **Find the old session before resuming.** Use `hermes sessions list` or the SQLite row, then record the exact ID. A reset usually leaves the old transcript in the DB and creates a newer routing entry; do not assume the newest session is the desired historical context.
5. **Resume through the target chat's inbound command path.** In Telegram, send `/resume <session_id>` from the user's chat (or use the interactive CLI `/resume`/`hermes --resume`). Do not use `hermes send` as a substitute: it sends an outbound bot message and does not reliably execute a user-issued gateway slash command. Verify the resulting `gateway.log` inbound event and the session/routing row afterward.
6. **Apply config changes safely.** A running gateway loads config at startup. If a restart is needed, perform it from an external shell/service context; a command launched from inside the gateway process is intentionally blocked because it would kill its own parent. Never restart while a live farm batch is running. After restart, verify `hermes gateway status`, the process, and the config again.
7. **Handle a stuck old session explicitly.** If the log reports a very large idle duration or an iteration such as `4/60` after many hours, treat it as a stale/hung agent run: preserve the transcript, stop/recover the specific session through the gateway's normal command path, and only then resume. Do not keep injecting repeated prompts into the same stale run.

A concise reproduction/verification checklist is in `references/session-reset-and-resume.md`.

## Multi-session semantics (verified in source)

- Session key = `platform:chat_type:chat_id[:thread_id]` → **every chat, group, and thread = a separate session/context**.
- Telegram DM **"New Thread"** client button (shown above the input box: "Type any message to create a new thread") → `message_thread_id` → separate Hermes session, natively supported.
- **Kích hoạt DM Topics (chat 1-1 riêng với Bot thành dạng Topics/Thread)**:
  - Bot chỉ hiển thị giao diện Topic trong chat 1-1 khi bot đã từng gọi Telegram API `createForumTopic` (hoặc nhận thread message).
  - Cách kích hoạt chuẩn và nhanh nhất cho bot mới mà không ảnh hưởng nhóm: Thêm `extra.dm_topics` vào `config.yaml` của profile bot đó rồi restart gateway:
    ```yaml
    gateway:
      platforms:
        telegram:
          extra:
            dm_topics:
              - chat_id: 1076231895  # ID Telegram của user
                topics:
                  - name: "General"
    ```
  - Khi gateway restart, bot tự động tạo Topic "General" và gửi seed message → client Telegram lập tức chuyển sang giao diện Topics (hiện nút New Thread để mở session mới).
  - Các group liên kết repo (`channel_overrides`) hoàn toàn **không bị ảnh hưởng**, vẫn là các nhóm chat làm việc bình thường.
- **Group thường (không phải forum) = 1 session duy nhất** — mọi tin nhắn chung 1 context. Muốn tách 2 việc cùng repo trong 1 group: `/new` giữa các việc (reset context, không tạo chat mới) hoặc nhắc rõ "chuyển việc: giờ làm X".
- **Group forum topics = mỗi topic 1 session riêng nhưng VẪN thừa hưởng channel_override của group** → pattern chuẩn cho "1 repo, nhiều việc song song" (vd repo Tiktok-video: topic `upvideo` + topic `render-video`): bot tự cd đúng repo ở mọi topic, context không trộn lẫn.
- **DM thread KHÔNG tự có override repo** — channel_overrides match theo chat_id (group); thread_id trong DM sinh tự động nên override theo thread rất thủ công → bot trong DM thread không tự cd repo, phải nhắc đường dẫn tường minh hoặc chỉ dùng cho việc không cần repo.
  gateway:
    platforms:
      telegram:
        extra:
          dm_topics:
            - chat_id: 1076231895  # ID Telegram
              topics:
                - name: "General"
                - name: "Tiktok Video"
  ```
- **Group thường (không phải forum) = 1 session duy nhất** — mọi tin nhắn chung 1 context. Muốn tách 2 việc cùng repo trong 1 group: `/new` giữa các việc (reset context, không tạo chat mới) hoặc nhắc rõ "chuyển việc: giờ làm X".
- **Group forum topics = mỗi topic 1 session riêng nhưng VẪN thừa hưởng channel_override của group** → pattern chuẩn cho "1 repo, nhiều việc song song" (vd repo Tiktok-video: topic `upvideo` + topic `render-video`): bot tự cd đúng repo ở mọi topic, context không trộn lẫn.
- **DM thread KHÔNG tự có override repo** — channel_overrides match theo chat_id (group); thread_id trong DM sinh tự động nên override theo thread rất thủ công → bot trong DM thread không tự cd repo, phải nhắc đường dẫn tường minh hoặc chỉ dùng cho việc không cần repo.
- Verify group thường vs forum bằng session key trong `gateway.log`: `grep -oE "session agent:main:telegram:(dm|group|forum):[0-9-]+(:[0-9]+)?" "$LOCALAPPDATA/hermes/logs/gateway.log" | sort -u` — group thường = `telegram:group:<chat_id>:<user_id>` (KHÔNG có segment thread_id thứ 3 sau user_id); DM thread = `telegram:dm:<uid>:<thread_id>`.
- Commands: `/new` (reset context — does NOT create a new Telegram chat), `/title <name>` + `/resume <name>` + `/sessions` (named sessions, switch like tabs), `/background <prompt>` (parallel background run, result delivered back to the chat — fire-and-forget), `/sethome` (cron delivery target).
- Groups: unless BotFather Group Privacy is OFF (`/mybots → Bot Settings → Group Privacy`) or the bot is promoted to admin, the bot only sees `/`-commands and replies — ordinary group chatter is invisible.
- Deep-dive (source paths, SessionSource/thread_id, dm_topics config, ChannelOverride dataclass): see `references/multi-session-and-channels.md`.

## Telegram display presets and change discipline

Use this when the user asks about Telegram noise, progress, heartbeats, or process-result notifications.

### First: distinguish inquiry from authorization

- A question such as “can I revert it?”, “what modes exist?”, or “would preset X be better?” is **not** permission to change `config.yaml`.
- First inspect and report the current effective values and named choices. Apply `hermes config set` only after the user explicitly chooses a preset/key.
- After changing, read back the exact affected keys. State whether each setting is Telegram-scoped or global; do not claim a restart is needed unless verified.

### Naming for quick user requests

Call these **Telegram display presets**. The user can later say, for example, “set Telegram preset 1”. Define the chosen key values inline before applying; preset names are convenience labels, not a built-in Hermes enum.

| Setting | Valid/useful values | Scope and effect |
|---|---|---|
| `display.platforms.telegram.tool_progress` | `all`, `off`, `log` | Per Telegram. Tool-start/progress bubble; `log` writes locally rather than chat. |
| `display.platforms.telegram.tool_progress_grouping` | `accumulate`, `separate` | Per Telegram. `accumulate` edits one progress bubble; `separate` emits one per tool. |
| `display.platforms.telegram.interim_assistant_messages` | `true`, `false` | Per Telegram. Natural mid-turn status messages, independent of tool progress. |
| `display.platforms.telegram.long_running_notifications` | `true`, `false` | Per Telegram. Heartbeat for long-running turns. |
| `display.platforms.telegram.thinking_progress` | `true`, `false` | Per Telegram. Scratch/thinking relay; default to off in groups. |
| `display.background_process_notifications` | `all`, `result`, `error`, `off` | **Gateway-global**, not Telegram-only: `all` includes running output + final; `result` only final success/failure; `error` only non-zero final; `off` silent. |
| `streaming.enabled` | `true`, `false` | Global token-delta streaming; separate from tool/process progress. |

### Practical presets

1. **Theo dõi live, ít spam:** tool `all`, grouping `accumulate`, interim `true`, long-running `true`, background `result`, thinking `false`, streaming `false`. This gives one evolving progress bubble plus an outcome, without token/thinking noise.
2. **Theo dõi đầy đủ:** tool `all`, grouping `accumulate`, interim/long-running `true`, background `all`; use only when frequent live output is wanted.
3. **Gọn nhưng không mất dấu:** tool `off`, interim/long-running `true`, background `result`.
4. **Chỉ kết quả/lỗi:** tool/interim/long-running/thinking `off`, background `error`; explain explicitly that an apparently stuck task has no live clue until it fails or the user asks status.

Use `hermes config set` for every approved value (never hand-edit config). Verify with a redacted YAML read or `hermes config show`; never print secrets.

## Cron watchdog (no_agent) semantics & delivery targeting

- **no_agent cron delivery rules**: stdout non-empty → delivered verbatim; stdout EMPTY → **silent** (nothing sent); non-zero exit / timeout → error alert (sent even with empty stdout). So a sync/watchdog script must print NOTHING on success and print the error + exit 1 on failure — the "chỉ báo khi lỗi" pattern (user yêu cầu 2026-08-11 cho `taikhoan-run-safe-sync`: trước đó print "Đã đồng bộ..." mỗi giờ → spam group Automation Core).
- **Đổi nơi nhận của cron**: `cronjob update deliver="telegram:<chat_id>"` (đích DM) — `deliver="origin"` gửi vào group nơi tạo job. User preference farm Taadaa: thông báo/lỗi cron → DM bot "Taadaa Hermes Sever" = `telegram:1076231895` (Home channel = `telegram:dm:<user_id>`), KHÔNG vào group. Verify bằng `cronjob list` đọc lại `deliver`.
- **Tìm origin chat của 1 job**: `$HERMES_HOME/cron/jobs.json` chứa `origin.chat_id` + `origin.chat_name` (authoritative; gateway.log chỉ cho ID không kèm tên). Map ID→tên nhóm khác: `grep -oE "telegram:(group|forum|dm):[0-9-]+" logs/gateway.log | sort -u` + `channel_overrides` trong config.yaml.
- **Cron script + repo**: script trong `$HERMES_HOME/scripts/` chỉ là launcher passthrough (subprocess gọi wrapper trong repo để logic commit được). Sửa logic → sửa file trong repo + HANDOFF.md entry (append byte-safe giữ CRLF), KHÔNG sửa launcher. Test 2 nhánh trước khi xong: success → exit 0 + stdout rỗng; failure (vd env trỏ source không tồn tại) → error + exit 1.
- **no_agent cron script KHÔNG kế thừa biến từ `$HERMES_HOME/.env`** (verified 2026-08-21 với `device-locks-watchdog`): `.env` chỉ được load bởi process gateway, không export ra child → `os.environ.get("TELEGRAM_BOT_TOKEN")` trả None khi script chạy qua cron dù .env có token. Script tự gửi Telegram qua Bot API phải TỰ parse file `.env` (fallback đọc file, giống như đọc config.yaml) — `watch_device_locks.py` chỉ check os.environ + config.yaml keys `telegram.bot_token`/`telegram_token` (không tồn tại) → in `TELEGRAM_BOT_TOKEN not found, outputting to console only:` rồi bỏ qua self-send.
- **Dòng `TELEGRAM_BOT_TOKEN not found` = tạp âm VÔ HẠI khi cron job có `deliver: telegram:<chat_id>`** — no_agent deliver stdout verbatim nên báo cáo vẫn tới nơi; KHÔNG phải watchdog hỏng, đừng hoảng. Chẩn đoán nhanh: `cronjob list` xem job có `deliver` đúng chat không + đọc script có fallback .env không.
- **Tránh gửi trùng**: chọn 1 kênh — HOẶC script tự send qua Bot API (bỏ cron deliver), HOẶC dựa vào cron `deliver` (bỏ phần self-send trong script, stdout chỉ để log local). Cả hai cùng lúc = 2 tin cho 1 lần chạy (script send + cron deliver stdout).

## Coordination pitfall (user preference, 2026-08-08)

Background-process notifications from unrelated farm jobs (e.g. tiktok_workflow workers) land in whatever chat is open. When the user is mid-topic on something else (like gateway setup): **report the worker status in 2–3 lines, do NOT launch into multi-step recovery**, and ask before retrying machines. The user explicitly pushed back on a hijacked conversation.

## Group chat (Telegram) gotchas

- BotFather **privacy mode ON** mặc định → bot chỉ thấy `/command`, reply vào tin bot, service messages.
- Tắt: BotFather → `/mybots` → Bot Settings → **Group Privacy → Off** (⚠️ Lưu ý: Trong BotFather có 2 mục dễ nhầm: `Edit Bot -> Privacy Policy` là đường link web, còn tắt chặn tin nhắn nhóm nằm ở `Bot Settings -> Group Privacy -> Turn off/Disable`).
- ⚠️ **BẮT BUỘC xoá + thêm lại bot vào group sau khi tắt Privacy:** Telegram cache quyền/privacy state lúc bot join nhóm. Nếu chỉ đổi cài đặt trên BotFather mà không kick bot ra add lại (hoặc cấp quyền Admin), Telegram vẫn chặn tin nhắn thường và bot sẽ "đơ" không phản hồi `alo`, `.`.
- Hoặc: promote bot làm group admin (luôn nhận mọi message, không cần đổi privacy).
- **Tắt hộp thoại xác nhận `/new` (destructive_slash_confirm)**: Mặc định Hermes hỏi xác nhận khi gõ `/new` trên Telegram (`Confirm /new?`). Tắt vĩnh viễn bằng lệnh: `hermes config set approvals.destructive_slash_confirm false`.
- **Cho phép bot nhận tin từ bot khác / automation scripts (`TELEGRAM_ALLOW_BOTS`)**:
  - Mặc định Hermes chặn tin nhắn từ sender là Bot (`is_bot=True`) qua `gateway/authz_mixin.py` để chống lặp vô hạn.
  - Khi cần Hermes bot trong group tự động tiếp nhận và xử lý alert bắn từ script qua Telegram Bot API token, bắt buộc thêm vào `$HERMES_HOME/.env`:
    ```bash
    TELEGRAM_ALLOW_BOTS=all
    ```
- Chỉ trả lời khi được gọi + observe context:
  ```yaml
  gateway:
    platforms:
      telegram:
        allowed_chats: ["-100xxx"]
        group_allowed_chats: ["-100xxx"]
        require_mention: true
        observe_unmentioned_group_messages: true
  ```
  Env tương đương: `TELEGRAM_ALLOWED_CHATS`, `TELEGRAM_GROUP_ALLOWED_CHATS`, `TELEGRAM_OBSERVE_UNMENTIONED_GROUP_MESSAGES`. Unmentioned messages chỉ append làm observed context, không dispatch agent.
- **Tự động bắt mọi tin nhắn không cần @mention trong group (Group Free-Response / require_mention: false)**:
  - Mặc định Telegram adapter của Hermes yêu cầu `@mention` hoặc reply (`require_mention: true`). Slash commands như `/new@bot` hay `/model@bot` vẫn chạy do chứa `@botname`, nhưng tin nhắn văn bản thường (`alo`, `.`...) sẽ bị Hermes âm thầm bỏ qua.
  - Để bot tự do trả lời mọi tin nhắn trong mọi nhóm mà không cần tag tên (giống bot Taadaa Sever):
    1. **BotFather**: `/mybots` → chọn bot → `Bot Settings` → `Group Privacy` → **Turn off** (tránh nhầm với link `Privacy Policy` trong `Edit Bot`). Kích bot ra và add lại vào nhóm 1 lần.
    2. **Hermes Config**: `hermes config set gateway.platforms.telegram.require_mention false` rồi `hermes gateway restart`.
  - Trong group chuyên trách (vd Farm Alerts), có thể kết hợp `require_mention: false` và `group_allowed_chats: ["-5373649734"]`.

## Telegram model default vs session model

When the user asks for the model command **in Telegram**, answer with the gateway slash command rather than the desktop/CLI picker:

- `/model` opens the Telegram inline model picker.
- `/model --global` opens the picker and makes the selected model/provider the persistent global default.
- `/model <model> --global` sets a persistent default directly, for example `/model gpt-5.6-luna --global`.
- `/model <model> --provider <provider> --global` explicitly sets both, for example `/model gpt-5.6-luna --provider 9router --global`.
- `/model <model> --session` intentionally affects only the current Telegram session.

## Fallback Providers (OmniRoute Direct Fallback)

- Khi model chính lỗi (`ag-gemini-pool-3` via `omni`), Hermes chuyển model theo `fallback_providers`.
- **Quy tắc user chốt 2026-09-04:** Bỏ qua 9Router, fallback thẳng qua OmniRoute (`omni-free via omni`).
- Cấu hình chuẩn `config.yaml`: `fallback_providers: [{model: omni-free, provider: omni}]`.
- BẮT BUỘC đồng bộ template: `D:\Taadaa\AI-Tools\config\hermes\hermes_config_template.yaml`.
- Lệnh kiểm tra: `hermes fallback list` (lưu ý: `hermes fallback remove` interactive hủy trên pipe non-TTY, dùng script `load_config`/`save_config` hoặc patch).
- Chi tiết: `references/omniroute-hermes-fallback-chain.md`.

Important: `model.persist_switch_by_default: false` makes plain `/model <model>` session-only; use `--global` explicitly. A global switch writes `config.yaml`, so new Telegram sessions use it. If the gateway does not reflect the changed default immediately, restart it from an external shell only when safe; do not restart during a live farm batch. For a Telegram-specific question, do not lead with `hermes model` (that is the local CLI menu); mention it only as an alternative if relevant.

## Global rule & /personality

**Rule chung cho MỌI chat không override** (group mới tự nạp, không cần đụng tay): `agent.system_prompt`. Đổi nhanh không restart = `/personality`:
```yaml
agent:
  personalities:
    van_hanh_mac_dinh:           # /personality <tên>
      description: "..."
      system_prompt: "..."       # ghi config.yaml + áp in-memory ngay lượt sau
```
`/personality` (liệt kê) · `/personality <tên>` (đổi) · `/personality none` (xóa). Nhóm có override thắng global → `/personality` không đổi được rule của chúng.

## Verify round-trip

1. `hermes gateway status` / `hermes gateway list` — process running.
2. Log `$HERMES_HOME/logs/gateway.log`: `[Telegram] Connected to Telegram (polling mode)` + `✓ telegram connected` + `set_my_commands OK (52 cmds)`. Khi user nhắn: `Ignoring /start platform ping for session agent:main:telegram:dm:<user_id>` → session đã tạo (user_id phải khớp `TELEGRAM_ALLOWED_USERS`).
3. User nhắn `/start` + `/model` trên điện thoại → có reply = round-trip hoàn chỉnh.

## Telegram Network Resilience & Fallback IPs (api.telegram.org)

- **Cơ chế tự phục hồi (TelegramFallbackTransport):** Hermes tích hợp sẵn transport fallback trong `plugins/platforms/telegram/telegram_network.py`. Khi kết nối trực tiếp tới `api.telegram.org` bị ISP bóp/nghẽn gói, Hermes tự query DoH (Google/Cloudflare) và chuyển sang Sticky Fallback IP (seed IPs: `149.154.166.110`, `149.154.167.220`) trong khi vẫn giữ nguyên header TLS/SNI `api.telegram.org`.
- **Dòng log cảnh báo:** `Primary api.telegram.org path unreachable; using sticky fallback IP 149.154.166.110` là trạng thái fallback tự động bình thường của gateway, không làm gián đoạn bot.
- **Hiện tượng cả Fallback IP bị nghẽn (Double Stall):**
  - Khi ISP drop gói gắt gao trên toàn bộ dải IP Telegram, log sẽ xuất hiện:
    `Sticky fallback IP 149.154.166.110 failed; resetting to primary DNS path`
    `Fallback IP 149.154.166.110 failed: Timed out`
  - Hậu quả: Long-poll socket bị treo ngầm, OmniRoute trống request 2–5 phút cho tới khi heartbeat timeout reset socket và kéo dồn (`Flushing text batch`).
- **Bản chất nghẽn ISP & Đa tuyến (Multi-ISP Redundancy FPT vs Viettel):**
  - FPT và Viettel sở hữu các tuyến cáp biển/đất liền và cổng định tuyến (transit/peering) quốc tế độc lập tới Telegram DC5 (Singapore). Khi Direct FPT bị nghẽn ngầm hoặc drop persistent TCP socket, proxy qua line Viettel (hoặc ngược lại) đóng vai trò đường thoát hiểm hiệu quả dù cùng là mạng VN.
- **3 Cấp độ xử lý nghẽn Telegram triệt để:**
  1. **Tầng Router (MikroTik L3/L4 Mangle - Tối ưu nhất):** Định tuyến riêng dải IP Telegram (`149.154.160.0/20`, `91.108.4.0/22`) ưu tiên WAN Viettel, failover FPT. Chuyển tuyến tức thì (~2-3s), tầng Python không bị kẹt socket, không cần sửa code app.
  - **Tùy chọn tối ưu:**
    1. **Proxy riêng:** Thêm `TELEGRAM_PROXY=http://<PROXY_USER>:<PROXY_PASS>@<PROXY_HOST>:<PROXY_PORT>` (hoặc SOCKS5/HTTP proxy khác) vào `$HERMES_HOME/.env`.
       - *URL Encoding cho Auth:* Ký tự `@` trong username/password (vd `admin@1` thành `admin%401`) BẮT BUỘC phải URL-encode thành `%40` để `httpx`/`urllib3` không parse sai host dẫn đến lỗi HTTP 407.
       - *Dùng chung port proxy với Phone Farm:* Telegram bot chỉ gửi vài KB JSON long-poll, hoàn toàn không ảnh hưởng tải hay IP farm. Tuy nhiên, port proxy được chọn **BẮT BUỘC phải là port IP tĩnh/cố định, KHÔNG bị script farm reconnect đổi IP xoay vòng** (nếu đổi IP, persistent socket của Telegram sẽ bị đứt và phải reconnect lại).
       - *Pre-flight Probe Commands (chạy trước khi commit config):*
         ```bash
         # 1. Test HTTP CONNECT tunnel (trả về 200 Connection established)
         curl -s -I -x "http://<PROXY_USER>:<PROXY_PASS>@<PROXY_HOST>:<PROXY_PORT>" https://api.telegram.org/
         # 2. Test Egress IP WAN
         curl -s -m 10 -x "http://<PROXY_USER>:<PROXY_PASS>@<PROXY_HOST>:<PROXY_PORT>" https://api.ipify.org
         # 3. Test trực tiếp bằng httpx stack của Hermes (trả về status 302/404)
         python -c "import httpx; r = httpx.get('https://api.telegram.org/', proxy='http://<PROXY_USER>:<PROXY_PASS>@<PROXY_HOST>:<PROXY_PORT>', timeout=15); print('httpx status:', r.status_code)"
         ```
    2. **Đổi DNS host (Tách biệt DNS và Routing):** Lỗi `[Errno 11001] getaddrinfo failed` là lỗi ở tầng Resolver, không phải L3. Định tuyến MikroTik không sửa được lỗi này nếu DNS máy host vẫn trỏ về gateway FPT bị rớt gói. Đổi DNS Windows sang Google/Cloudflare (`8.8.8.8`, `1.1.1.1`) bằng PowerShell Admin:
       ```powershell
       Set-DnsClientServerAddress -InterfaceAlias "Slot04 x16" -ServerAddresses ("8.8.8.8","1.1.1.1")
       ```
    3. **Định tuyến MikroTik (Dual-WAN Telegram Mangle) — Checklist an toàn Farm:**
       - *Khóa chặt src-address:* Bắt buộc gán `src-address=<IP_PC_Hermes>` trong Mangle rule, tuyệt đối không match toàn dải LAN để tránh kéo nhầm 160 máy S7 (`192.168.110.x`) sang PPPoE khác làm loạn proxy binding và dính checkpoint TikTok.
       - *MSS Clamping:* PPPoE có MTU 1492, phải thêm rule `change-mss` (`clamp-to-pmtu` / 1452) trên forward chain để chống drop gói lớn (PMTUD blackhole) gây silent stall.
       - *FastTrack bypass:* FastTrack bỏ qua Mangle, bắt buộc exclude kết nối Telegram khỏi FastTrack.
- **Phạm vi cô lập (Zero-Impact Invariant):**
  - **S7 phone farm:** Nhận DNS qua DHCP của MikroTik/Aruba, ADB chạy local LAN/USB (`192.168.110.x`) -> hoàn toàn không ảnh hưởng.
  - **GPM:** Điều khiển qua API local `19995`, profile chạy proxy Singbox/MikroTik (remote DNS qua proxy) -> hoàn toàn không ảnh hưởng.
  - **Tailscale:** Chạy card mạng ảo độc lập (`Tailscale Tunnel`) với MagicDNS riêng -> hoàn toàn không ảnh hưởng.

## Pitfalls (merged)

- **Telegram long-poll stall (silent TCP CLOSE-WAIT / update queue buffering) vs OmniRoute zero-traffic:**
  - **Triệu chứng:** Bot Telegram tạm dừng phản hồi 2–5 phút, OmniRoute không nhận được bất kỳ request nào (`storage.sqlite` trống trơn trong khoảng thời gian này). Sau đó bot đột ngột phản hồi dồn dập và OmniRoute nhận một đợt bão request (burst) cùng lúc.
  - **Cơ chế gốc:** Kết nối TCP long-polling giữa thư viện PTB (python-telegram-bot) và `api.telegram.org` bị ngắt ngầm (silent TCP stall / half-open / CLOSE-WAIT). Tin nhắn gửi từ Telegram bị dồn ứ ở server Telegram (`pending_update_count > 0`) mà client local chưa đọc được.
  - **Dấu hiệu log:** Trong `gateway.log` xuất hiện cảnh báo heartbeat:
    `WARNING: [Telegram] Telegram polling heartbeat: N update(s) queued but not consumed (stuck probe 1/2)`
    kèm theo chuỗi `Flushing text batch ...` giải phóng hàng loạt session cùng lúc ngay sau khi socket được thông tắc hoặc timeout reset.
  - **Chẩn đoán & Xử lý:** Đây là nghẽn socket mạng quốc tế tới Telegram, KHÔNG phải do OmniRoute sập hay model bị đơ. Proxy local (MikroTik/Singbox cùng LAN) không giải quyết được vì vẫn chung tuyến cáp ISP.
  - **Tối ưu tốc độ phục hồi (`_polling_heartbeat_loop`):** Mặc định code cũ đặt `HEARTBEAT_INTERVAL = 90s` (probe 2 lần = 180s = 3 phút mới unstick). Đã nâng cấp hỗ trợ cấu hình qua env var với default tối ưu:
    - `HERMES_TELEGRAM_HEARTBEAT_INTERVAL`: Mặc định `30` giây (thay vì `90` giây).
    - `HERMES_TELEGRAM_HEARTBEAT_TIMEOUT`: Mặc định `15.0` giây.
    - Thời gian phát hiện và giật lại kết nối tối đa chỉ mất ~30–60 giây.
  - **Lưu ý đồng bộ mã nguồn:**
    - Repo git: `D:\Taadaa\Hermes` (remote `fork https://github.com/thanhdatbui/hermes-agent.git`, branch `main`).
    - Runtime paths: `%LOCALAPPDATA%\hermes\hermes-agent\plugins\platforms\telegram\adapter.py` và `venv\Lib\site-packages\plugins\platforms\telegram\adapter.py`.
  - **Lưu ý restart & Tác động lên Active Sessions:**
    - Lệnh `hermes gateway restart` bị chặn nếu gọi từ trong session terminal tool (tránh tự kill parent); khi cần chạy thủ công ngoài shell / PowerShell:
      ```powershell
      powershell -Command "$p = (Get-Content '$env:LOCALAPPDATA\hermes\gateway_state.json' | ConvertFrom-Json).pid; if ($p) { Stop-Process -Id $p -Force }; Start-Process pythonw -ArgumentList '-m hermes_cli.main gateway run' -WindowStyle Hidden"
      ```
    - **Tác động khi restart:** Lịch sử chat/transcript trong SQLite (`state.db`) được bảo toàn nguyên vẹn. Tuy nhiên, MỌI turn đang suy nghĩ dở, subagents đang chạy ngầm, script terminal hoặc batch tool-calling đang thực thi sẽ bị kill ngang (thành orphan process) và session sẽ dừng lại, không tự động chạy tiếp nếu user không gửi tin nhắn mới kích hoạt.
    - **Quy tắc an toàn & Tự động Restart khi Idle:** Tuyệt đối KHÔNG restart Gateway trực tiếp từ trong session (bị chặn bởi `_HERMES_GATEWAY=1`) hoặc khi có session AI đang chạy. Khi cần reload cấu hình (.env, proxy...) mà không gián đoạn bot, dùng **ONE-SHOT Idle Watcher** (`restart-when-idle.ps1` đọc `%LOCALAPPDATA%\hermes\gateway_state.json`). Watcher kiểm tra `active_agents == 0` liên tục trong 16 giây rồi mới tự động restart và thoát ngay, đảm bảo không có turn AI nào bị ngắt dở và 100% không đụng tới các batch farm chạy bằng `python.exe`. Chi tiết: `references/safe-idle-gateway-restart.md`.
- **Telegram `/model` quick-select buttons freeze (missing `mq:` callback prefix):** Khi bấm các nút model nhanh ở hàng trên cùng của menu `/model` (Gemini 3.7 Flash, GPT-5.6 Luna, Plan Review...), callback data có prefix `mq:<model>:<provider>`. Trong `plugins/platforms/telegram/adapter.py`, hàm `_handle_callback_query` phải chứa `"mq:"` trong tuple kiểm tra `data.startswith(("mp:", "mpg:", "mpv:", "mm:", "mc:", "mb", "mx", "mg:", "mq:"))` để chuyển tiếp vào `_handle_model_picker_callback`, nếu thiếu bot sẽ âm thầm bỏ qua callback và giao diện đơ không set config.
- **Chẩn đoán bot "đơ / nghi sập gateway" do turn latency cao vs crash thật:**
  - Kiểm tra sống/chết tiến trình trước: `hermes gateway status` và `gateway-exit-diag.log` để xác nhận PID có bị restart không (tránh kết luận ẩu "gateway vừa sập").
  - Kiểm tra `gateway.log` và `agent.log` tìm các session có context phình to (>150k tokens trên GPT/Gemini) hoặc chuỗi tool call blocking (ADB/Playwright 40-60s/lệnh): các turn này có thể mất 300-600s (`time=400s+`) mới trả tin nhắn, khiến người dùng tưởng bot chết.
  - Phân biệt với `session_reset`: dòng `Invalidated run generation for ... (session_reset)` xuất hiện khi người dùng gửi `/new` hoặc session bị reset giữa chừng làm hủy generation cũ.
- **Session bị ngắt giữa chừng ("gateway shut down" / "Operation interrupted" lặp lại):** nghi watchdog/health-guard NGOÀI Hermes trước khi đổ lỗi mạng. Gateway chạy `pythonw.exe -m hermes_cli.main gateway run` — windowless (tên process = **pythonw.exe**, KHÔNG phải python.exe) + subcommand **`gateway run`** (KHÔNG phải `serve`). Bên thứ 3 health-check (vd `GanProxyWatcherTray` → log `D:\CodexRuntime\codex_gmail_debug-gan-proxy\hermes-health.log`) mà snapshot sai tên process hoặc sai pattern → false-negative → `hermes.exe gateway restart` mỗi 10 phút → giết session đang chạy. Chẩn đoán: `tail hermes-health.log` tìm `HERMES_RESTART_ATTEMPT` lặp theo nhịp 10 phút + `wmic process where "Name='pythonw.exe'" get CommandLine` đối chiếu pattern. Cách fix guard: xem `android-proxy-watcher` §Tray crash + Hermes guard fixes (2026-08-11).
- **Lỗi Cron exit code 3221226091 (`0xC000026B` / `STATUS_DLL_INIT_FAILED_LOGOFF`):** Xảy ra khi một script no_agent đang chạy thì tiến trình cha (Hermes Gateway) bị restart / reload đột ngột khiến Windows kill ngang tiến trình con. Khi Gateway vừa lên lại sẽ nhận exit code lỗi này từ run trước đó. Cách chẩn đoán: kiểm tra `gateway.log` mốc thời gian "Starting Hermes Gateway..." và chạy thử trực tiếp script bằng target python để xác nhận script exit 0 bình thường.
- **MEDIA:/path attachments do GATEWAY process (host) gửi**, không phải trong container → terminal backend docker: path phải host-visible, mount qua `terminal.docker_volumes`, emit `MEDIA:/home/user/.hermes/cache/documents/...`.
- Token `[SILENT]` / `NO_REPLY` = agent giữ turn trong transcript nhưng không gửi gì ra chat; failed turns vẫn surface lỗi.
- Docs: `/docs/user-guide/gateway` → 404. Vào hermes-agent.nousresearch.com/docs → sidebar **"Messaging Platforms"**.
- Bot riêng cho từng project, không dùng chung token bot khác.
- Nhiều platform cùng lúc OK — thêm token từng platform rồi `hermes gateway restart`. ⚠️ `/new` KHÔNG restart gateway: config đọc 1 lần lúc khởi động; sửa config → bắt buộc restart (restart = ngắt agent đang chạy — chờ batch xong).
- Nâng cấp bot (optional): `/setcommands`; `status_indicator: true` dưới `gateway.platforms.telegram.extra` (mặc định off); `command_menu.max_commands` cap 60 (clamp 1..100).

## Báo cáo user & Chống hiện tượng phản hồi 2 lần (Double-Reply)

- KHÔNG gửi từng bước / tool output trung gian — các lượt trung gian dùng token `[SILENT]`; chỉ 1 báo cáo cuối (kết quả từng máy, thời gian, file log) hoặc lỗi cần xử lý.
- **Hiện tượng trả lời 2 lần liên tiếp (Double-Reply / Queued follow-up):**
  - **Cơ chế:** Khi agent gửi tin nhắn phản hồi ở turn dispatch (vd: "Đã nhận lệnh, đang điều phối worker..."), và ngay sau đó hoặc một thời gian ngắn một async subagent hoàn tất (`[ASYNC DELEGATION BATCH COMPLETE]`) hoặc gateway có `Queued follow-up for session ...`, gateway sẽ tự động kích hoạt turn tiếp theo và render thêm một tin nhắn nữa. Kết quả: User thấy 2 tin nhắn phản hồi nối tiếp nhau trên Telegram.
  - **Kỷ luật bất biến:** Khi dispatch worker background cho một tác vụ chạy ngầm, Coordinator BẮT BUỘC trả lời cực kỳ ngắn gọn (1 câu xác nhận duy nhất) hoặc emit `[SILENT]` nếu không có câu hỏi cần giải đáp ngay, giữ báo cáo đầy đủ cho turn sau khi worker hoàn thành. Tuyệt đối không viết 2 báo cáo tổng kết trùng lặp ngữ cảnh ở cả 2 turn.
- Ảnh màn hình máy N: `adb -s <serial> exec-out screencap -p` (serial từ `config-machine-N.yaml` / workbook mapping), KHÔNG cần mở app mirror. Không tìm được serial → báo rõ, không đoán.
- VPS không thay được máy LAN (ADB USB bắt buộc cùng LAN); VPS chỉ làm não (terminal backend ssh / adb -H relay).

## Platform comparison

`references/platforms-comparison.md` — matrix voice/images/files/threads/reactions/typing/streaming ~28 platform + khuyến nghị (Telegram #1; Discord #2; WhatsApp rủi ro lock; SMS trả phí; Email cho alert).
Chi tiết gắn group↔repo (lấy chat_id, prompt chuẩn, verify state.db): `references/channel-overrides-repo-binding.md` + `references/channel-repo-binding.md`.

## Vision routing via 9Router

- **Native multimodal (Gemini / Claude / GPT-4o / GPT-5.6-luna on 9Router):** Set `agent.image_input_mode=native` and delete/clear `auxiliary.vision`. Hermes attaches image pixels directly in `/v1/chat/completions` payload to 9Router. This fixes the common pitfall where `vision_analyze` returns 401/403 (missing auth header/stale key) and prevents the model from hallucinations/misreading screenshots.
- **Text-only main model (DeepSeek V4):** Use `auxiliary.vision` + `agent.image_input_mode=text`.
- Full setup details in `references/vision-routing-9router.md`.

## Telegram formatting & one-touch command copy (Mobile UX)

- **User preference for commands / prompts on Telegram:** When sending commands or prompts meant for the user to copy and run/send, **NEVER** embed them inside mixed explanation text or multi-line prose.
- **Stand-alone Code Blocks (` ```text `):** Provide commands in dedicated, standalone fenced code blocks without surrounding prose inside the block. On mobile Telegram clients (iOS/Android), standalone code blocks render an explicit 1-tap "Copy" button in the corner, allowing the user to copy only the exact command cleanly without copying the surrounding explanation.

## Runtime core/plugin mismatch recovery (Windows)

Use when Gateway remains alive but a platform disappears after Desktop/restart with `No adapter available for telegram`, an adapter import error, or a missing core symbol.

1. **Scope the repair to the active runtime first.** Identify the live Gateway process command line and its install root. Do not edit the source repository merely because it contains a similarly named adapter; an outage fix belongs under `%LOCALAPPDATA%\\hermes\\hermes-agent` unless the user explicitly asks for a source-code fix.
2. **Preflight before restart.** Enumerate active Hermes/farm processes. If a feed/upload/reg/render batch is running, do not restart Gateway: restart can kill child jobs and watchdogs. Repair files and verify imports/logs in place; defer restart until the farm is idle.
3. **Compare core and plugin as one artifact.** Read the installed Hermes version from runtime metadata, then compare the active plugin with the venv copy under `venv/Lib/site-packages`. Prefer the venv copy only when it is compatible with the installed core. Check both the adapter's private-symbol imports and whether the matching core module provides those symbols. Never print tokens or config values.
4. **Repair the runtime, not the source by default.** Copy the compatible adapter into the active runtime path, remove only related `__pycache__` directories, and verify byte equality/hash plus a cold import using the venv interpreter. A machine reset is not a substitute for repairing mismatched files.
5. **Verify without assuming restart succeeded.** Check `hermes gateway status`, then inspect the newest Gateway startup block. Acceptance evidence: Telegram connected/polling, `✓ telegram connected`, `Gateway running with N platform(s)`, and `set_my_commands OK`; absence of `No adapter available`, the missing-symbol error, and plugin-load failure. A real Telegram round-trip is the final check when safe.
6. **Restart only from an external context when needed.** A Gateway-internal restart may be blocked because it would kill its own parent. Stop/start only after the farm preflight is clear, then repeat status, log, and round-trip verification.

**Reporting style:** concise Vietnamese; state purpose, changed runtime paths, verification evidence, and any restart blocker. Do not bury the result in a long plan or imply the source repository was fixed when only the runtime was repaired.

Session-specific checklists:
- `references/idle-restart-and-session-lifecycle.md` — chi tiết 4 tầng session (_running_agents vs _agent_cache vs session_store vs executor), cơ chế check idle qua gateway_state.json và script PowerShell nền restart an toàn.
- `references/runtime-version-mismatch.md` — recover a live Telegram adapter/core mismatch safely.
- `references/runtime-sync-forensics.md` — identify who actually copied runtime files, distinguish updater trigger from copy mechanism, and avoid blaming OmniRoute/Desktop without evidence.

## Runtime-sync/update forensics

Use this when the user asks “what updated Hermes?” or when a runtime contains mixed core/plugin versions:

1. **Separate three actors:** (a) source checkout/repo, (b) the copy/install mechanism that changed `%LOCALAPPDATA%\\hermes\\hermes-agent`, and (c) the process or session that invoked it. A manifest proves (b), not automatically (c).
2. Inspect `runtime-sync-*` manifests, wheel/artifact path, source root, installed root, timestamps, and `install_command`. Redact tokens and credentials. Treat backup manifests as evidence of file operations, not proof of a scheduled job.
3. Check `hermes-update.log`/`update.log`, Task Scheduler, Startup launchers, Desktop/Gateway logs, process command lines, and Git reflogs around the timestamp. A failed `hermes update` entry that stops at the running-process preflight is not evidence that it installed anything.
4. Do not call a runtime sync “automatic,” “OmniRoute,” or “Desktop self-update” unless a scheduler/launcher/session log proves that trigger. Report confidence explicitly: confirmed copy mechanism, likely trigger, or unresolved trigger.
5. Before any repair, preserve the existing dirty-tree state and do not run `git reset`, `git clean`, broad reinstall, or whole-tree copy. If a user customization may be in the affected file, diff the current file against venv and backups before overwriting it.
6. When a custom runtime sync copied a whole wheel or a broad allowlist from a source checkout, require a pre-install compatibility gate: core/plugin version/artifact identity, import-symbol check, atomic replacement or rollback, and cold-start verification before Gateway restart.

**Reporting style for forensics:** answer the direct question first in concise Vietnamese; distinguish “đã xác định” from “chưa xác định”; name exact paths/timestamps only when backed by manifests/logs; never turn an inferred trigger into a fact.

## See also

- `android-proxy-watcher` — farm VPN/proxy recovery ladder (device-level).
- `9router-proxy-ops` — model provider side of the same stack.
