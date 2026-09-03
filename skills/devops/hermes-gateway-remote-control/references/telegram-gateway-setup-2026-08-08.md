# Telegram Gateway Setup — worked walkthrough (2026-08-08)

Machine: Kibe Windows, HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes` (profile `default`), gateway v0.18.2.

## Sequence that worked

1. BotFather → `/newbot` → token; @userinfobot → user ID `1076231895`.
2. `.env` already had a COMMENTED template:
   ```
   # TELEGRAM_BOT_TOKEN=...
   # TELEGRAM_ALLOWED_USERS=...   # Comma-separated user IDs
   ```
   User pasted values but left `#` + trailing comment → `awk -F= '/^TELEGRAM_/{print $1"=["length($2)"]"}'` returned nothing (keys still commented). Fix via python: uncomment + `val.split('#')[0].strip()`, preserve CRLF, write back with utf-8-sig. Validated format without printing: token `\d{6,12}:[A-Za-z0-9_\-]{30,40}` (46 chars), users `\d+(,\d+)*` (10 chars).
3. `hermes gateway install --start-on-login --start-now` → UAC prompt auto-declined ("Skipped elevation") → **Startup-folder fallback succeeded**:
   `%APPDATA%\...\Startup\Hermes_Gateway.vbs` + `gateway-service\Hermes_Gateway.cmd`, then direct spawn PID. So no admin needed; but auto-start only at LOGIN.
4. Log evidence of success (logs/gateway.log):
   ```
   [Telegram] Connected to Telegram (polling mode)
   ✓ telegram connected
   [Telegram] set_my_commands OK ... (52 cmds)
   Ignoring /start platform ping for session agent:main:telegram:dm:1076231895
   ```

## The quoted-key bug (the whole "override không chạy" saga)

Group chat_id `-5435853713`. `hermes config set '...channel_overrides."-5435853713".system_prompt' "..."` stored the key as the 9-char string `"-5435853713"` (with quotes) because the dotted-path parser keeps the quotes literally. Lookup uses bare `-5435853713` → no match → system prompt never injected → agent wandered into `C:\Users\Kibe\OmniRoute` and `/d/CodexRuntime` instead of the repo.

Diagnosis path: `yaml.safe_load(config.yaml)` and print `list(channel_overrides.keys())` → saw `['"-5435853713"']`. Fix:
1. Re-set WITHOUT quotes → keys became `['"-5435853713"', '-5435853713']`.
2. Remove the bad key: CLI has no unset → python `del` + `yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)` (newline='\n'), then `hermes config check`.
3. `hermes gateway restart` → `/new` in the group.

Verify the override actually reached the model (not just config): `state.db` → `messages` table, session_id of the fresh session; check the assistant's first reply cd's into the repo. Session id comes from `sessions/sessions.json` entry for `agent:main:telegram:group:<id>:<userid>`.

## Timing rule

- Config change → only effective after restart + `/new` (system prompt pinned at session creation; prompt-caching invariant).
- Restart during a running batch kills the agent mid-task — set config now, restart after the batch finishes, then tell the user to `/new`.
- The user-facing contract: "chờ batch xong → restart → /new → hết loãng".

## Group system_prompt template (repo-bound, working example, 1119 chars)

```
Bạn là Hermes phụ trách repo dự án Tiktok-video (D:\Taadaa\Tiktok-video, nhánh main). Trước MỌI lệnh terminal phải cd /d/Taadaa/Tiktok-video. Tuân theo AGENTS.md + HANDOFF.md + PROJECT_RULES.md trong repo. Lệnh chạy workflow upload: PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" và venv D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe -m tiktok_workflow --config <config-machine-N.yaml> --machine N --no-dry-run (kèm echo YES). Không sửa file ngoài repo, không đọc credential/workbook. QUY TẮC BÁO CÁO: khi chạy batch/lệnh dài, KHÔNG gửi từng bước hay tool output trung gian; các lượt trung gian dùng [SILENT]; chỉ gửi 1 báo cáo tóm tắt cuối cùng (kết quả từng máy, thời gian, file log) khi hoàn tất hoặc khi có lỗi cần xử lý. QUY TẮC ẢNH MÀN HÌNH: khi user yêu cầu ảnh màn hình máy N — tìm serial từ D:\CodexRuntime\tiktok-video\config-machine-N.yaml hoặc workbook mapping (D:\OneDrive\Tiktok\Tik1.xlsx), chụp bằng "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> exec-out screencap -p (save file local rồi gửi qua MEDIA:), KHÔNG cần mở app xiaowei. Nếu không tìm được serial, báo rõ thay vì đoán.
```

## Architecture facts confirmed this session

- Desktop + gateway share 100% of HERMES_HOME; desktop closing does not stop the gateway (separate process). Gateway dies on PC sleep/shutdown and only restarts at Windows LOGIN (Startup folder) — so PC must stay on and logged in for 24/7 remote control; VPS only replaces the "brain", the ADB/LAN machine is still required for the USB phone farm (adb relay via SSH or `adb -H <pc> -P 5037`).
- Phone screenshots remote: `adb exec-out screencap -p` — never need to open the xiaowei mirror app (it is just another consumer of the same adb source). Remote-desktop apps (AnyDesk/RustDesk) are the "see the whole mirror wall from afar" option.
- Session storage: `state.db` + `sessions/sessions.json` + `logs/gateway.log` under HERMES_HOME; auto-compression (0.3) + idle reset (24h, 4h sweep) means no manual pruning.
