---
name: hermes-session-tuning
description: "Chẩn đoán Hermes session lag (context bloat → compression threshold), tinh chỉnh compression, và kiểm tra/ép reasoning_effort khi route qua 9router (deepseek v4)."
---

# Hermes Session Tuning (lag + reasoning qua 9router)

## Trigger
- User kêu Hermes lag / session chậm dù RAM-CPU vẫn còn thừa
- Cần kiểm tra model deepseek đang chạy reasoning nào (THINK:auto vs high vs max trong 9router console log)
- Muốn ép reasoning effort chắc chắn qua 9router
- **Bị ngắt turn giữa chừng do chạm trần tool-calling** — prompt cưỡng chế `You've reached the maximum number of tool-calling iterations allowed...` (xem `references/tool-calling-iteration-limit-and-turn-budget-exhaustion.md`)
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
- **Dynamic Skill & Rule Retrieval O(1) chống Context Bloat (2026-10-22)**:
  Thay vì nạp đồng thời toàn bộ 190+ skills vào context window khi mở session (tốn 60k-100k tokens baseline, làm sớm chạm ngưỡng nén và gây lỗi `[SKILL_PRUNED]`), áp dụng bộ ba công cụ O(1) tại `D:/Taadaa/tools/`:
  1. `build_skill_index.py`: Trích xuất front-matter của 190 skills thành `skills_index.json` (<0.5s).
  2. `skill_lookup.py --query "<intent>"`: Tra cứu từ khóa O(1), tự động luôn đính kèm Pinned Core Invariants (`taadaa-farm-ops-rules`, `farm-anti-overengineering`, `session-close-protocol`, `evidence-first-delivery`, `agent-verification-loop`).
  3. `load_selected_skills.py`: Nạp chọn lọc đúng N skills khớp vào context làm việc, chặn Path Traversal và escape HTML comments.
  4. **Cơ giới hóa (Mechanical Wiring)**: Không để ở mức CLI On-Demand (dễ bị quên). Tích hợp Pre-dispatch Hook qua `skill_injector.py` vào `dispatch_worker.py` để tự động bốc skill nạp cho Worker với trần 15k ký tự (graceful fail-closed, tự cắt `## References` dài >100k của pinned skills để tránh nổ trần).
  5. **Chốt chặn an toàn khi cơ giới hóa**:
     - *Safe Boundary Clamping*: Khi cắt tỉa context để fit budget, lùi về ranh giới `<!-- END SKILL: ... -->` của block trước đó, không cắt ngang xương giữa tag.
     - *Audit Telemetry RC Integrity*: Ghi audit log với `correlation_id` đồng nhất; truyền `rc=1` khi trạng thái là `FAIL_CLOSED_*`, truyền `0` khi `OK`/`NO_MATCH`.
     - *Hermetic Test Fixtures*: Test cho injector bắt buộc dùng `tmp_path` hermetic fixture, không phụ thuộc vào live `DEFAULT_INDEX` trên farm để tránh flake do mtime drift.
     - *Windows 8191 CLI Length Cap*: Windows CreateProcess giới hạn 8191 ký tự command line; khi truyền qua argument dòng lệnh của wrapper, clamp trần an toàn `max_context_chars=2500` hoặc dùng file/env.
  6. Đã nghiệm thu Sol Reviewer 85/100 (APPROVED) và phủ 43 unit/integration tests xanh 100%. Xem chi tiết tại `references/dynamic-skill-routing-o1-against-context-bloat-20261022.md`.
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

## 2c. Kiểm tra & Đối soát Phân tầng Reasoning Coordinator (High) vs Worker (Medium) qua OmniRoute (:20129)

Khi cần kiểm chứng thực tế Coordinator hay Worker đang chạy Gemini High hay Medium (hoặc kiểm tra có bị lệch reasoning giữa các tầng):

### 3 Tầng kiểm tra O(1) không vi phạm Guard
1. **Kiểm tra cấu hình Hermes qua `manage_hermes_config.py`** (né blacklist `config.yaml`):
   ```bash
   python D:/Taadaa/tools/manage_hermes_config.py get agent.reasoning_effort
   python D:/Taadaa/tools/manage_hermes_config.py get agent.reasoning_overrides
   python D:/Taadaa/tools/manage_hermes_config.py get delegation
   ```
   - Chuẩn kiến trúc: Coordinator session chính chạy `agent.reasoning_effort: high`, `reasoning_overrides.omni-worker: high`.
   - Worker subagent chạy `delegation.reasoning_effort: medium`.

2. **Kiểm tra định tuyến Combo tại OmniRoute (`storage.sqlite`)**:
   - Query combo `omni-worker` trong `C:/Users/Kibe/.omniroute/storage.sqlite`:
     Tier 1 ưu tiên là `ag-gemini-pool-3` (`antigravity/gemini-3.8-flash-tiered`).

3. **Bóc tách Payload & Thinking Budget thực tế từ Call Logs**:
   - Query call gần nhất từ bảng `call_logs` trong `storage.sqlite` để lấy `artifact_relpath`.
   - Đọc trực tiếp file JSON tại `C:\Users\Kibe\.omniroute\call_logs\<artifact_relpath>`:
     - `requestBody.reasoning_effort`: hiển thị rõ `"high"` (Coordinator) hoặc `"medium"` (Worker).
     - Trong `open-sse/translator/request/openai-to-gemini.ts`:
       + `"high"` $\rightarrow$ `thinkingBudget: 32768`.
       + `"medium"` $\rightarrow$ `thinkingBudget: 8192`.
     - `tokens.reasoning` ghi nhận số thinking tokens thực tế trả về từ upstream Antigravity.

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
- Khuyến nghị vận hành khi user lo lắng bị nhồi:
  - Không lo lắng về System Prompt hay Tool Schemas (khung chuẩn 24k tokens).
  - Giải phóng lịch sử bằng `/new` ngay sau khi hoàn thành một chủ đề lớn để đưa request về lại ~24k tokens ban đầu.
  - Hạn chế để tool foreground dump log thô dài hàng nghìn dòng vào context.

### 3. Đối soát Định lượng Payload Thực tế & Triệt tiêu Trùng lặp Hệ Thống (Audit 25/10/2026)

Khi user yêu cầu kiểm tra trực tiếp log request lên OmniRoute (`C:\Users\Kibe\.omniroute\call_logs\`):
- **Phân bổ tải thực tế (Turn mở đầu):**
  - **System Prompt:** ~16.4k chars (~4.1k tokens).
  - **Tools Definitions (28 tools):** 61.1k chars JSON (~14.5k tokens).
  - **Base Overhead cố định:** ~18k - 19k tokens/turn.
- **3 Điểm nghẽn Trùng lặp & Rác schema phát hiện tại hiện trường:**
  1. *Tools Schema "Chết"*: `execute_code` (1.7k chars schema) bị Coordinator Guard chặn cứng (`COORDINATOR GUARD - EXECUTE_CODE DISABLED`) nhưng vẫn serialize schema gửi sang LLM mỗi turn. Cần disable hẳn toolset hoặc gỡ schema khỏi coordinator profile.
  2. *Bẫy trùng lặp Memory ↔ User Profile*: Memory (98% trần) và User Profile (96% trần) bị duplicate 100% các khối thông tin: Shift Pool 4d 3 ca, reboot né TFT/War3, quy chuẩn Bio/Tên TikTok, tracking vận đơn Shopee, và rule auto-heal. Cần dọn User Profile về đúng persona, chuyển quy trình farm sang Dynamic Skills O(1).
  3. *Trùng lặp Invariants trong System Prompt*: Chi tiết ngân sách O(1) L2 Emergency Surgery (<=2 files, <=30 dòng, 1 test focused, cấm đụng config/tools) và Circuit Breaker bị lặp lại từng câu chữ ở cả "Thang leo thang khi kẹt" và "6 Gates điều phối".
  4. *Quy cách Soạn tin Nhắn Mẫu (Telegram Mobile Copy UX)*: CẤM dùng blockquote `>` khi soạn tin mẫu cho User copy gửi người khác (Telegram mobile chỉ copy 1 dòng khi tap). BẮT BUỘC đóng gói trong code block ````text ... ```` độc lập, ngắn gọn, không nhồi reasoning để user tap 1 chạm là copy sạch 100% (chi tiết tại `hermes-gateway-ops/references/telegram-mobile-copy-ux-and-codeblock-formatting.md`).
- **Bài học từ Case Study `everything-everywhere-for-antigravity` (Kitchen-sink Anti-pattern):**
- Gom tĩnh 346 skills root + 325 skills plugins (11.440 files) nhồi vào session gây ngộ độc token (14k-18k tokens mô tả/turn), loãng chú ý (Attention Dilution), khiến model "fix lỗi này lòi lỗi khác" (local reasoning bị phá vỡ).
- Khẳng định tính ưu việt của Dynamic Skill Routing O(1): chỉ bốc đúng 3-5 skills theo intent query, giữ system prompt tinh gọn.

### 4. Triệt Tiêu Schema Tool Thừa & Tinh Gọn System Prompt (Audit & Thực Thi 27/10/2026)
- **Vô hiệu hóa Toolset Schema Thừa qua `agent.disabled_toolsets`**:
  * Các toolset không dùng hoặc bị Coordinator Guard chặn (`code_execution` cho `execute_code`, `tts` cho `text_to_speech`, `todo`) vẫn tự động serialize schema JSON gửi sang LLM mỗi turn (~3.500 ký tự JSON $\approx$ 900 tokens).
  * Khắc phục: Khóa cứng trong `config.yaml` bằng:
    `python D:/Taadaa/tools/manage_hermes_config.py set agent.disabled_toolsets '["code_execution", "tts", "todo"]' --type json --force`
  * **CẢNH BÁO GIỮ `computer_use`**: Tuyệt đối KHÔNG đưa `computer_use` vào `disabled_toolsets` nếu cần điều khiển desktop/PC nền, vì tắt tool này sẽ làm mất hoàn toàn khả năng chụp màn hình và tương tác UI Windows.
- **Bẫy Đối Soát Lỗi Thời (Stale Payload Audit Trap)**:
  * Tránh trích dẫn số liệu báo cáo cũ (vd report ngày 25/10 về việc trùng lặp Memory ↔ User Profile) khi user đã dọn sạch trong các session sau đó. Luôn kiểm tra hiện trường live trong prompt trước khi phán đoán.
- **User Sudo Tinh Gọn `SOUL.md`**:
  * Các đoạn văn chắp vá từ các đợt triage sự cố cũ trong `SOUL.md` (như chi tiết dirty target salvage triage dài dòng, câu chữ lặp ở Gate 5) có thể được user cấp quyền User Sudo để gọt bớt, tiết kiệm ~800 ký tự mà vẫn bảo toàn 100% Invariants cốt lõi.

### 4. So sánh Kiến trúc ChatGPT Web: OmniRoute Cluster (GPM CDP) vs Chrome Extension + Local MCP
- **Bản chất kiến trúc toy script (Extension + Local MCP):** Cắm extension vào 1 tab Chrome cá nhân, bóc tách DOM text để giả lập function calling và paste text thủ công.
- *Chí mạng Rate Limit:* 1 account Plus dính trần `40 msgs / 3 hours`, agent code loop 20-30 turns là kẹt cứng 3 tiếng.
- *Rủi ro Ban/WAF:* Tab web bị nhồi tool calling liên tục dễ kích hoạt Cloudflare Turnstile hoặc bot detection khóa nick.
- *Context Leaks:* Giao diện web cắt tỉa context sớm, nhanh hallucinate và quên chỉ dẫn.
- **Bản chất hạ tầng công nghiệp (OmniRoute + GPM CDP Pool):**
- *Chuẩn hóa API:* Đóng gói headless session thành chuẩn `/v1/chat/completions`, cắm trực tiếp vào Hermes, Cursor, Cline, Claude Code hỗ trợ native tool calling chuẩn JSON.
- *Failover & Concurrency:* Tự động xoay vòng (round-robin / least-used) giữa nhiều profile GPM; khi 1 account chạm trần tự chuyển account khác mà không làm đứt mạch agent loop.
- *Stealth & Isolation:* Gán cố định proxy residential/mobile 1:1, fingerprint sạch, giải quyết OTP qua Microsoft Graph API tự động.

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

### 0l. 🚨 Telegram Multi-ISP Failover Flapping, Unbounded Probe Hang & Bẫy Regression Heartbeat Interval (Incident 26/10/2026):
- **Triệu chứng**: Dashboard OmniRoute (`:20129`) hoàn toàn trống trơn 0 request suốt 10 phút 15 giây (`13:10:49` đến `13:21:04`), user gửi tin nhắn nhưng bot không nhận, không typing. Đến `13:20:26` bất ngờ xả dồn 7 tin nhắn cùng 1 giây, bùng nổ token 250k–470k tokens sang OmniRoute.
- **Nguyên nhân cốt lõi**:
  1. *Probe Recovery thiếu Timeout*: Trong `TelegramMultiISPTransport` (`plugins/platforms/telegram/telegram_network.py`), lệnh `resp = await self._get_primary().handle_async_request(req)` gọi trực tiếp trên transport mà không có `asyncio.wait_for(..., timeout=5.0)`. Khi WARP proxy (`127.0.0.1:40000`) vấp gói, probe bị treo ở mức socket hệ điều hành suốt 10 phút.
  2. *Mắc kẹt ở FPT Direct (Flapping 55 lần/ngày)*: Luồng probe bị đơ khiến gateway bị giam ở chế độ `FALLBACK (FPT Direct)`. Tại Việt Nam, FPT Direct chặn/bóp long-poll `getUpdates` của `api.telegram.org` $\rightarrow$ không tin nhắn nào lọt về gateway $\rightarrow$ OmniRoute 0 request trong 10 phút.
- **🚨 Bẫy Regression Cần Tránh (User Correction 26/10/2026)**:
  TUYỆT ĐỐI KHÔNG hạ `HERMES_TELEGRAM_HEARTBEAT_INTERVAL` từ 180s xuống 30s! Lịch sử ngày 28/09 cho thấy để interval ngắn sẽ khiến probe `get_me()` nhạy cảm tự sát khi mạng lag 1s, kích hoạt chuỗi phạt Exponential Backoff (5–10 phút).
- **Kiến trúc Chuẩn Dual-Proxy Failover (WARP ↔ Viettel Proxy)**:
  - Khai báo `TELEGRAM_FALLBACK_PROXY=http://192.168.110.2:10001` (Router Viettel farm) thay vì ép đi FPT Direct. Cả hai tuyến đều là proxy vượt tường lửa, trễ <1s.
  - Bọc `asyncio.wait_for(..., timeout=5.0)` cho lệnh probe và thêm debounce 2-3 nhịp trước khi kích hoạt failover.
  - Xem chi tiết tại `references/telegram-multi-isp-flapping-and-dual-proxy-failover.md`.

### 0m. 🚨 OmniRoute Proxy Cascade ECONNRESET, Event Loop Deadlock Ceiling & Watchdog Restart Window (26/10/2026 Incident):
- **Triệu chứng**: Dashboard OmniRoute (`:20129`) trống trơn 0 request suốt 10-20 phút; đúng lúc 17:07 User gửi tin vào Telegram thì 5+ topics đồng loạt văng: `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- **Bẫy nghi ngờ nhầm**: Tưởng do "session nào đó tự ý giảm timeout". Thực tế cấu hình timeout hoàn toàn nguyên vẹn (`gateway_timeout: 3600`, `api_max_retries: 3`, `child_timeout_seconds: 900`).
- **Nguyên nhân cốt lõi (Chuỗi sự cố)**:
  1. *Bão rớt cụm Proxy Mobile (`test.taadaa.click:51xx`)*: Cụm proxy 5103..5115 đồng loạt văng `ECONNRESET / PROXY_UNREACHABLE` đúng lúc stream payload nặng >405k tokens khiến Main Event Loop của Node.js bị **khóa cứng (Deadlock)** suốt gần 6 phút (16:59:52 đến 17:05:32).
  2. *Watchdog Deadlock Ceiling Force-Restart*: Sau 12 lần fail `/api/health` liên tiếp (30s x 12 = 6m), watchdog `omniroute_watchdog.ps1` kích hoạt `deadlock ceiling reached` force-kill toàn bộ Node.js.
  3. *Cửa sổ chết 17:05 – 17:07:52*: Quá trình restart lần 1 vấp lỗi exit code 1, lần 2 mất 24s. Trong 2 phút này port 20129 đóng hoàn toàn $\rightarrow$ Các tin nhắn gửi đúng lúc 17:07 bị Connection Refused và văng lỗi đồng loạt trên Telegram.
  4. *Tử huyệt Retry Headroom Hermes quá ngắn*: `agent.api_max_retries: 3` chỉ đợi ~15-18s (backoff ~2s, 4s, 8s). Khi OmniRoute restart mất ~25-30s, Hermes đốt sạch 3 lần thử trước khi port 20129 mở lại, làm fail turn hàng loạt và ép user phải gõ lại tin nhắn từng topic.
- **Biện pháp xử lý & Chuẩn hóa**:
  - Nâng retry headroom: `python D:/Taadaa/tools/manage_hermes_config.py set agent.api_max_retries 6 --type int` (trải dài chuỗi retry ~122s, đảm bảo bắt kịp thời điểm OmniRoute vừa restart xong mà không ngắt turn).
  - Hạ trần `$MaxDeadlockFailures` trong `omniroute_watchdog.ps1` từ 12 xuống 4 (~2 phút) để đồng bộ với cửa sổ chờ của Hermes.
  - Tách `fallback_providers` độc lập (trỏ sang 9Router `:20128` thay vì trỏ lại chính cổng 20129).
  - Xem chi tiết tại `references/omniroute-restart-retry-headroom-and-deadlock-ceiling-20261026.md`.

### 0n. 🚨 Triage Nhanh: Phân Biệt Lỗi Telegram Mạng vs Lỗi OmniRoute Model Provider ("The model provider failed after retries") (26/10/2026 Incident):
- **Hiện tượng**: Bot xuất hiện thông báo: `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.` sau banner `Working — N min — iteration X/100`. User phân vân hỏi: *"Lỗi Telegram hay Omni nữa?"*.
- **Bản chất**:
  1. Dòng chữ `The model provider failed after retries` là lỗi tầng **Model Provider API** (OmniRoute / LLM upstream) khi Hermes thử lại đủ số lần `api_max_retries` mà vẫn fail. Không phải lỗi giao thức Telegram.
  2. Kích hoạt bởi hiệu ứng cộng hưởng đứt mạng ISP: Khi mạng Viettel chập chờn $\rightarrow$ Gateway chuyển sang FPT Direct $\rightarrow$ FPT bị lỗi kết nối ra ngoài $\rightarrow$ Proxy Mikrotik của OmniRoute (`http://mirotik1.taadaa.click:10017`) không đến được Google Antigravity $\rightarrow$ Kích hoạt `[Proxy Fast-Fail] Proxy unreachable` $\rightarrow$ OmniRoute trả về `HTTP 503: Service temporarily unavailable: all targets were skipped by pre-dispatch filters` $\rightarrow$ Hết ngân sách retry Hermes.
- **Kỷ luật chẩn đoán O(1) Guard-Safe**:
  - Không gõ bash đường dẫn hệ thống hay lệnh `curl` (bị Guard chặn đứng).
  - Tra cứu log qua Python với `Path(os.environ.get('LOCALAPPDATA', '')) / 'hermes' / 'logs'`, tìm `failed after retries` và `Proxy Fast-Fail`.
  - Kiểm tra trạng thái cổng `:20129` bằng `urllib.request`.
  - Xem chi tiết tại `references/model-provider-failed-after-retries-triage.md`.

### 0o. 🚨 Protection Regression Gate cho Hạ Tầng Hermes & OmniRoute (`infra_regression_gate.py` - 26/10/2026)
- **Chỉ thị User Bắt Buộc**: Mọi chỉnh sửa cấu hình Hermes (`config.yaml`) hoặc OmniRoute Watchdog (`omniroute_watchdog.ps1`) BẮT BUỘC phải thỏa mãn bộ Invariant lịch sử, cấm sửa mò theo triệu chứng gây tái phát sự cố.
- **Tích hợp cơ giới hóa**: `manage_hermes_config.py set` tự động gọi `infra_regression_gate.py`. Nếu vi phạm Invariant $\rightarrow$ Hard-block ngay (exit code 4).
- **Bộ Invariant hạ tầng chuẩn**:
  1. `compression.threshold`: Bắt buộc trong `[0.28, 0.35]` (chuẩn `0.30`). Cấm <0.28 (lặp nén liên tục 120k ctx 03/10) và cấm >0.35 (chạm trần 372k GPT worker 11/08).
  2. `agent.api_max_retries`: Bắt buộc trong `[3, 4]`. Cấm >4 (tránh Thundering Herd 503 storm 02/10) và cấm <3 (tránh fail sớm khi restart).
  3. `agent.api_retry_delay`: Bắt buộc trong `[5.0, 12.0]` (chuẩn `6.0s`).
  4. `Retry Headroom`: Tổng chờ `sum(delay * 2^i)` bắt buộc trong `[70s, 130s]` (đủ đón restart 111s, không quá trần Telegram).
  5. `fallback_providers`: CẤM trỏ vào chính nó (port 20129).
  6. `omniroute_watchdog`: `$MaxDeadlockFailures` bắt buộc trong `[4, 6]` (tránh false-kill <4 và tránh treo lâu >6).
- **Unit test**: `pytest D:/Taadaa/tools/tests/test_infra_regression_gate.py` (8/8 passed). Xem chi tiết tại `references/infra-protection-regression-gate-20261026.md`.

### 0p. 🚨 Sự Cố Fast-Fail Probe 2s Kill Oan Stream & SQLite 1.15GB Lock Event Loop (Incident 27/10/2026):
- **Triệu chứng**: Cả ngày OmniRoute báo sập liên tục, trả về `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` (>130 lần). Người dùng kiểm tra proxy bên ngoài vẫn sống 100% (ping 50ms, curl IP xoay sạch). Thỉnh thoảng OmniRoute bị treo cứng 6 phút khiến Watchdog force-kill tiến trình.
- **Nguyên nhân gốc rễ (3 tầng)**:
  1. *Mạng Viettel flapping >120 lần/ngày*: Packet drop ngắn 1–2s làm trễ TCP SYN.
  2. *Bẫy so găng Fast-Fail Probe 2s (`proxyFetch.ts:681 Promise.race`)*: Probe TCP 2s (`FAST_FAIL_TIMEOUT_MS=2000`) chạy song song với request LLM (15s–45s). Khi mạng lag 2.1s, probe kết luận proxy chết và **FORCE-KILL REQUEST LLM ĐANG GENERATE DỞ**. Cả 28 account Antigravity cùng cụm `test.taadaa.click:51xx` bị gạt bỏ sạch trong 5s $\rightarrow$ 503 `ALL_TARGETS_SKIPPED`.
  3. *SQLite 1.15GB (>1.06 triệu dòng) làm nghẽn Event Loop*: Bảng `conversation_turn_nodes` (1.06M rows) và `quota_snapshots` (418k rows) tích tụ không được dọn dẹp do cron cũ chỉ giữ 7 ngày và bỏ sót 4 bảng nặng. I/O lock đồng bộ trên Main Event Loop Node.js làm `/api/health` fail 12 lần liên tiếp $\rightarrow$ Watchdog force-kill.
- **Biện pháp xử lý & Chốt chặn Invariant**:
  1. *Nâng trần Probe TCP*: Đặt `PROXY_FAST_FAIL_TIMEOUT_MS=5000` (5s) trong `omniroute_watchdog.ps1` và `server.env`.
  2. *Khóa an toàn Farm IP*: Giữ nguyên `PROXY_FAIL_OPEN=false` để cấm tuyệt đối việc rò rỉ Direct IP dân cư nhà Kibe làm ban nick farm.
  3. *Prune 1.14M dòng rác & Cron 6h*: Cập nhật `cleanup_omniroute_db.py` với retention 3 ngày, bao trọn 6 bảng nặng và nâng lịch cron `daily-omniroute-db-cleanup` lên chạy mỗi 6 giờ (`every 6h`).
  4. *Delay socket TIME_WAIT*: Bổ sung `Start-Sleep -Seconds 3` vào đầu hàm `Start-OmniRoute` của Watchdog để tránh lỗi restart văng `exit code 1` sau 3 giây.
  5. *Protection Regression Gate*: Đã tích hợp đầy đủ vào `infra_regression_gate.py` với 12/12 unit test xanh 100%. Xem chi tiết tại `references/omniroute-proxy-fast-fail-probe-hang-and-sqlite-bloat-20261027.md`.

## References
- `references/omniroute-proxy-fast-fail-probe-hang-and-sqlite-bloat-20261027.md` — Sự cố Fast-Fail probe 2s kill oan stream LLM khi Viettel chập chờn, phình SQLite 1.15GB (1.14M dòng rác), và toàn bộ giải pháp hạ tầng kèm Protection Regression Gate (27/10/2026).
- `references/omniroute-fast-fail-probe-and-protection-regression-gate.md` — Chi tiết bẫy Fast-Fail probe 2s làm kill oan request LLM, sự cố SQLite 1.15GB phình 1.14M dòng, và bản thiết kế Protection Regression Gate cho hạ tầng (27/10/2026).
- `references/omniroute-proxy-fast-fail-false-kill-and-infra-regression-gate.md` — Bẫy so găng Fast-Fail 2s tự kill request stream, phình SQLite 1.14M dòng, và chốt chặn Protection Regression Gate cho hạ tầng (27/10/2026).
- `references/omniroute-proxy-fast-fail-race-and-sqlite-bloat-20261026.md` — Sự cố Proxy Fast-Fail 2s so găng abort oan request LLM (15s-45s) trên proxy sống, bão 130x all targets skipped và SQLite 1.06M rows gây deadlock Event Loop (26/10/2026).
- `references/infra-protection-regression-gate-20261026.md` — Cơ chế Protection Regression Gate (infra_regression_gate.py) tự động chặn đứng các đột biến cấu hình vi phạm Invariant hạ tầng Hermes & OmniRoute (26/10/2026).
- `references/model-provider-failed-after-retries-triage.md` — Phân định dứt khoát lỗi Telegram vs lỗi Model Provider OmniRoute, hiệu ứng cộng hưởng Multi-ISP và bộ lệnh probe Python Guard-Safe (26/10/2026).
- `references/omniroute-restart-retry-headroom-and-deadlock-ceiling-20261026.md` — Đồng bộ Retry Headroom (api_max_retries: 6) cho Hermes, phân tích cửa sổ chết OmniRoute restart 30s và hạ trần watchdog deadlock ceiling (26/10/2026).
- `references/omniroute-deadlock-ceiling-and-proxy-cascade-restart.md` — Sự cố OmniRoute Event Loop Deadlock do bão rớt proxy mobile ECONNRESET, Watchdog Deadlock Ceiling 12/12 force-restart và cửa sổ chết 17:05-17:07 văng lỗi Telegram đồng loạt (26/10/2026).
- `references/telegram-multi-isp-failover-probe-hang.md` — Sự cố Telegram Multi-ISP Failover flapping, probe thiếu timeout làm treo 10 phút và xả dồn tin nhắn (26/10/2026).
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
- `references/scheduled-reboot-and-session-preservation-triage.md` — Quy trình triage Auto-Reboot 3 ca (05:20, 11:20, 17:20), cơ chế bảo toàn session in-flight và phân biệt hiện tượng khựng shutdown sạch vs crash sập nguồn (19/10/2026).
- `references/dynamic-skill-routing-o1-against-context-bloat-20261022.md` — Giải pháp Dynamic Skill & Error Routing O(1) chống Context Bloat và [SKILL_PRUNED] cho 190+ skills, cơ chế fail-closed pinned invariants, và bài học Operator chấn chỉnh bệnh nịnh bợ flip-flop (22/10/2026).
- `references/payload-and-schema-audit-20261025.md` — Báo cáo đối soát định lượng payload thực tế từ call log OmniRoute, bóc tách 18.6k tokens base overhead, dead schema `execute_code`, trùng lặp Memory ↔ User Profile và case study kitchen-sink anti-pattern (25/10/2026).
- `references/tool-calling-iteration-limit-and-turn-budget-exhaustion.md` — Chẩn đoán trần lặp công cụ per-turn (MAX_TOOL_CALL_ITERATIONS), kỷ luật chống bại liệt/khóc lóc khi bị ép dừng và giải pháp nâng trần runtime (26/10/2026).
- `references/intermittent-hang-triage-and-guard-safe-probes.md` — Triage hiện tượng "thỉnh thoảng treo 5-10 phút", phân biệt treo máy tính vs treo bot/webhook backoff, và bộ lệnh probe Python thuần guard-safe (26/10/2026).
- `references/provider-restart-retry-tuning-and-deadlock-conflict-20261026.md` — Tinh chỉnh cửa sổ retry Hermes khi Provider restart (api_max_retries: 4, api_retry_delay: 6.0s ~90s) và đối soát tránh mâu thuẫn Thundering Herd / Watchdog Deadlock / Anti-Flapping (26/10/2026).
- `references/omniroute-fast-fail-probe-false-kill-and-sqlite-bloat-20261027.md` — Sự cố OmniRoute sập do Fast-Fail probe 2s kill oan stream khi mạng Viettel jitter, SQLite phình 1.15GB (>1.14M rows) và kiến trúc phân định Regression Gate vs Protection Invariant Gate (27/10/2026).
- `references/provider-failure-session-preservation-and-time-wait-anatomy.md` — Cấu trúc lỗi Model Provider Failed, bảo toàn session trong SQLite không mất context (resume O(1) bằng dấu '.') và tử huyệt TIME_WAIT socket 111s khi Watchdog restart (26/10/2026).
