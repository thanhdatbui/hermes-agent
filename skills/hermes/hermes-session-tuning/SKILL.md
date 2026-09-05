---
name: hermes-session-tuning
description: "Chẩn đoán Hermes session lag (context bloat → compression threshold), tinh chỉnh compression, và kiểm tra/ép reasoning_effort khi route qua 9router (deepseek v4)."
---

# Hermes Session Tuning (lag + reasoning qua 9router)

## Trigger
- User kêu Hermes lag / session chậm dù RAM-CPU vẫn còn thừa
- Cần kiểm tra model deepseek đang chạy reasoning nào (THINK:auto vs high vs max trong 9router console log)
- Muốn ép reasoning effort chắc chắn qua 9router
- **Session bị reset/đứt ngang 04:00** — banner `◆ Session automatically reset (daily schedule at 4:00). Conversation history cleared. Use /resume to browse and restore a previous session.` (live 2026-08-12 Tiktok Reg group)

## 0. Session reset 4:00 tự động — config `session_reset` (live 2026-08-12)
- `session_reset.mode: both` (mặc định setup wizard) = reset theo CẢ 2: `idle_minutes: 1440` (24h idle) VÀ `at_hour: 4` (reset toàn bộ 04:00 hằng ngày). Hệ quả: mọi group/thread bị gom về session mới lúc 4h sáng, mất context, log `sessions` có `end_reason='session_reset'`.
- **Tắt hẳn**: `hermes config set session_reset.mode none` → config.yaml `session_reset: {mode: none}`. (Chế độ khác: `idle` chỉ idle, `daily` chỉ theo giờ.)
- **Phải restart gateway mới áp dụng** — và `hermes gateway restart` chạy TRONG gateway bị block ("cannot restart ... from inside the gateway process"). Restart từ shell ngoài (desktop terminal / login item) hoặc chờ lần khởi động sau.
- Sau khi bị reset, session cũ vẫn còn trong DB (`hermes sessions list` / `/sessions`) — khôi phục bằng `/resume <session_id>` ngay trong group đó hoặc resume qua routing. Session bị reset có `expiry_finalized=true` trong `gateway_routing` state.db nhưng messages vẫn đọc được.
- Không nhầm cơ chế này với compression fail loop (mục 1b) — đây là reset CHỦ ĐỘNG có banner, không phải nén treo.

## 0b. Session dài nhiều ngày → /new-safe nhờ repo-resident state (session-start context rule, live 2026-08-16/17)

User chạy session vài ngày (fix debug/build script). Session dài = lag (avg 193K token/call, 17s/turn) + đốt quota; `/new` là fix nhưng mất "mạch suy nghĩ" trong đầu agent. Nguyên tắc: **trạng thái công việc phải nằm trong repo (plan + git), không nằm trong đầu agent** → /new lúc nào cũng an toàn, session mới tự định hướng.

### 1. Quy tắc SESSION-START-CONTEXT (chống phình context)
Đã phủ vào **toàn bộ 30/30 file `AGENTS.md`** dưới `D:\Taadaa` (cả root, repo con, và worktree). Nội dung rule chống phình: session mới (vừa /new, resume, đổi máy) TRƯỚC khi hỏi/làm gì phải chạy đúng 4 bước:
1. Đọc `AGENTS.md`. Nếu có `HANDOFF.md`, **CHỈ đọc phần `Current State / Blockers / Next Task`** — nếu file >20KB thì không nạp toàn bộ lịch sử.
2. Tìm trong `.hermes/plans/`: **CHỈ đọc đúng 1 file `.md` mới nhất theo timestamp**. Không đọc cả thư mục plans.
3. Kiểm tra git: `git status --short` + `git log --oneline -5`.
4. Báo cáo "Task đang dở / bước kế tiếp / trạng thái git" rồi **HỎI xác nhận** — CẤM tự đoán task tự làm tiếp.

AGENTS.md discovery (verify từ source): first-match-wins `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`; **AGENTS.md chỉ đọc ở đúng cwd, không walk parent/child** → đặt rule file đúng thư mục session khởi chạy (vd `cd D:\Taadaa\automation-core`).

**Verify injection = spawn session mới, không tin docs:** `cd <repo> && hermes chat -q "Bạn có thấy quy tắc Session-start context trong AGENTS.md không? Nêu 2 việc đầu tiên phải làm"` — session FRESH trả lời đúng nội dung + kèm số dòng (đã chạy thật: session `20260816_002655_5a384f`, trả về đúng block dòng 14-25) = chứng minh rule đã vào system prompt.

### 2. Auto-trim watchdog định kỳ (chống tái phát phình startup files)
- Vấn đề: `HANDOFF.md` và `PROJECT_RULES.md` hay phình lại sau vài ngày (vd `Tiktok_Reg/HANDOFF.md` từ 141 phình lên 534 dòng). Tổng startup files toàn workspace từng lên tới ~1.1MB.
- Giải pháp: Script `~/AppData/Local/hermes/scripts/auto_trim_startup_files.py`
  - `HANDOFF.md` / `handoff.md` > 200 dòng: cắt phần giữa (debug log cũ), giữ top 130 + bottom 60 dòng (current state + invariants).
  - `AGENTS.md` / `PROJECT_RULES.md` con > 400 dòng: cắt duplicate workspace policy blocks.
  - Tự backup vào `D:/Taadaa/handoff-trim-backups/<timestamp>/` trước khi sửa, giữ nguyên EOL.
  - Watchdog pattern: im lặng khi không có file nào vượt ngưỡng.
- Cron job: `auto-trim-startup-files` (ID: `26f05737495b`), schedule `0 3 * * 0` (hằng tuần Chủ nhật 03:00), `no_agent: true` (không tốn token).

Thứ tự an toàn khi sửa AGENTS.md: backup trước (`cp AGENTS.md AGENTS.md.bak-$(date +%Y%m%d-%H%M%S)`), chèn bằng patch (không byte-append khi block phải nằm đầu file), verify bằng chat -q probe. `D:\Taadaa\AGENTS.md` KHÔNG phải git repo (đã verify `git rev-parse` fail) → backup manual là chứng cứ duy nhất; `automation-core/AGENTS.md` tracked trong git.

## 1. Chẩn đoán lag — KHÔNG phải RAM/CPU, là context token
Thứ tự:
1. Process check: `powershell.exe -NoProfile -Command 'Get-Process | Sort-Object WS -Descending | Select-Object -First 20 Name,Id,CPU,...'` — **bọc toàn bộ lệnh PS trong single-quote**, `$_` bị bash/MSYS nuốt nếu dùng double-quote.
2. Hermes.exe renderer con (`--type=renderer`) + msedgewebview2 = UI Electron (renderer ~800MB với session nặng là bình thường). CPU cao không phải nguyên nhân chính.
3. Grep log per-session: `grep 'conversation_loop: API call' agent.log` → parser python tính `avg_in` mỗi session (xem `references/lag-diagnosis.md`). Session nào `avg_in` ~300K+ tokens/call là thủ phạm.
4. `grep 'Preflight compression'` + `grep 'context compression started/done'` → nén có chạy trễ không.

Nguyên nhân lag chính: **context tokens khổng lồ mỗi API call**. Deepseek ctx 1M + threshold 0.5 → nén chỉ ở ~524K, session chạy cả ngày ở 300-500K/call → latency ~11s/call, bất kể máy mạnh cỡ nào. UI renderer nặng (500+ messages trong DOM) là phụ.

Fix:
- `hermes config set compression.threshold 0.3` — nén sớm (~314K cho ctx 1M), giữ call ~200-250K. Trade-off: nén nhiều lần hơn, mất chi tiết sớm hơn. 0.2 = nhanh nhất nhưng nén liên tục.
- **Config chỉ áp cho session MỚI** — session cũ đã phình phải `/new` mới hết lag.
- Session 500+ messages nên `/new` dù đã nén (UI vẫn nặng).

## 1b. Compression fail loop + threshold vs target_ratio

### Fail loop (nén "liên tục" nhưng không bao giờ xong)
- Triệu chứng UI: `Compressing context (N min elapsed, iteration X/60) — your message is queued`.
- Log: nhiều dòng `context compression started` (messages/tokens tăng dần) mà KHÔNG có `context compression done` nào → compression call fail (timeout qua proxy / fallback chết), session không giảm → chạm ngưỡng → nén lại → loop vô hạn. Đây KHÔNG phải tần suất bình thường của threshold.
- Nguyên nhân thực tế (2026-08-11): 3 session ~330K token nén song song qua cùng 1 9router → proxy nghẽn; log `Auxiliary compression: timeout on the critical path` + `all fallbacks exhausted`. Fallback chết: openrouter payment error (v98store migrated → cheapkeyai.shop), nous chưa auth.
- Probe proxy nhanh: `curl -s -m 8 http://127.0.0.1:20128/v1/models -o /dev/null -w "%{http_code} in %{time_total}s"` — khỏe < 1s; ~5s+ = proxy đang nghẽn (ngay cả endpoint rẻ nhất).
- Fix: `/stop` (hủy vòng nén + trả message queue) → `/new`; không chạy nhiều session nặng song song (cùng renderer + 9router = tải nhân đôi/nhân ba).

### Compression model routing: dùng `auxiliary.compression`, KHÔNG dùng `compression.model`

Source-verified on Hermes 0.18.2:

- `compression.*` controls the **compression lifecycle** (`enabled`, `threshold`,
  `target_ratio`, protected messages). It does **not** select the summarizer model.
- `_get_auxiliary_task_config("compression")` reads
  `config["auxiliary"]["compression"]`; `_resolve_task_provider_model` then applies
  **explicit call args > `auxiliary.compression.{provider,model,...}` > `auto`**.
- `auto` means inherit the active session's main runtime. Log evidence before an override:
  a Sol session compressed through Sol and a Luna session through Luna.
- Correct global override:
  `hermes config set auxiliary.compression.model deepseek-v4-flash`
  and `hermes config set auxiliary.compression.provider custom:9router`.
  The older-looking commands `hermes config set compression.model ...` /
  `compression.provider ...` merely add inert keys to the lifecycle block; do not claim
  success from YAML parsing alone.
- `_get_auxiliary_task_config()` loads config at the auxiliary call, so the corrected route
  applies to the **next compression attempt**, including existing sessions; `/new` is not
  required just to change the compression model. Verify from the next
  `agent.auxiliary_client: Auxiliary compression: using ...` log line.
- `delegation.model` is separate: it selects future `delegate_task` children, not the
  compression model.
- Do not attribute all Sol/Luna usage to compression from provider totals. Correlate actual
  `context compression started/done` and `Auxiliary compression: using ...` events with
  request timestamps; normal coordinator/audit traffic shares the same provider totals.
- Feasibility gate (`conversation_compression.py`): the auxiliary compression model context
  must fit the main model's compression payload/threshold; check this before pinning a
  smaller-context summarizer.
  - **Triệu chứng warning auto-lowered**: `⚠ Compression model <model> context is N tokens, but the main model <main>'s compression threshold was M tokens. Auto-lowered this session's threshold to N tokens so compression can run.`
  - **Xử lý nhanh**: Đổi model nén sang model context 1M (vd: `ag-gemini-pool-3` trên `omni` hoặc `ag/gemini-3.7-flash-high` trên `9router`):
    `hermes config set auxiliary.compression.model ag-gemini-pool-3`
    `hermes config set auxiliary.compression.provider omni`
- **Cấu hình `auxiliary.compression.fallback_chain` an toàn**:
  Khi model nén chính lỗi hoặc hết quota, Hermes duyệt qua danh sách `fallback_chain`. Bắt buộc kiểm tra provider trong chain có credential hợp lệ. Nếu 9Router không còn active token cho model Antigravity (dẫn đến `401 No active credentials for provider: antigravity`), phải trỏ fallback sang combo free nội bộ trên OmniRoute (`model: omni-free`, `provider: omni`) để đảm bảo không bị loop treo nén `all fallbacks exhausted`.

### Quota burn = context bloat, not model price (diagnosis pattern)

- "Flash still burns quota" → check usageHistory: 2,033 flash req/day × avg 195K prompt
  tokens = 396M tokens/day; 49% of requests 200-400K, 45% 100-200K. Model is cheap; the
  VOLUME of tokens per call is the burn. Fix = shorter sessions (/new), lower threshold,
  route compression to cheap model.
- `grep -h 'context compression started' agent.log` reveals which model compresses each
  session — that single grep exposes the compression cost driver.

### threshold (KHI nén) ≠ target_ratio (nén về bao nhiêu)
- `compression.threshold 0.3` (ctx 1M → nén ở ~300K) quyết định **tần suất**.
- `compression.target_ratio 0.2` quyết định **post-nén nhỏ cỡ nào** (~60-90K thực tế, log `317K→79K`). Đây là tham số giữ cho model đọc được — KHÔNG phải threshold.
- Ràng buộc "codex đọc được context" → target_ratio lo (post-nén ~80K << codex 272K).

### VÌ SAO threshold = 0.3 — CẤM nâng lên 0.45 (user phản biện đúng 2026-08-11)
- Worker/delegation chạy **gpt-5.6 (ctx 372K)**: context vượt ~372K (tới ~400K) là gpt **"ngọng"/lỗi ngay**, không chờ nén kịp. `threshold 0.3` trên ctx 1M = nén ở ~300K → LUÔN nén TRƯỚC khi vượt 372K → gpt worker không bao giờ thấy >372K.
- Nâng lên 0.45 (nén ở 450K) = **tự sát**: context chạm 372K+ TRƯỚC khi nén chạy → gpt ngọng mẹ → chính là nguồn lỗi/treo. Đây KHÔNG phải lựa chọn tần suất — là ranh giới cứng của model worker.
- Muốn nén ít hơn: KHÔNG đụng threshold; chỉ có thể tăng target_ratio (post-nén to hơn) hoặc giảm tải tool output — nhưng giữ post-nén < 272K cho codex.
- Context windows (nguồn `~/.codex/cockpit-local-access-model-catalog.json`, field `context_window`): gpt-5.6-luna/terra/sol = **372K**; gpt-5.3-codex = **272K**; gpt-5.3-codex-spark = 128K; gpt-5.4/5.5 = 272K. User thường nhớ nhầm "257K" — con số thật là 272K.

## 2. Reasoning effort qua 9router (deepseek v4)
- Hermes config: `agent.reasoning_effort: max` → resolve thành `{'enabled': True, 'effort': 'max'}`. DeepSeek V4 chỉ chấp nhận **low/high/max** (`DEEPSEEK_V4_REASONING_EFFORTS`); "medium" bị reject → provider default.
- Wire: transport gửi `extra_body.reasoning={"enabled":true,"effort":"max"}` khi `_supports_reasoning_extra_body()` true = custom:9router + localhost:20128 + model `cmc/deepseek/*` (các custom endpoint khác KHÔNG gửi reasoning).
- 9router console log `THINK:X` đọc từ body sau translate, ưu tiên: `output_config.effort` → `thinking` → `reasoning_effort`/`reasoning.effort` → `thinkingConfig` → `enable_thinking`.
- **Cách ép chắc chắn 100%: đổi tên model kèm suffix** — `cmc/deepseek/deepseek-v4-flash(max)` hoặc `(high)`. 9router parse suffix làm override cứng `{mode:"level"}`; `(auto)`→auto; `(none|off)`→tắt; `(1234)`→budget tokens. Không suffix → đọc body, body không có gì → provider default (auto).
- **THINK:auto trong log DÙ config max** — nguyên nhân: (a) request chạy trước khi đổi config (reasoning_config resolve lúc session init → cần /new hoặc /model), (b) fallback gemini (`fallback_providers: gemini/gemini-3.6-flash` qua cùng 9router, `reasoning_overrides: high`), (c) Hermes version đang chạy khác code trên disk.
- Verify nhanh: `curl -s POST http://127.0.0.1:20128/v1/chat/completions -d '{"model":"cmc/deepseek/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'` — nhưng nguồn thật là console log 9router (cần auth, `/login`).

## Pitfalls
- PowerShell qua bash: `powershell.exe -NoProfile -Command '...'` — single-quote toàn bộ, `$_`/`$()` bị MSYS nuốt → ParserError.
- 9router bundle minified (`app/.next-cli-build/server/chunks/*.js`) — grep multi-line fail; đọc bằng python `open(..., errors='replace')` + `re.finditer`.
- `hermes config set KEY VAL` là đường chuẩn — AGENTS.md cấm hand-edit config.yaml.
- Máy này HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes` (config.yaml, logs, source), KHÔNG phải `~/.hermes`. Log: `logs/{agent,errors,desktop,gui}.log`.
- 9router hay có bản mới: check banner dashboard (vd v0.5.45 → v0.5.50).

## Log forensics (`~/AppData/Local/hermes/logs/agent.log`, agent.log.1, …)

Parse with Python regex:
- Per-session API stats: `agent.conversation_loop: API call #N: ... in=<tokens> out=... latency=<s>s` — aggregate avg_in, avg_latency, max_latency per session id.
- **Regex thực tế đã chạy được (2026-08-07)**: `API call #(\d+):.*?in=(\d+) out=(\d+) total=(\d+) latency=([\d.]+)s` — format đầy đủ: `API call #15: model=cmc/deepseek/deepseek-v4-flash provider=custom in=237237 out=578 total=237815 latency=12.5s`. Pattern `in=[0-9]+.*latency=[0-9.]+s` cũng OK nếu chỉ cần 2 field.
- `agent.turn_context: conversation turn: session=<id> ... history=<n>` — message count.
- `agent.turn_context: Preflight compression: ~N tokens >= threshold` — compression trigger.
- `agent.conversation_compression: context compression started/done` — messages N->M, rough_tokens. A compression run blocks the session ~1-2 min (visible "lag spike").

Rule of thumb from real data: avg_in > ~250-300K tokens/call ⇒ multi-second+ latency; 700+ messages ⇒ UI jank; a session at 500K+ tokens pre-compression is the laggy one.

## Direct state.db Query for Session Activity Stats (2026-09-05)

Khi cần thống kê nhanh số user requests, active sessions, delegation counts trong 1 khoảng thời gian — query trực tiếp `C:/Users/Kibe/AppData/Local/hermes/state.db` bằng Python sqlite3. Nhanh hơn và chính xác hơn grep log.

### Quick template
```python
import sqlite3, datetime, os
from pathlib import Path

now = datetime.datetime.now()  # UTC+7
one_hour_ago = now - datetime.timedelta(hours=1)
now_ts, ago_ts = now.timestamp(), one_hour_ago.timestamp()

db_path = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Kibe\AppData\Local")) / "hermes" / "state.db"
# Mở ở chế độ read-only (uri=True) với timeout 10s tránh lock contention với Gateway
conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10)
cur = conn.cursor()

# User messages in window
cur.execute('SELECT COUNT(*) FROM messages WHERE role="user" AND timestamp>=? AND timestamp<?', (ago_ts, now_ts))
print(f'User msgs: {cur.fetchone()[0]}')

# Active sessions
cur.execute('SELECT DISTINCT session_id FROM messages WHERE timestamp>=? AND timestamp<?', (ago_ts, now_ts))
sessions = [r[0] for r in cur.fetchall()]
print(f'Active sessions: {len(sessions)}')

# Delegations dispatched
cur.execute('SELECT COUNT(*) FROM async_delegations WHERE dispatched_at>=? AND dispatched_at<?', (ago_ts, now_ts))
print(f'Delegations: {cur.fetchone()[0]}')

# Per-session breakdown
for sid in sessions:
    cur.execute('SELECT role, COUNT(*) FROM messages WHERE session_id=? AND timestamp>=? AND timestamp<? GROUP BY role', (sid, ago_ts, now_ts))
    rc = {r[0]: r[1] for r in cur.fetchall()}
    cur.execute('SELECT title FROM sessions WHERE id=?', (sid,))
    title = (cur.fetchone() or ['N/A'])[0] or 'N/A'
    print(f'  {sid}: user={rc.get("user",0)} asst={rc.get("assistant",0)} tool={rc.get("tool",0)} | {title}')
```

### Key tables
| Table | Key columns | Use |
|---|---|---|
| `messages` | role, timestamp, session_id | User/assistant/tool message counts per window |
| `sessions` | id, title, started_at, api_call_count | Session metadata |
| `async_delegations` | state, dispatched_at, completed_at | Worker dispatch/fail stats |

### Notes
- `timestamp` in messages is Unix epoch (REAL) — use `>=` and `<` for half-open interval
- `role` values: `user`, `assistant`, `tool`, `system`
- High assistant:user ratio (>10:1) = delegation loop / retry storm, not many real users
- Per-session `api_call_count` from sessions table is cumulative (all time), not per-window

## Memory tool ≠ lag driver (user hỏi 2026-08-07 — trả lời kèm số liệu)

User hỏi "dọn memory có giúp lag/tốn quota k". Trả lời verify bằng số liệu thật:
- Memory tool = `~/AppData/Local/hermes/.../memories`, bơm vào system prompt mỗi turn. 2,200 chars ≈ **~600 token ≈ 0.3%** của 1 API call 193K token. Dọn memory giảm quota RẤT NHỎ, không giảm lag.
- **Lag thật = context token bloat**: session 2,659 calls → avg **in=193,200** / max **483,924** tokens/call, latency avg **17.0s** / max **159.6s**, 276 calls >300K. Đây là số liệu chuẩn khi user kêu lag.
- Đừng đề xuất dọn memory như fix lag — fix thật là `/new` session (reset về ~10K/call) + tránh 2 session nặng song song (cùng renderer + 9router → nhân đôi tải).
- Dọn memory vẫn đáng làm: giảm quota nhẹ + focus tốt hơn (entry cũ/ít dùng làm model phân tâm → retry → tốn quota gián tiếp). Nhưng nói rõ với user là không phải fix lag.

## Cross-session interference & Multi-session lag diagnosis

Khi user chat hàng loạt session song song và thấy phản hồi chậm (hỏi "do nghẽn model ở omni hay nghẽn ở gateway"):

### Quy trình chẩn đoán 3 bước tách bạch:
1. **Kiểm tra Model / Proxy (OmniRoute / 9Router):**
   - Không đoán mò proxy nghẽn. Đọc trực tiếp `C:\Users\Kibe\.omniroute\storage.sqlite` (bảng `call_logs`, cột `status, duration, error_summary`) hoặc `curl -s http://127.0.0.1:20129/v1/models`.
   - Nếu `duration` chỉ 2-5s, status 200, pool nhiều account active không 429 → **Không phải nghẽn ở model/omni**.
2. **Kiểm tra Tool execution blocking trong Agent (`agent.log`):**
   - Grep `tool .* completed \([\d\.]+s` trong `agent.log`.
   - Tìm các lệnh `terminal`, `search_files`, `process` chạy foreground tốn 30s - 600s (ADB, pytest, batch sync). Khi agent đang chờ tool hoàn tất, cả turn bị kéo dài (300s - 1900s) dù LLM chỉ mất vài giây.
3. **Kiểm tra Gateway ThreadPool & SQLite lock (`gateway.log`):**
   - Kiểm tra `response ready: platform=... time=...` đối chiếu với số `api_calls`.
   - Tìm `state.db routing save failed: database is locked` (xảy ra khi nhiều session cùng ghi routing/transcript vào SQLite).
   - Kiểm tra mạng Telegram Bot API: tìm cảnh báo `Primary api.telegram.org connection failed ... fallback IPs`.

### Giải pháp khuyến nghị:
- Chuyển các tác vụ dài sang background (`background=true` hoặc cron) thay vì để agent foreground blocking.
- Session cũ context phình to (>150k-200k tokens) cần `/new` để tránh overhead nén & latency.

## References
- `references/lag-diagnosis.md` — lệnh chẩn đoán + parser python per-session stats.
- `references/reasoning-effort-wire-path.md` — source-map file:line đã verify (Hermes + 9router JS) cho toàn bộ đường reasoning.
