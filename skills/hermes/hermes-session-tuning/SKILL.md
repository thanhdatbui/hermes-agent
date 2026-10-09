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
- `hermes config set compression.threshold 0.3` — nén sớm (~314K cho ctx 1M), giữ call ~200-250K. Trade-off: nén nhiều lần hơn, mất chi tiết sớm hơn.
- 🚨 **CẤM TUYỆT ĐỐI HẠ THRESHOLD DƯỚI 0.3 (User Correction 03/10/2026)**: Cấm hạ threshold xuống 0.12 hay 0.2 với lý do "giảm tải proxy". Ở context window 120k tokens, threshold 0.12 sẽ ép nén liên tục ngay từ 14.4k tokens ("120k context thì nén liên tục"), phá vỡ trải nghiệm người dùng. BẮT BUỘC duy trì `compression.threshold: 0.3`.
- **Cơ chế Retry Overload (503) & OmniRoute Recovery**: Khi gặp lỗi 503 Overloaded, `agent/conversation_loop.py` tự động nâng `base_delay = 10.0s`, khóa sàn `Retry-After >= 10s`, và `_emit_status` tức thì để trải dài chuỗi retry ~85s (đủ thời gian cho watchdog OmniRoute tự restart ~24s). Chi tiết xem `references/omniroute-heap-pressure-and-retry-backoff.md`.
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

### Thứ tự ưu tiên resolve context_length & Ngưỡng nén thực tế (Source-verified Hermes 0.18.2):
- **Phân định context_length giữa `model.context_length` và `custom_providers` (`agent_init.py:1676-1723`, `model_metadata.py:2047-2081`)**:
  Hermes đọc `_config_context_length` từ block `model.context_length` trước tiên (bước 0).
  Nếu `model.context_length` đã được set (vd: `1000000`), Hermes DÙNG LUÔN giá trị này và **BỎ QUA HOÀN TOÀN** giá trị `context_length` khai báo trong `custom_providers.<name>.models.<model>.context_length` (nhánh này chỉ chạy khi `_config_context_length is None`).
- **Floor cho model nhỏ (`ContextCompressor._effective_threshold_percent`)**:
  Nếu `context_length < 512.000` (như 200k), Hermes tự động kích hoạt floor nâng ngưỡng nén lên tối thiểu 75% (`_SMALL_CTX_THRESHOLD_PERCENT = 0.75`), khiến model bị nén ở 150k.
  Nhưng khi context là 1.000.000 (>= 512k), Hermes giữ nguyên tỉ lệ `compression.threshold: 0.3` (30%) $\rightarrow$ Ngưỡng nén thực tế chuẩn xác là **300.000 tokens**.
  Điều này đảm bảo an toàn tuyệt đối: luôn nén trước trần 372k của các worker GPT-5.6 (luna/terra/sol), tránh bị gpt "ngọng" khi context phình to.

## 2. Reasoning effort qua 9router (deepseek v4)
- Hermes config: `agent.reasoning_effort: max` → resolve thành `{'enabled': True, 'effort': 'max'}`. DeepSeek V4 chỉ chấp nhận **low/high/max** (`DEEPSEEK_V4_REASONING_EFFORTS`); "medium" bị reject → provider default.
- Wire: transport gửi `extra_body.reasoning={"enabled":true,"effort":"max"}` khi `_supports_reasoning_extra_body()` true = custom:9router + localhost:20128 + model `cmc/deepseek/*` (các custom endpoint khác KHÔNG gửi reasoning).
- 9router console log `THINK:X` đọc từ body sau translate, ưu tiên: `output_config.effort` → `thinking` → `reasoning_effort`/`reasoning.effort` → `thinkingConfig` → `enable_thinking`.
- **Cách ép chắc chắn 100%: đổi tên model kèm suffix** — `cmc/deepseek/deepseek-v4-flash(max)` hoặc `(high)`. 9router parse suffix làm override cứng `{mode:"level"}`; `(auto)`→auto; `(none|off)`→tắt; `(1234)`→budget tokens. Không suffix → đọc body, body không có gì → provider default (auto).
- **THINK:auto trong log DÙ config max** — nguyên nhân: (a) request chạy trước khi đổi config (reasoning_config resolve lúc session init → cần /new hoặc /model), (b) fallback gemini (`fallback_providers: gemini/gemini-3.6-flash` qua cùng 9router, `reasoning_overrides: high`), (c) Hermes version đang chạy khác code trên disk.
- Verify nhanh: `curl -s POST http://127.0.0.1:20128/v1/chat/completions -d '{"model":"cmc/deepseek/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'` — nhưng nguồn thật là console log 9router (cần auth, `/login`).

## 2b. Reasoning Effort qua OmniRoute (:20129) — Delegation Worker Subagent

Khi `delegation.provider: omni` (worker subagent chạy qua OmniRoute combo), `reasoning_effort` bị **silent drop** nếu provider `omni` chưa map về custom profile.

### Nguyên nhân gốc (2026-09-08)
1. `_PROVIDER_ALIASES` trong `agent/auxiliary_client.py` không có `"omni"` → provider không normalize → `_supports_reasoning_extra_body()` trả `False` → payload HTTP gửi sang OmniRoute **thiếu trường `reasoning_effort`**.
2. OmniRoute translator (`openai-to-gemini.ts`) khi không có `reasoning_effort` → inject default thinking budget: `thinkingConfig.thinkingBudget: 24576` (tương đương High/Full thinking, KHÔNG phải Medium).
3. Kết quả: config `delegation.reasoning_effort: medium` bị bỏ qua hoàn toàn, subagent chạy thinking mức High.

### Fix (3 lớp)
1. **Alias**: Thêm `"omni": "custom"` vào `_PROVIDER_ALIASES` trong `agent/auxiliary_client.py` (site-packages,会被 update覆盖). Alternative: đăng ký `ProviderProfile` cho omni qua user plugin `~/.hermes/plugins/model-providers/omni/`.
2. **custom_providers**: Thêm entry trong `config.yaml`:
   ```yaml
   custom_providers:
   - name: omni
     base_url: http://127.0.0.1:20129/v1
     key_env: OMNIROUTE_API_KEY
     model: omni-worker
   ```
3. **Restart gateway**: `hermes gateway restart` từ shell ngoài (không thể restart từ trong gateway process).

### Verify sau fix
- Spawn subagent test → check OmniRoute call log: `reasoning_effort` phải là `"medium"` (không phải `null`).
- Check `summary.tokens.reasoning` giảm từ ~24K xuống ~8K tokens.
- OmniRoute upstream payload phải có `thinkingConfig.thinkingBudget: 8192` (Medium map).

### Provider plugin (alternative vĩnh viễn)
Tạo `~/.hermes/plugins/model-providers/omni/__init__.py` với `OmniProfile(ProviderProfile)` override `build_api_kwargs_extras()` để forward `reasoning_config.effort` thành `top_level["reasoning_effort"]`. File `plugin.yaml` cần `kind: model-provider`.

## Pitfalls
- **False 429 Alert & Timestamp Milliseconds**: Khi grep thô chuỗi `"429"` trong log (`agent.log`, `errors.log`), chuỗi `,429` xuất hiện từ timestamp millisecond (`09:48:26,429`) hoặc token count (`cache=255429`, `total=144429`). Cần kiểm tra HTTP status qua endpoint `/api/logs/console` trên OmniRoute (:20129) thay vì kết luận nhầm là HTTP 429 rate-limit.
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

db_path = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "hermes" / "state.db"
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

### Kiến trúc phân tầng Memory vs Skill vs Repo (Consensus User - Sol - Claude 30/09/2026)
- **Kỷ luật đẩy nghiệp vụ về đúng repo (User correction)**: Tuyệt đối CẤM nhồi chi tiết quy tắc vận hành, code logic của từng repo vào Memory làm nặng bot. Mọi quy tắc nghiệp vụ phải nằm trong Skill hoặc tài liệu của repo đó.
- **Vai trò sống còn của Memory - Bảng định tuyến O(1)**: Không được xóa sạch đường dẫn repo / file như lý thuyết suông của Sol. Trong môi trường cấm quét đĩa diện rộng, Memory là **Lớp phản xạ định tuyến vận hành (Operational Routing Layer)** giúp Agent ánh xạ từ khóa tự nhiên của User thành Repo đích và Entry point mà không cần User phải nhắc tên repo và không cần quét đĩa.
- **Mô hình 4 tầng chuẩn**: System Prompt (Skill Catalog tóm tắt) ➜ Memory (`MEMORY.md` < 1000 chars bảng định tuyến O(1) + Invariants) ➜ Skills (SOP sâu nạp theo yêu cầu) ➜ Repos (Ground truth code thực thi). Chi tiết tại `references/memory-architecture-routing-vs-repo-separation.md`.

## Payload Anatomy & Cloudflare 413 Trap (2026-09-22 Audit)

Khi user hỏi "Kiểm tra payload mỗi request của t hiện nay. Có bị nhồi nhét quá nhiều k, sợ hermes nó nhồi nhiều quá":

### 1. Bóc tách định lượng Request Payload thực tế của Hermes:
- **System Prompt (~37k chars ≈ ~9.3k tokens, ~14%):** Luật an toàn Farm, 5 Gates điều phối, Closeout gate, Profile user, Invariant memories, tóm tắt danh mục skills.
- **Tools Definitions Schema (~58.8k chars ≈ ~14.7k tokens, ~22%):** Bảng định nghĩa tham số của 28 công cụ (terminal, browser, cronjob, computer_use, session_search...).
- **Fixed Baseline tổng cộng: ~24.000 tokens (~95KB):** Đây là khung cố định bắt buộc cho một agentic autonomous coordinator. Mức này chiếm chưa tới **2.4%** của Gemini (1M context) và **12%** của Claude (200k context) → **Hoàn toàn an toàn, không lo bị nhồi**.
- **Conversation History & Tool Results (~175k – 720k+ chars ≈ 44k – 180k+ tokens, 64% – 80%):** ĐÂY CHÍNH LÀ NGUỒN PHÌNH TẢI CHÍNH. Mỗi turn tool dump kết quả dài hoặc session tích tụ qua nhiều ngày sẽ đẩy tổng gói tin lên 250k – 300k tokens (~1MB text).

### 2. Bản chất lỗi "Cloudflare HTTP 413: Payload Too Large":
- **Web Proxy (ChatGPT Web / GPM Web):** Đi qua Cloudflare WAF bảo vệ web app. Cloudflare và upstream web server có trần cứng HTTP body (~1MB). Khi lịch sử chat tích tụ hoặc prompt chứa tool context nặng, gói tin vượt trần → Cloudflare chặn họng trả về **HTTP 413 (Payload Too Large)**.
- **Native API Endpoints (Google Antigravity, OpenAI direct, Anthropic direct):** KHÔNG bị trần Cloudflare web giới hạn. Gemini hỗ trợ 1.000.000 tokens và Claude 200.000 tokens. Request 82k hay 259k tokens vẫn trả về 200 OK bình thường trong 7s–10s.
- **Khuyến nghị vận hành khi user lo lắng bị nhồi:**
  - Không lo lắng về System Prompt hay Tool Schemas (khung chuẩn 24k tokens).
  - Giải phóng lịch sử bằng `/new` ngay sau khi hoàn thành một chủ đề lớn để đưa request về lại ~24k tokens ban đầu.
  - Hạn chế để tool foreground dump log thô dài hàng nghìn dòng vào context.

## Cross-session interference & Multi-session lag diagnosis

Khi user chat hàng loạt session song song và thấy phản hồi chậm (hỏi "do nghẽn model ở omni hay nghẽn ở gateway"):

### 0. 🚨 TỬ HUYỆT Disk Full 100% (No space left on device - 0 bytes free) (2026-09-24 Incident):
- **Triệu chứng**: Toàn bộ 10+ sessions đồng loạt đứng im, OmniRoute console trống trơn 0 request suốt 6-10 phút dù user liên tục nhắn tin. Log gateway xuất hiện: `[Errno 28] No space left on device`.
- **Nguyên nhân gốc**: Thư mục `C:\Users\Kibe\.omniroute\db_backups` tích tụ hàng trăm file backup `storage.sqlite` (mỗi file 2.7GB, tích tới 140+ GB!) do watchdog/restart tự copy mà không có cơ chế auto-prune. Khi ổ C: cạn kiệt (còn < 200MB), mọi syscall `open('w')`, `file.write()`, `db.commit()` bị hệ điều hành Windows treo vĩnh viễn ở mức Kernel (I/O wait lock). Tiến trình máy tính bị đóng băng trước khi kịp mở socket gửi request sang OmniRoute.
- **Chẩn đoán nhanh O(1)**: `df -h` hoặc `powershell -NoProfile -Command "Get-PSDrive C"`.
- **Xử lý khẩn cấp**:
  ```powershell
  # Giữ lại 5 bản backup mới nhất, xóa sạch phần còn lại trong .omniroute\db_backups:
  $files = Get-ChildItem -Path 'C:\Users\Kibe\.omniroute\db_backups' -File | Sort-Object LastWriteTime -Descending
  $files | Select-Object -Skip 5 | Remove-Item -Force
  Get-ChildItem -Path 'C:\Users\Kibe\.omniroute' -Filter '*bak*' | Remove-Item -Force
  ```
  Giải phóng ngay 100-140 GB trống cho ổ C:, đưa Use% từ 100% về ~85%.

### 0b. 🚨 Telegram Webhook "Read timeout expired", Outbound Media Stall & Chuỗi Phạt Exponential Backoff (5-10 phút) (2026-09-24/25 Incidents):
- **Triệu chứng**: User thấy OmniRoute dashboard trống trơn 0 request suốt 5-10 phút (tưởng OmniRoute nghẽn hoặc bot đồng loạt nghỉ batch). Thực tế User đã gửi nhiều tin nhắn trên Telegram nhưng bot không nhận được, không typing, cho đến khi đột ngột xả dồn 1 loạt tin nhắn vào cùng 1 giây.
- **Nguyên nhân cốt lõi (3 tầng nghẽn Gateway Webhook)**:
  1. *Synchronous disk I/O trong Event Loop*: Thao tác cache media chạy sync trên Main Event Loop thread block Event Loop 5-15 giây.
  2. *Outbound Media Download Stall qua mạng FPT*: Khi user gửi tin nhắn kèm ảnh/video, Webhook nhận payload qua Cloudflare Tunnel (`bot.taadaa.click`), nhưng Gateway bắt buộc phải gọi ngược ra `https://api.telegram.org/file/bot...` để tải file ảnh về. Nếu `TELEGRAM_PROXY` bị tắt, luồng tải ảnh đi Direct FPT và bị ISP silent drop/stall socket $\rightarrow$ kẹt httpx connection $\rightarrow$ làm nghẽn toàn bộ cổng Webhook.
  3. *Telegram Exponential Backoff Penalty*: Do Gateway bị kẹt không kịp phản hồi HTTP 200 cho Telegram trong 5 giây $\rightarrow$ `getWebhookInfo` báo `last_error_message: "Read timeout expired"`. Telegram coi như Webhook sập và áp dụng chuỗi phạt không đẩy tin mới: `1s -> 2s -> 5s -> 10s -> 30s -> 60s -> 300s (5 phút)`. Toàn bộ tin nhắn bị giam tại server Telegram cho đến khi hết hạn phạt mới dồn ập về máy.
- **Chẩn đoán nhanh O(1)**:
  ```python
  import urllib.request, json
  # Lấy token từ .env
  url = f'https://api.telegram.org/bot{token}/getWebhookInfo'
  req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
  with urllib.request.urlopen(req, timeout=10) as resp:
      print(json.dumps(json.loads(resp.read().decode())['result'], indent=2))
  ```
  Nếu thấy `last_error_message: "Read timeout expired"` và `last_error_date` trùng khớp khoảng thời gian im lặng $\rightarrow$ khẳng định 100% do Webhook bị timeout và dính án phạt Telegram giam tin.

### 0e. 🚨 SQLite WAL Bloat (state.db-wal 4GB) gây Disk I/O Lock & Treo Webhook Event Loop (2026-09-25 Incident):
- **Triệu chứng**: Gateway chậm chạp, Webhook 8443 bị chậm phản hồi dẫn đến `Read timeout expired`, lệnh truy vấn SQLite văng `sqlite3.OperationalError: disk I/O error` hoặc timeout 180s.
- **Nguyên nhân gốc**:
  - `hermes_state.py` trong write hot-path chỉ chạy `PRAGMA wal_checkpoint(PASSIVE)`. Lệnh `PASSIVE` chỉ flush frame mà **KHÔNG BAO GIỜ thu nhỏ file WAL** (nó giữ nguyên high-water mark).
  - Trải qua hàng trăm nghìn turn chat/subagent, file `C:\Users\Kibe\AppData\Local\hermes\state.db-wal` phình khổng lồ lên **3.8 GB – 4.0 GB**.
  - Mỗi khi có write transaction mới, SQLite phải lock và scan trên file WAL 4GB, biến mọi thao tác ghi/đọc của Gateway thành thảm họa I/O.
- **Xử lý tức thì (O(1) Hotfix)**:
  ```python
  import sqlite3
  conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db', timeout=60.0)
  conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
  conn.close()
  ```
  Ép SQLite xả toàn bộ WAL về 0 MB trong < 1 giây, đưa tốc độ đọc `state.db` từ >180s về lại < 100ms.
- **Khóa cứng phòng ngừa (Anti-Bloat Watchdog)**:
  - Tích hợp hàm `check_and_truncate_wal()` vào `hermes_stale_watchdog.py` (chạy định kỳ 2 phút).
  - Nếu dung lượng `state.db-wal` > 50MB $\rightarrow$ tự động kích hoạt `PRAGMA wal_checkpoint(TRUNCATE)` ngầm, triệt tiêu vĩnh viễn nguy cơ bloat WAL làm nghẽn đĩa.

### 0f. 🚨 Event Loop Saturation do Subagent 600s Timeout Cascade + Semaphore Queue Overload (2026-09-25 Incident):
- **Triệu chứng**: Dashboard OmniRoute trống trơn 0 request suốt 5–6 phút dù bot không chết, sau đó bất ngờ xả dồn 170+ requests; log xuất hiện `Subagent timed out after 600.1s`, `timed out before the coroutine was dispatched` (cron warning) và `Semaphore timeout after 30000ms for antigravity:...` (OmniRoute 429).
- **Nguyên nhân cốt lõi (2 đầu nghẽn đồng thời)**:
  1. *Đầu Hermes Gateway*: `delegation.child_timeout_seconds: 600` (10 phút) quá rộng. Khi 2+ worker subagent bị kẹt tool hoặc chờ mạng, chúng ngâm trọn 600s mới bị hủy, giữ cứng concurrency slots (`max_concurrent_children: 8`). Cùng lúc, các lệnh terminal foreground nặng (>180s) block event loop, khiến coroutine dispatch bị đình trệ nghiêm trọng (cron delivery bị trễ).
  2. *Đầu OmniRoute*: Khi nhiều session cùng dồn context lớn (100k–280k tokens) vào combo `omni-worker`, các account Antigravity trong `ag-gemini-pool-3` bị giữ slot hoặc dính rate-limit đồng thời. Request xếp hàng quá 30s dẫn đến 429 Semaphore Timeout.
- **Biện pháp xử lý & Nâng trần chịu đựng (Dual-Head Tuning)**:
  - *Nâng trần OmniRoute*: Khai báo `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT=24` trong `OmniRoute/.env` để tận dụng host 64GB RAM gánh đồng thời nhiều context lớn.
  - *Rút ngắn trần Hermes an toàn (Sweet Spot chống ngâm slot & chống False-Kill Farm)*: 
    - CẢNH BÁO BẪY 180s: Tuyệt đối KHÔNG hạ trần tổng xuống 180s vì sẽ gây False-kill hàng loạt trên worker chạy flow farm (TikTok login/OTP/upload, debug kèm test thực tế mất 4-8 phút). Bị kill ở 180s sẽ để lại máy kẹt dở dang, process `adb.exe` mồ côi và trigger coordinator retry gây trùng thao tác (đăng 2 lần, ban tài khoản). Con số 180s chỉ an toàn nếu là silence/heartbeat timeout (không có tool call mới).
    - Cấu hình chuẩn Sweet Spot: `hermes config set delegation.child_timeout_seconds 480` (hạ từ 1200s xuống 480s = 8 phút, đủ cho 100% flow nặng nhưng không bắt chờ 20 phút khi deadlock).
  - *Kỷ luật Terminal Chặn Đứng Nghẽn Event Loop (Gốc rễ sự cố)*: Clamp cứng foreground terminal `timeout <= 60s` trên session chat trực tiếp. Tác vụ nặng (>30s) BẮT BUỘC chạy `background=True` kèm `notify_on_complete=True`, có cờ `python -u` (chống block buffer pipe Windows), không bao giờ để blocking 600s trên session điều phối.

### 0c. 🚨 Bẫy Regex Lọt Quét Đĩa & Lệch Wire Protocol Trong Hook (`guard_broad_grep.py` - Incident 28/09/2026):
- **3 Lỗ hổng khiến lệnh quét đĩa lọt lưới (Sol High Audit)**:
  1. `\bgrep\s+`: Chỉ bắt `grep -rn`, bỏ lọt `grep.exe -rn` vì sau `grep` là `.exe` không phải whitespace.
  2. `\b` unescaped bị Python biên dịch thành mã ASCII `\x08` (phím Backspace) thay vì word boundary.
  3. Dấu `$` trong target `r"D:[\\/]?$"` bắt buộc nằm ở cuối dòng, bỏ lọt `os.walk('D:/Taadaa')`.
- **4. 🚨 TỬ HUYỆT WIRE PROTOCOL MISMATCH (`shell_hooks.py` vs Hook Scripts)**:
  - `agent/shell_hooks.py` của Hermes truyền payload JSON qua stdin:
    `{"hook_event_name": "pre_tool_call", "tool_name": "terminal", "tool_input": {"command": "...", "timeout": ...}}`
  - Nếu script hook đọc `args = payload.get("args")` $\rightarrow$ `args` luôn là `{}` (vì key thật là `tool_input`) $\rightarrow$ `cmd = ""` $\rightarrow$ **HOOK BỊ ĐIẾC HOÀN TOÀN, MỌI LỆNH QUÉT ĐĨA ĐỀU LỌT LƯỚI!**
  - **Sửa chuẩn**: `args = payload.get("tool_input") or payload.get("args") or {}`, `tool_name = payload.get("tool_name") or payload.get("tool") or ""`.
- **5. 🚨 BẢN FIX "BẰNG MỒM" TRONG PROMPT HOÀN TOÀN VÔ NGHĨA — BẮT BUỘC HARD CLAMP BẰNG HOOK**:
  - Quy ước "chỉ chạy lệnh <= 60s" ghi trong prompt không ngăn được agent chạy `os.walk('D:/Taadaa')` ngâm trần 600s (`[Command timed out after 600s]` 602.91s, đơ Telegram 10 phút đêm 28/09).
  - **Hard Clamp tầng Tool Hook**:
    + Lệnh foreground (`not background`) thiếu `timeout`: Chặn với `GUARD_FOREGROUND_TIMEOUT_MISSING`.
    + Lệnh foreground có `timeout > 60s`: Chặn với `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`.
    + Ép tác vụ nặng (>60s) chuyển sang `terminal(background=True, notify_on_complete=True)`.

### 0d. 🚨 Upstream Antigravity 90s Timeout Cascade & Bẫy Deadlock HTTP 499 (2026-09-24 Claude & Sol Consensus):
- **Triệu chứng**: User thấy agent/Omni bị treo 4-5 phút, console OmniRoute trống trơn 0 request dù nhiều session đang chat. Dễ nghi ngờ nhầm do Telegram webhook rớt hoặc ổ đĩa bị nghẽn do agent quét file.
- **Nguyên nhân cốt lõi (Tử huyệt lệch Timeout Headroom)**:
  1. *Hermes Client timeout*: Mặc định ngầm định `90.0s` (`run_agent.py:1269–1301`). Sau 90s không có byte nào trả về, httpx cancel socket.
  2. *OmniRoute Combo timeout*: `ag-gemini-pool-3` đặt `targetTimeoutMs: 90000`, `omni-worker` không set (rơi về 120s/600s).
  3. *Deadlock dừng combo loop*: Khi socket Google treo, Hermes chạm 90s trước $\rightarrow$ gửi Abort $\rightarrow$ OmniRoute ghi nhận HTTP 499 và dừng combo loop ngay (`open-sse/services/combo.ts:2066` `Client disconnected (499) — stopping combo loop`). Router **KHÔNG failover sang Tier kế tiếp**, và **KHÔNG phạt cooldown account**. Subagent tiếp theo lại chọn trúng account chết $\rightarrow$ domino freeze 4 phút.
- **Quy trình chẩn đoán O(1) tách bạch 3 tầng**:
  1. **OmniRoute upstream call logs**:
     Query `C:\Users\Kibe\.omniroute\storage.sqlite`:
     ```python
     import sqlite3
     conn = sqlite3.connect('C:/Users/Kibe/.omniroute/storage.sqlite')
     c = conn.cursor()
     # Tìm các request bị abort hoặc duration kịch khung 90s
     rows = c.execute("SELECT id, timestamp, account, provider, duration, error_summary FROM call_logs WHERE (status = 499 OR duration > 60000) ORDER BY id DESC LIMIT 15").fetchall()
     ```
     Nếu thấy chuỗi `duration ~ 90000` kèm `status=499` và `error_summary='Request aborted'` trên `antigravity` $\rightarrow$ khẳng định 100% do upstream socket timeout.
  2. **Kiểm tra ổ đĩa C: (loại trừ Kernel I/O lock)**:
     `Get-PSDrive C` (trống > 20GB) và `Avg. Disk Queue Length` trên ổ C: (< 0.1) $\rightarrow$ loại trừ nghẽn I/O hệ điều hành. (Ổ D: có thể queue cao do batch/pytest/git nhưng độc lập, không làm treo SQLite trên C:).
  3. **Kiểm tra Telegram Webhook**:
     Lấy `TELEGRAM_BOT_TOKEN` từ `C:\Users\Kibe\AppData\Local\hermes\.env` và gọi `https://api.telegram.org/bot<token>/getWebhookInfo`. Kiểm tra `pending_update_count == 0` và đối chiếu `last_error_date` với timestamp hiện tại.
- **Biện pháp xử lý & Hardening triệt để (Tạo Headroom Gap 45s vs 120s)**:
  1. **Hạ trần Timeout Upstream Combo xuống 45s**: Set `targetTimeoutMs: 45000` cho tất cả combo (`omni-worker`, `ag-gemini-pool-3`...) và `STREAM_READINESS_TIMEOUT_MS=45000`. Khi Google ngâm socket, OmniRoute tự timeout ở 45s $\rightarrow$ sinh 504 `combo_target_timeout` $\rightarrow$ failover tức thì sang Tier 2/3/4. CẤM dùng flat timeout 30s vì sẽ false-kill các prompt 150k token khi prefill.
  2. **Nâng trần Client Headroom trên Hermes**: Thêm `HERMES_API_CALL_STALE_TIMEOUT=120` vào `C:/Users/Kibe/AppData/Local/hermes/.env`. Hermes kiên nhẫn đợi đến 120s, nhận được kết quả failover của OmniRoute ở giây thứ 50 mà không bao giờ sinh mã 499.
  3. **Adaptive Circuit Breaker & Gradient Weight**: Giảm trọng số dần (1.0 $\rightarrow$ 0.7 $\rightarrow$ 0.3 $\rightarrow$ 0.0) khi gặp timeout; cách ly 10m kèm Half-open probe.
  4. **Router-Level Saturation Guard**: Nếu 1 provider chiếm >90% worker slots quá 30s $\rightarrow$ đóng cổng nhận request mới vào provider đó và bẻ sang fallback ngay.

### 0g. 🚨 OmniRoute SQLite Maintenance Hang, WAL 1.8GB & Crash 0xC0000409 (Incident 30/09 - 01/10/2026):
- **Triệu chứng**: OmniRoute treo nhiều lần (23:49, 07:50, 13:49), crash với mã `0xC0000409` (STATUS_STACK_BUFFER_OVERRUN) lúc 13:59. Hermes Gateway im lặng, các agent chết giữa chừng do proxy không phản hồi.
- **Nguyên nhân cốt lõi**:
  1. *Database & WAL phình to*: Bảng `quota_snapshots` và `conversation_turn_nodes` trong `storage.sqlite` phình lên 1.9GB, file WAL tích tụ 1.8GB.
  2. *Bảo trì SQLite đồng bộ trên Main Event Loop*: Cứ mỗi 6 tiếng, watchdog/Node.js chạy checkpoint WAL và cleanup + VACUUM đồng bộ. File 1.8GB lock I/O khiến luồng Node.js duy nhất bị nghẽn (freeze), không thể nhận/trả request, thời gian khởi động kéo dài 150s.
  3. *Fallback OpenCode "mất context"*: Bridge OpenCode chỉ forward tin nhắn cuối của user, khi fallback sang muse-spark khiến bot bị "trắng context" (mất toàn bộ lịch sử hội thoại).
- **Biện pháp xử lý & Tinh chỉnh (Watchdog, Prune & Failover)**:
  1. *Dọn bảng định kỳ > 3 ngày*: Xóa dữ liệu cũ hơn 3 ngày trong `quota_snapshots` và `conversation_turn_nodes` (hai bảng này chỉ vẽ chart UI, không ảnh hưởng pool credentials hay routing). DB giảm từ 1888MB $\rightarrow$ 597MB, WAL từ 1.8GB $\rightarrow$ 4MB, startup time từ 150s $\rightarrow$ 44s.
  2. *Tăng trần heap Node.js & Tần suất checkpoint nhỏ giọt*: Trong `omniroute_watchdog.ps1`, cấu hình `--max-old-space-size=8192` (8GB heap), checkpoint WAL mỗi 5 phút (thay vì dồn 6 tiếng), giới hạn body log 64KB, cắt chuỗi 16KB, giữ log 7 ngày, bỏ cổng inspect.
  3. *Bản vá Failover Telegram Adapter (WARP ↔ Trực tiếp)*: Trang bị `TelegramMultiISPTransport` cho cả luồng gửi tin (`request` / `edit_message`) song song với luồng nhận (`get_updates`), kèm unit test `tests/test_telegram_send_failover.py` (3 passed).
  4. *Fallback an toàn*: Đặt fallback chain chỉ còn `omni-worker` $\rightarrow$ `luna`, tăng `api_max_retries: 5`, giữ `compression.threshold: 0.3`.
  5. *Đồng bộ Git Commit*: Đã commit bản vá Telegram send failover vào cả 2 repo: `D:\Taadaa\Hermes` (`da4d167e6`) và `hermes-agent` (`ec6c8d1c9`). Khi chạy `closeout_gate.py` cho `hermes-agent`, hệ thống tự phát hiện file test `tests/test_telegram_send_failover.py` để chạy focused pytest verification trước khi chuyển Sol High chấm điểm.

### 0h. 🚨 OmniRoute V8 Heap Pressure 7.1GB (HTTP 503 resource_pressure) & Thundering Herd Retry Storm (Incident 02/10/2026):
- **Triệu chứng**: Bot Telegram báo "The model provider failed after retries" (HTTP 503 `resource_pressure`), trong khi Dashboard OmniRoute vẫn có request thành công xen kẽ. Watchdog cũ không phát hiện được do `/api/health` vẫn 200.
- **Nguyên nhân cốt lõi (3 tầng)**:
  1. *OmniRoute V8 Heap Guard*: V8 heap Node.js vượt trần 7126MB (`[chatCore] heap pressure guard tripped: 7166MB > 7126MB; returning 503`), router chủ động ngắt chat completions để bảo vệ tiến trình.
  2. *Context Bloat không chạm ngưỡng nén*: `compression.threshold: 0.3` trên `context_length: 1000000` tạo ra ngưỡng nén 300.000 tokens. Các session dài tích tụ 150k – 250k tokens không bị nén, liên tục gửi payload khổng lồ sang OmniRoute.
  3. *Thundering Herd Retry Storm*: 10 session đồng thời cùng retry 5 lần (`api_max_retries: 5`) với backoff ngắn (~2s, ~4s, ~8s...) dồn dập vào OmniRoute, khiến Node.js không kịp dọn rác (GC) hoặc hồi phục.
- **Biện pháp xử lý & Tinh chỉnh triệt để (User Consensus & Vá Thực Tế 03/10/2026)**:
  1. *Watchdog OmniRoute (`omniroute_watchdog.ps1`)*: Bổ sung `Get-NewHeapTripCount` quét regex `heap pressure guard tripped|critical pressure guard tripped`. Tự động restart khi trip 4 lần liên tiếp (~60s), cooldown 600s (10 phút).
  2. *🚨 CẢNH BÁO BẪY NÉN LIÊN TỤC — BẮT BUỘC GIỮ THRESHOLD 0.3*: Tuyệt đối KHÔNG hạ `compression.threshold` xuống `0.12`. Khi hạ xuống 0.12, các session làm việc bình thường ở 120k tokens sẽ bị kích hoạt nén liên tục ("120k context thì nén liên tục"), gây tắc nghẽn trải nghiệm. BẮT BUỘC duy trì `compression.threshold: 0.3` (300k tokens trên context 1M).
  3. *Giảm retry bão tải*: `hermes config set agent.api_max_retries 3` (giảm từ 5 xuống 3 để tránh 50 requests dồn dập).
  4. *Vá giãn retry 503 Overloaded (`agent/conversation_loop.py`)*: Nâng `base_delay` từ 2.0s lên **`10.0s`** khi phân loại là `FailoverReason.overloaded`. Nhịp retry kéo giãn thành ~11–15s $\rightarrow$ ~20–30s $\rightarrow$ ~40–60s (tổng chờ ~85s), đủ thời gian cho watchdog OmniRoute restart (~24s) và Node.js chạy GC dọn RAM trước lần thử tiếp theo. Chi tiết xem `references/omniroute-heap-pressure-and-retry-backoff.md`.

### Quy trình chẩn đoán 4 bước tách bạch:
1. **Kiểm tra Model / Proxy (OmniRoute / 9Router):**
   - Không đoán mò proxy nghẽn. Đọc trực tiếp `C:\Users\Kibe\.omniroute\storage.sqlite` (bảng `call_logs`, cột `status, duration, error_summary`) hoặc `curl -s http://127.0.0.1:20129/v1/models`.
   - Đo latency `/api/health`: nếu vọt từ ~5ms lên 3s-5s+ $\rightarrow$ hàng đợi admission queue đang quá tải.
   - Kiểm tra `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT`: Mặc định là 9. Khi có 15-35 sessions cùng chạy, 9 slot này bị chiếm trọn bởi context nặng (50k-255k tokens), khiến các request chat mới bị nghẽn chờ slot. Nâng lên 24 trong `omniroute_watchdog.ps1` (RAM 64GB host dư tải an toàn).
2. **🚨 BẤT BIẾN: Không Tự Ý Coi Session Cũ Là "Zombie / Rác" (User Multi-Day Workspaces):**
   - User phân tách công việc theo Telegram Forum Topics / Groups (Topic Farm Alert, Topic Review Code, Topic ChatGPT Web, Topic Avatar Watchdog...).
   - Nhiều task kéo dài 2-3 ngày qua nhiều phiên. CẤM TUYỆT ĐỐI Agent tự ý coi các session từ hôm trước là "zombie / leak / session rác" rồi đòi kill. Mọi thao tác hủy session phải do User chỉ định.
3. **🚨 BẪY: Tưởng Treo Bot Do Chuỗi Tool Call Tuần Tự hoặc Khoảng Nghỉ Tự Nhiên (Dashboard 0 Requests False Alarm):**
   - Khi User nhìn Dashboard OmniRoute/9Router thấy khoảng trống 5-10 phút không có request nào, rất dễ nghi ngờ bot bị treo hoặc Telegram rớt mạng.
   - **Quy trình phân biệt O(1) tránh báo động nhầm**:
     1. *Kiểm tra `gateway.log`*: Trong khung giờ đó User có nhắn tin không? Nếu không có tin nhắn mới từ User $\rightarrow$ Bot đang ở trạng thái Idle hoàn toàn tự nhiên.
     2. *Kiểm tra `agent.log`*: Các worker/subagent có đang chạy tool execution dài (pytest, batch sync, terminal lệnh nặng) không? Trong lúc chạy tool, Agent không phát sinh request LLM lên OmniRoute.
     3. *Kiểm tra tin nhắn kế tiếp*: Ngay khi User gửi tin mới, Gateway có nhận tức thì (<0.1s) và router có bùng nổ request xử lý ngay không? Nếu có $\rightarrow$ Hệ thống hoàn toàn thông suốt, không phải lỗi mạng hay treo bot.
   - Khi OmniRoute tải nặng, latency mỗi call `omni-worker` tăng lên 20s-25s/call.
   - Nếu Coordinator chạy chuỗi 10-15 tool calls tuần tự trong 1 turn: $15 \times 22\text{s} = 330\text{s}$ (~5.5 phút) im lặng trên Telegram. User lầm tưởng bot bị treo mạng tiếp.
   - Kỷ luật Coordinator: Ở session chat trực tiếp với User, giữ turn O(1) < 2 tool calls. Muốn probe/scan sâu bắt buộc dispatch `delegate_task` chạy ngầm.
4. **Kiểm tra Tool execution blocking trong Agent (`agent.log`):**
   - Grep `tool .* completed \([\d\.]+s` trong `agent.log`.
   - Tìm các lệnh `terminal`, `search_files`, `process` chạy foreground tốn 30s - 600s (ADB, pytest, batch sync). Khi agent đang chờ tool hoàn tất, cả turn bị kéo dài (300s - 1900s) dù LLM chỉ mất vài giây.
5. **Kiểm tra Gateway ThreadPool & SQLite lock (`gateway.log`):**
   - Kiểm tra `response ready: platform=... time=...` đối chiếu với số `api_calls`.
   - Tìm `state.db routing save failed: database is locked` (xảy ra khi nhiều session cùng ghi routing/transcript vào SQLite).
   - Kiểm tra mạng Telegram Bot API: tìm cảnh báo `Primary api.telegram.org connection failed ... fallback IPs`.

### Giải pháp khuyến nghị:
- Chuyển các tác vụ dài sang background (`background=true` hoặc cron) thay vì để agent foreground blocking.
- Session cũ context phình to (>150k-200k tokens) cần `/new` để tránh overhead nén & latency.

### 0i. 🚨 Tử Huyệt state.db Phình 14GB, Bẫy VACUUM Ăn Tràn Ổ C & Lỗi "session storage could not be written" (Incident 07/10/2026):
- **Triệu chứng**: Turn bị ngắt khẩn cấp kèm thông báo: `⚠️ No reply: the turn was stopped because session storage could not be written (the transcript would have been lost on restart). This is often a full disk — free some space (or fix state.db permissions)...`
- **Nguyên nhân cốt lõi (SQLite Lock Timeout trên Database Khổng Lồ)**:
  - Ổ đĩa ban đầu KHÔNG hề đầy (ổ C: còn 18GB, ổ D: còn 900GB).
  - File `C:\Users\Kibe\AppData\Local\hermes\state.db` đã tích tụ phình to tới **14.2 GB** (hơn 1.23 triệu messages, 6.000 sessions, kèm index FTS5 trigram khổng lồ).
  - Khi Coordinator hoặc Worker ghi tin nhắn mới, SQLite mất hơn 5 giây (`busy_timeout = 5000ms`) để cập nhật index trên file 14GB $\rightarrow$ văng lỗi `database is locked`. Hermes buộc phải ngắt turn để bảo vệ transcript không bị mất.
- **🚨 BẪY CHẾT NGƯỜI: Lệnh `hermes sessions optimize` hoặc `VACUUM` trực tiếp gây cạn kiệt ổ C:**
  - Khi chạy `hermes sessions optimize` (FTS merge + VACUUM), SQLite mặc định tạo file tạm trong thư mục DB hoặc `%TEMP%` trên **ổ C**.
  - Database gốc 14GB cần tối thiểu 14-15GB trống để nhân bản file tạm. Với ổ C chỉ còn ~18GB, tiến trình VACUUM sẽ nuốt sạch dung lượng còn lại xuống 0 byte $\rightarrow$ văng lỗi `Error: optimization failed: database or disk is full` và biến lỗi full disk giả thành **Full Disk THẬT**, khóa cứng toàn bộ gateway.
- **Biện pháp xử lý chuẩn hóa 2 bước an toàn**:
  1. *Prune session theo cửa sổ thời gian an toàn (CLI chuẩn của Hermes)*:
     Chạy nền với `background=true` để không block gateway:
     `hermes sessions prune --older-than 21d --include-archived --yes`
     (Giảm ngay 2.256 sessions và 450.000 messages cũ mà không khóa DB dài hạn).
  2. *VACUUM chuyển hướng sang ổ D (VACUUM INTO)*:
     TUYỆT ĐỐI KHÔNG chạy `VACUUM` trơn trên ổ C khi dung lượng trống < 2x dung lượng DB. Dùng `VACUUM INTO 'D:/Taadaa/...'` để xuất DB đã nén sang phân vùng còn nhiều dung lượng trống (ổ D còn >800GB). Sau đó dọn dẹp temp files trong `%TEMP%`.
  - Xem chi tiết tại `references/state-db-bloat-and-session-storage-lock.md`.

### 0j. 🚨 Windows Terminal `_drain` GIL Starvation & Gateway Freeze 37 phút (Incident 07/10/2026):
- **Triệu chứng**: Toàn bộ hệ thống (Telegram Gateway, Cron Scheduler, HTTP response streams) bị đóng băng hoàn toàn suốt 37 phút (20:08:51 đến 20:46:12). Mọi file log (`gateway.log`, `agent.log`, `errors.log`) im bặt. Sau khi hết nghẽn, `agent.log` xả ra hàng loạt API call với latency ghi nhận vọt lên **2258.0s (~37.6 phút)** và 15+ cron jobs missed schedule chạy cùng 1 giây.
- **Nguyên nhân gốc rễ (Root Cause qua Py-Spy Dump)**:
  1. *Windows Pipe Blocking Read*: Windows không hỗ trợ `select.select()` trên pipe fd nên `tools/environments/base.py` dùng vòng lặp `while True: chunk = os.read(fd, 4096)` trong thread `_drain`.
  2. *Output vô hạn & 9.9 GB RAM*: Khi một subprocess in log khổng lồ không kiểm soát, hàng chục triệu object chuỗi nhỏ được tạo và append liên tục làm Private Memory vọt lên **9.9 GB**.
  3. *GC Thrashing giữ chặt GIL*: Bộ thu dọn rác (GC) scan liên tục trên bộ nhớ ảo (swap disk), giữ chặt GIL của Python khiến tất cả thread khác bị chết đói (Starvation).
- **Biện pháp xử lý & Vá Runtime**:
  - Khống chế trần an toàn `max_capture = 100MB` trong `tools/environments/base.py`.
  - Chèn `time.sleep(0.0001)` định kỳ nhả GIL cho các luồng mạng và cron scheduler.
  - Xem chi tiết tại `references/windows-terminal-drain-gil-starvation.md`.

### 0k. 🚨 Lỗi Corrupted Turn Gemini HTTP 400 (Invalid function call turn sequence) & Vòng lặp Treo Stream "Waiting for chunks yet" (Incident 07/10/2026):
- **Triệu chứng**:
  - Agent quăng lỗi raw JSON ra Telegram:
    `HTTP 400: [400]: { "error": { "code": 400, "message": "Please ensure that function call turn comes immediately after a user turn or after a function response turn.", "status": "INVALID_ARGUMENT" } }`
  - Các turn tiếp theo bị treo cứng 6 - 12 phút ngâm stream: `⌛ Working — iteration 0/200, waiting for stream response (4s, no chunks yet)`.
- **Nguyên nhân cốt lõi (Root Cause)**:
  1. *Lệch cấu trúc Turn (Gemini API Strict Turn Alternation Violation)*: Gemini bắt buộc luân phiên `user` $\rightarrow$ `model (functionCall)` $\rightarrow$ `function (functionResponse)`. Khi stream bị ngắt do socket timeout hoặc tool guard chặn giữa chừng, message history trong SQLite `state.db` bị rách (thiếu tool response hoặc 2 lượt model liên tiếp).
  2. *Upstream từ chối vĩnh viễn*: Mỗi khi user chat tiếp, Hermes gửi lại toàn bộ history bị lỗi $\rightarrow$ Gemini trả về HTTP 400.
  3. *Treo stream*: Hermes không abort sạch mà tiếp tục ngâm chờ chunk stream, gây treo 6-12 phút mỗi lượt.
- **Quy trình xử lý & Cứu hộ (Recovery Workflow)**:
  1. CẤM cố chat tiếp trong session đã hỏng turn (chắc chắn tiếp tục ăn lỗi 400 và treo stream).
  2. Dùng `/new` ngay lập tức để mở session sạch.
  3. Tại session mới, dùng `session_search(around_message_id=..., session_id="...")` hoặc query từ khóa để salvage: (a) Yêu cầu gốc của user, (b) Tiến độ công việc đã xong, (c) Nút thắt kỹ thuật đang kẹt. Tiếp quản và giải quyết dứt điểm tại session mới mà không bắt user nhắc lại.
  - Xem chi tiết tại `references/gemini-turn-sequence-corruption-and-session-recovery.md`.

## References
- `references/gemini-turn-sequence-corruption-and-session-recovery.md` — Sự cố lệch cấu trúc turn Gemini HTTP 400, vòng lặp treo stream chunks và quy trình cứu hộ session dở dang qua session_search (07/10/2026).
- `references/windows-terminal-drain-gil-starvation.md` — Sự cố Windows Terminal _drain GIL Starvation giữ cứng GIL 37 phút làm treo Gateway & 15+ Cron Jobs (07/10/2026).
- `references/state-db-bloat-and-session-storage-lock.md` — Chi tiết sự cố state.db 14GB gây timeout ghi session storage (07/10/2026).
- `references/cockpit-codex-pool-and-luna-coordinator-benchmark.md` — Quy trình nạp pool 10 accounts Codex qua GPM CDP và benchmark hành vi điều phối của model Luna (gpt-6-luna / gpt-5.6-luna) chống over-engineering (07/10/2026).
- `references/omniroute-heap-pressure-and-retry-backoff.md` — Chi tiết sự cố OmniRoute Heap Pressure 7.1GB (HTTP 503), phân tích thundering herd retry storm 10 session và bộ thông số hạ ngưỡng nén 120k + giảm retry (02/10/2026).
- `references/memory-architecture-routing-vs-repo-separation.md` — Biên bản đồng thuận kiến trúc User - Sol - Claude (30/09/2026): Phân tầng 4 cấp (System Prompt ➜ Memory Routing Table O(1) ➜ Skills SOP ➜ Repos), kỷ luật không nhồi nghiệp vụ vào Memory và bản thiết kế Reflex Routing Table <1000 chars.
- `references/hook-wire-protocol-and-foreground-timeout-clamp.md` — Chuẩn hóa Wire Protocol `tool_input` trong `shell_hooks.py` và cơ chế Hard Clamp `timeout <= 60s` cho terminal foreground chống nghẽn Event Loop (Incident 28/09/2026).
- `references/subagent-timeout-and-event-loop-saturation.md` — Chẩn đoán & giải pháp Event Loop Saturation do Subagent ngâm 600s + Semaphore Queue Overload (25/09/2026), cấu hình dual-head OmniRoute 24 slots & Hermes child timeout 180s.
- `references/omniroute-upstream-hang-adaptive-resilience.md` — Sự cố OmniRoute treo 4 phút (13:51 24/09/2026), phân tích bão 252 requests/5m & 90s timeout cascade trên Antigravity, biên bản đồng thuận Sol High vs Claude CLI (Timeout 3 tầng: TTFB 45s, Adaptive Weight Gradient, Saturation Guard, Bulkhead Isolation).
- `references/disk-full-io-freeze-diagnosis.md` — Chẩn đoán lỗi Treo Hệ Thống do Tràn Ổ Đĩa (Disk Full 100%).
- `references/lag-diagnosis.md` — lệnh chẩn đoán + parser python per-session stats.
- `references/reasoning-effort-wire-path.md` — source-map file:line đã verify (Hermes + 9router JS) cho toàn bộ đường reasoning.
- `references/telegram-send-failover-and-omniroute-sqlite-tuning.md` — Chi tiết kiến trúc Multi-ISP Send Failover (WARP/Viettel Proxy ↔ FPT Direct), quy trình dọn dẹp SQLite/WAL định kỳ chống treo luồng Node.js và bảng phân giải context_length/ngưỡng nén thực tế (01/10/2026).
