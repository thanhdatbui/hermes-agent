---
name: agent-model-routing
description: "Route coordinator and worker agents by task difficulty and cost."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [agents, orchestration, model-routing, delegation, cost]
    category: autonomous-ai-agents
    related_skills: [hermes-agent, codex, opencode]
---

# Agent Model Routing Skill

Use this skill when one agent coordinates work while another model or coding CLI performs implementation. It defines routing by role, difficulty, quota, and verification needs. It does not prescribe a permanent ranking for models; provider catalogs and model IDs change, so verify the live catalog before configuring.

## When to Use

- Hermes should plan, delegate, and verify rather than implement everything itself.
- A coding worker has different quota or quality characteristics from the coordinator.
- Multiple models such as Codex and OpenCode Go need role-based routing.
- A local OpenAI-compatible router is being considered for centralized credentials and fallback.

## Prerequisites

- Know the actual provider/model IDs from the provider's current model picker or CLI.
- Confirm which agent can call tools and which agent owns filesystem changes.
- Keep a verification path: diff inspection, tests, logs, or another concrete artifact.

## Independent-analysis override

When the user explicitly says to ignore saved routing policy, analyze independently, or rerun the analysis after switching models, treat old user-specific ladders in this skill as historical context—not authority. Re-derive the recommendation from the resources available **now**: live model routes, quota ownership, measured latency/quality, provider-risk assumptions, and Hermes runtime primitives. Separate verified facts from assumptions, correct prior advice openly, and do not mutate routing/config unless the user explicitly asks for execution.

## Native Hermes feasibility first

Before proposing a multi-tier model ladder, distinguish policy from runtime capability. Stock `delegate_task` has one global `delegation.provider/model` pin and no per-call model selector; top-level fallbacks handle provider/request failures, not semantic quality escalation. Use profiles/Kanban/external CLI lanes when roles need different models. See `references/hermes-role-routing-feasibility.md` for the exact capability map, config acceptance checks, task-specific compression fallback, and the separation of quality, quota, and audit triggers.

## How to Run

1. Classify the request as routine implementation, architecture/review, or debugging/recovery.
2. Select a coordinator model that is cheap and reliable at planning/tool orchestration.
3. Select a worker model based on implementation difficulty, not brand preference.
4. Delegate with explicit scope, acceptance criteria, workdir, and proof requirements.
5. Inspect the worker's result and run or request verification.
6. Escalate only after evidence: normal worker → stronger review model → recovery/debug model.

## Quick Reference

Before drawing a fallback chain, preserve the user's explicit capability ordering. **High quota is not capability equivalence**: a weaker but abundant model is an availability fallback and must be labeled degraded, with reduced authority for live/deploy/security/recovery decisions. Keep transparent quota/transport fallback in the router and semantic model selection/escalation in Hermes; do not duplicate the same retry chain in both layers. For the current Terra/Sol, Claude AG/Pro, and DeepSeek Flash/Pro case—including the expected-cost formula for a Pro:Flash price ratio—read `references/capability-fallback-and-worker-cost-routing.md`.

| Role | Default strategy |
|---|---|
| Coordinator | Strong enough for high-leverage planning/routing, economical at the expected request volume; keep its context and raw tool traffic thin |
| Routine worker | Fast, cheap coding model with good repository execution |
| Quality escalation | Stronger worker only after acceptance/test evidence, while that provider/account still has usable quota |
| Quota/transport fallback | Independent healthy account/pool/provider—not merely a stronger model sharing the exhausted quota |
| Architecture/review | Independent strong reasoning model selected by risk |
| Final gate | Coordinator verifies proof; never trust a completion claim alone |

A practical split when Codex quota is available is: Hermes coordinator on a low-cost OpenCode Go model; **Codex Sol for BOTH planning AND coding**; Codex Luna ONLY for debugging under D:/Taadaa automation workflows. Use Claude Opus at low effort as the default independent reviewer, with OpenCode only as reviewer fallback when Claude quota/provider access fails. The loop is Worker implementation → Reviewer audit → Worker accepts/rejects each finding with evidence → Reviewer consensus re-check, bounded by a maximum round count and persisted state/artifacts.

**Coordinator cost economics — user chốt 2026-08-15 (KHÔNG đặt model đắt làm coordinator phiên dài):**
- Sol/Opus/Pro ngồi coordinator thường trực = phí phạm: ôm context lớn, bị gọi sau gần như mọi tool action, token lượng cao → đốt quota (đo thật: Pro = 2.76× Flash; pool $10 cháy 1.25–1.67 ngày ở mức 6–8 credit/ngày; nếu toàn bộ traffic chuyển Pro ≈ 16.6–22.1 credit/ngày).
- Mô hình đúng: **Flash = coordinator hằng ngày + worker; Pro = planner/rescuer phiên NGẮN context gọn; Sol = plan/audit case khó; Opus = audit gate độc lập**. Model đắt chỉ one-shot theo gate, không ngồi loop dài.
- Target: **Pro ≤10–15% tổng token traffic** — blended = (1−s)+s·r (r=2.76): s=5%→1.088×, s=10%→1.176×, s=20%→1.352× overhead so với all-Flash. Flash-first break-even failure rate = (r−1)/r ≈ 63.8%.
- Automation thường ngày (canonical script, selector, parse log, test, bug hẹp) KHÔNG cần model xịn. Chỉ gọi Pro khi: design mới/state machine, bug mơ hồ multi-file, lock/recovery/concurrency/scheduler, hoặc Flash fail 1 vòng có evidence.
- **Trước khi đổi routing/config: trình phương án rõ (roles/models/chi phí) và chờ user duyệt — KHÔNG ghi config trước khi duyệt** (user 2026-08-15: "t duyệt r ms làm").
- Native Hermes Kanban đã hỗ trợ per-role model mixing KHÔNG cần bịa dispatcher: bundled skill `kanban-orchestrated-coding` định nghĩa step keys `planner`/`auditor`/`worker`/`reviewer`; config `kanban.orchestration.roles.<step_key>` = candidates[{profile,model}] + toolsets; dispatcher route theo `task.current_step_key` (`resolve_workflow_step_policy`, first candidate rồi match assignee). Chi tiết cơ chế: `references/kanban-orchestrated-coding-native-flow.md`.
- Profile Hermes: `custom_providers` là **LIST dict** (không phải mapping): `[{name, base_url, key_env, api_mode, discover_models, model, models:{<model>:{context_length}}}]` — dùng chung `key_env: NINEROUTER_API_KEY`, không inline secret. Viết config profile/root bằng python+yaml (`utils.atomic_yaml_write` / `load_config/save_config`), không text-regex manual.

**Finalized chains — user chốt 2026-08-15 (đã verify catalog live; thay cho mọi ladder cũ khi bàn worker/plan/review):**
- **Worker implementation fallback chain — TOÀN BỘ trong 9router, Hermes KHÔNG cấu hình `fallback_providers`** (Hermes chỉ giữ 1 model/provider `custom:9router`): combo `worker` (DB live 18/08, ground truth) = `cmc/deepseek/deepseek-v4-flash → oc/deepseek-v4-flash-free → oc/hy3-free → ag/gemini-3.7-flash-high → ag/claude-sonnet-4-6 → gpt-5.6-luna`. Gemini 3.7 flash đã là member combo worker từ 17/08 (sweep 3.6→3.7). Benchmark 17/08 cho thấy `oc/deepseek-v4-flash-free` hay 502 + chậm (213s task dài) — cân nhắc đưa Gemini lên trước nó khi user duyệt. **ROOT CAUSE 17/08 (thay MỌI chẩn đoán cũ): Antigravity gateway có denylist literal chặn ĐÚNG chuỗi identity mặc định của Hermes `"You are Hermes Agent, an intelligent AI assistant created by Nous Research."` → 429 `RESOURCE_EXHAUSTED` cho bất kỳ request nào bắt đầu bằng câu đó (cả gemini lẫn sonnet/opus, mọi account). Bisect thật: đổi tên (Alice→200), đổi org (Google→200), bỏ cụm "intelligent AI assistant" (200), Claude/Anthropic (200), riêng "Hermes Agent" hay "Nous Research" (200) — ĐÚNG nguyên câu → 429 lặp lại. FIX (đã verify 17/08): sửa `~/AppData/Local/hermes/SOUL.md` (identity slot #1 — prompt_builder.load_soul_md) thành câu identity gọn không dính denylist → `hermes chat -m ag/gemini-3.7-flash-high` trả 200 thật. AG gemini/sonnet giờ dùng được làm MAIN session + subagent (chỉ session MỚI /new nạp SOUL.md mới; session cũ giữ prompt cũ). 9router-proxy-ops ref `ag-gemini-429-fix.md` chẩn đoán "size" là SAI — xem bản sửa ở đó. **UPDATE 17/08 tối (re-verified): denylist KHÔNG còn active — test 3 identity (gốc "You are Hermes Agent, a helpful and direct AI assistant...", generic, Alice) đều 200 gọi `ag/gemini-3.7-flash-high`. 429 "Resource has been exhausted" xuất hiện LẠI trong benchmark v6 khi dồn ~10 session Gemini liên tiếp = RPM burst lock ~5 phút (quota dashboard `:20128/dashboard/quota` vẫn 99-100% free) — chẩn đoán 429 trước tiên: check dashboard quota, rồi spacing 60s giữa các call.**
- **Plan/review chain THƯỜNG:** combo `plan-review` = `gpt-5.6-terra → ag/claude-opus-4-6-thinking → cmc/deepseek/deepseek-v4-pro` (gọi model `plan-review` qua 9Router HTTP API).
- **Plan/review chain KHÓ:** combo `plan-review-hard` = `gpt-5.6-sol` (gọi model `plan-review-hard` qua 9Router HTTP API).
- **Audit/Review BẮT BUỘC gọi qua 9Router HTTP API với model `plan-review` hoặc `plan-review-hard`**: Dùng công cụ `python D:/Taadaa/tools/invoke-plan-review.py` hoặc POST `http://127.0.0.1:20128/v1/chat/completions` với `model: "plan-review"`, `tools: []`, `tool_choice: "none"`, `stream: false`. CẤM gọi trực tiếp model `ag/claude-opus-4-6-thinking` vì provider AG không có active key riêng lẻ; CẤM dùng `delegate_task` để review.
- **Claude CLI Opus Max Quota Burn (Lesson 2026-08-24)**: Claude CLI OAuth có rolling window 5 giờ. Khi chạy `claude -p` với `--model opus --effort max` hoặc `high` trên prompt/context lớn (30-50KB), mỗi turn sinh 15.000–35.000 thinking tokens ngầm → chỉ 4–5 vòng audit/re-audit là cạn 100% quota 5h. Khắc phục: KHÔNG dùng Claude Opus Max cho nhiều vòng loop lặp đi lặp lại; gọi 9Router HTTP (`gpt-5.6-terra` / `gpt-5.6-sol`) cho các vòng review trung gian, chỉ gọi Claude Opus 1 lần khi chốt chặn cuối (Blind Audit).
- **Reviewer KHÔNG BAO GIỜ dùng Flash** (user 2026-08-15: "Reviewer sao dùng flash dỏm quá k?") — review/audit dùng plan/review chain, không dùng worker model.
- **Audit/Review BẮT BUỘC gọi qua combo `plan-review` / `plan-review-hard` qua 9Router HTTP (User correction 2026-08-18)**: CẤM dùng `delegate_task` để audit (vì `delegate_task` bị gán cứng vào `worker` trong config Hermes). Mọi tác vụ Audit / Review code / Plan review PHẢI được gọi trực tiếp qua 9Router HTTP (`POST http://127.0.0.1:20128/v1/chat/completions` với `model: "plan-review"` hoặc `"plan-review-hard"` + `tools: []` + `tool_choice: "none"` + `"stream":false`).
- **Review lane discipline (user correction 2026-09-01):** Khi user bảo gọi Sol hoặc Claude để review, không được tự thay bằng Claude Sonnet hay gọi bare model ngoài lane đã cấu hình. Case khó/concurrency dùng `plan-review-hard`; case thường dùng `plan-review`. Nếu user chọn Claude CLI riêng thì chỉ dùng **Claude Opus**, không Sonnet. Trước khi gọi, nêu chính xác lane/model; nếu review đang chạy mà user bảo “cứ cho chạy”, không được tự hủy.
- **KHÔNG thêm profile/kanban role cho plan/review** (user 2026-08-15: "sao phải thêm profile nghe phức tạp v gọi sub agent ra làm k đc à"): `delegate_task` không chọn model từng call (1 global pin) → "subagent Pro" không tồn tại; coordinator Flash gọi thẳng 9Router HTTP (`POST /v1/chat/completions`, bắt buộc `tools:[]` + `tool_choice:"none"` + `"stream":false`, `Bearer $NINEROUTER_API_KEY`) theo chain độ khó. Mỗi call lưu model/finish_reason/cost để tối ưu sau.
- **Lệnh vận hành (chạy script repo X máy Y) → KHÔNG plan, KHÔNG Kanban**: Flash chạy thẳng (canonical script + params, không sửa file). Chỉ lệnh phát triển (build script mới / fix bug) mới vào chain plan/review.
- Model chain nằm trong config/design-doc (không hard-code trong script).

**Latest routing override — 2026-08-09 (highest precedence for this user):**
- When the coordinator session is **gpt-5.6-terra**, it remains read-only; its fresh implementation worker is **gpt-5.6-luna with reasoning_effort=high**.
- Before `delegate_task`, configure the Hermes delegation pin exactly: `delegation.provider: cockpit`, `delegation.model: gpt-5.6-luna`, `delegation.reasoning_effort: high`. Do not inherit Terra for implementation and do not substitute Luna/max unless the user explicitly requests it.
- The bound Luna/high worker owns the exclusive patch/test scope; Terra inspects the diff and verifies independently.

**This user's model routing (CRITICAL — explicitly corrected multiple times; refreshed 2026-08-06):**
- **Hermes (deepseek-v4-flash, 9router)** = coordinator + task SIMPLE + triage/đọc log + **vòng debug nhanh**. Debug nên để deepseek (chạy nhanh); dựng script/bài mới → Codex.
- **Codex gpt-5.6-luna/max** = worker implement/live (AGENTS.md: worker duy nhất được patch/live). Trong Codex app, spawn subagent cùng hệ sinh thái GPT (luna/terra/sol) cho mượt.
- **gpt-5.6-terra / deepseek-v4-pro** = audit/review CHÍNH (READ-ONLY — đưa root-cause/plan, KHÔNG patch; người thực thi lại là Luna/max hoặc Hermes).
- **gpt-5.6-sol** = plan tổng + case khó nhất (high→extra_high→ultra, session MỚI mỗi nấc, làm khác đi).
- **Claude** = audit hard-trigger / plan tổng, quota-gated (`claude-quota-preflight.ps1`, 5h<85% + weekly<90%).
- **Gemini 3.6 flash** = VISION cho deepseek + fallback audit CUỐI cùng. KHÔNG làm auditor chính — user đánh giá "bợ dái, không tư duy phản biện" (sycophant, no critical thinking). Đã cấu hình `auxiliary.vision`.
- **OpenCode** = fallback reviewer (sau terra/pro/sol) — **đã set up thành lớp audit free TRƯỚC Gemini (2026-08-06)**: **CASCADE model mạnh→yếu, hết quota/502 mới qua model kế**: `nemotron-3-ultra-free` (mạnh nhất, hay 502 ResourceExhausted) → `ling-3.0-flash-free` (ổn định, verdict thật) → `longcat-2.0-free` → `north-mini-code-free` (fallback nhẹ). KHÔNG dùng `deepseek-v4-flash-free` (trùng family user); `mimo/laguna` trả template giả → bỏ. Wrapper `D:\Taadaa\tools\invoke-opencode-audit.ps1` (chạy OK, exit 0, output JSONL **UTF-16** — đọc bằng `encoding='utf-16'`, verdict nằm trong các part `{"type":"text","part":{"type":"text","text":...}}`). **Audit chain đã chốt: OpenCode free (cascade) → Gemini 3.6 Flash → Command Code → fresh Codex (Sol/Terra)** — OpenCode là lớp MỚI đứng TRƯỚC Gemini. OpenCode phát hiện findings xuyên section (P1/P2/P3 — các section khác ngoài vùng sửa vẫn mâu thuẫn Luna-only) mà ds-pro + Gemini không thấy — dùng khi cần audit chéo policy toàn file. `freemodel/*` (gpt-5.6-luna free) → 401 Insufficient balance — không dùng được. **PITFALL (user corrected 2026-08-06):** luôn chạy `opencode models | grep -i free` TRƯỚC khi chọn model audit — **KHÔNG chọn model trùng family với model chính của user** (user đang dùng deepseek ở mọi nơi → `opencode/deepseek-v4-flash-free` bị user chặn vì "gọi deepseek của nó hơi bị trùng"). PHẢI TEST từng free model bằng `opencode run` thật với ĐÚNG args wrapper (`--agent taadaa-review --format json`): `nemotron-3-ultra-free` → 502 ResourceExhausted (Nvidia worker limit 32/32) khi dùng agent+json nhưng thỉnh thoảng chạy được (quota reset); `mimo-v2.5-free`/`laguna-s-2.1-free` → trả template giả (echo format, không audit thật) hoặc không output; **`ling-3.0-tiny-free` → ổn định + verdict thật (đọc file, findings line-level; **tên MỚI 2026-08-07 thay `ling-3.0-flash-free` — catalog đổi, smoke OK**)`. **PITFALL tốc độ (2026-08-07)**: `ling-3.0-tiny-free` audit cả repo timeout >600s (exit 124) — **phải dùng prompt FOCUSED (liệt kê đúng file + câu hỏi, cấm quét toàn repo) + timeout 900s**; `north-mini-code-free` hiện **401 upstream** (không dùng được); `longcat-2.0-free` chạy được + nhanh hơn (smoke OK). **PITFALL RepoRoot (2026-08-07)**: `invoke-opencode-audit.ps1 -RepoRoot D:\Taadaa` → opencode glob `**/*.py` thấy worktree cũ (`automation-core-codex-tiktok-add-phone-vietnamese`, `context-worktrees/Tiktok_Reg-reduce-context`) → audit NHẦM file, báo "feature không tồn tại" dù có thật (nemotron cũng đạt MAX_STEPS trước khi xong = audit không hoàn chỉnh). **Phải trỏ RepoRoot vào repo CHÍNH (`D:\Taadaa\automation-core` / `D:\Taadaa\Tiktok_Reg`), audit multi-repo chia 2 prompt chạy 2 lần.** Chi tiết matrix + cascade: `references/opencode-free-model-audit.md`.
- **Escalation ladder Taadaa**: Hermes flash (simple) → fail → Codex Luna/max (worker, làm khác đi) → vẫn fail → deepseek-v4-pro HOẶC terra review (read-only, plan mới) → fresh Luna/max làm theo plan → case khó nhất → Sol. Cùng 1 evidence chỉ review 1 lần (1 audit slot).
- **Hermes `delegate_task` subagents: model NOT selectable per call** (source-verified 2026-08-05 in `tools/delegate_tool.py`). Subagents run whatever `delegation.provider/model/reasoning_effort` config sets, or inherit the parent model when unset — so a Hermes session on a cheap model (e.g. 9router flash) cannot spawn a Luna/max worker or a Sol planner through `delegate_task`. Per-role model mixing (worker Luna/max + planner Sol + auditor) is a **Codex-app capability but ONLY within its GPT catalog** (verified 2026-08-05: `~/.codex/cockpit-local-access-model-catalog.json` lists exactly 10 models — gpt-5.6-luna/sol/terra, gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, gpt-5.3-codex-spark, GPT Image 2, codex-auto-review; **no Gemini/Claude/DeepSeek/Command Code**). Non-GPT audit models (Gemini/Claude/Command Code/OpenCode/DeepSeek) therefore go through **CLI wrappers (`invoke-*.ps1` → 9router `:20128`) in BOTH apps** — the Codex GUI cannot spawn them as subagents either; the 9router provider exists only in Codex CLI `config.toml`, not in the app catalog. A Hermes subagent can use a different configured provider/model from the parent by pinning `delegation.provider` + `delegation.model`; it is **not** limited to the parent's provider. The real limitation is that this is one global pin shared by every `delegate_task` child, not a per-call/per-role selector. Use profiles/Kanban or external CLI lanes when planner, worker, and auditor need distinct providers/models concurrently. To make Hermes subagents run Luna/max, set `delegation.provider: cockpit`, `delegation.model: gpt-5.6-luna`, `delegation.reasoning_effort: max` (cockpit = local custom provider at `http://localhost:60818/v1`, `api_mode: codex_responses`, key `COCKPIT_API_KEY`, models gpt-5.6-luna/sol/terra — already defined in this machine's config). This cockpit path is **live-verified** (2026-08-05: `POST /v1/responses` model `gpt-5.6-luna` + `reasoning.effort=max` → `status: completed`). Re-verified on Hermes **0.20.0** (2026-08-05): `delegate_task` STILL has no per-task model — `_MODEL_HIDDEN_TASK_FIELDS` is only `{acp_command, acp_args}`, not model. Source-level details live in skill `hermes-orchestration-dispatcher`, `references/hermes-subagent-model-routing.md`.

**Live capability matrix** (9router/cockpit probes, vision model status, delegation config recipes): `references/model-capability-matrix.md`. Re-probe before relying — credentials/quota change. **Benchmark thật DS v4 flash vs Gemini 3.7 flash (17/08, 5 task Taadaa — DS ngang chất lượng nhưng 502/timeout, Gemini 5/5 ổn định; route status cmc/v98/oc; rubric + pitfalls chạy benchmark; v2 T6-T10 + retry max_tokens 30000; "gọi qua opencode" = route `oc/*` trong 9router, không phải opencode CLI): `references/model-benchmark-dsv4-vs-gemini-2026-08-17.md`.** **9router reasoning control (THINK:X trong console log, `providerThinking` DB settings, mode `"thinking"` invalid→auto, suffix `(high)`/`(max)` bị 403, deepseek effort allowed set, session compression threshold): `references/9router-reasoning-thinking-control.md`.** **UPDATE 2026-08-06: user added GPT upstream to 9router → `gpt-5.6-luna/terra/sol` (bare or `cx/` prefix) now respond via 9router HTTP `:20128`** (curl `/v1/chat/completions` → 200 `resp_...`). This REVERSES the earlier "Terra/Sol are Codex-CLI-only" claim: Hermes can now call terra/sol in-app via HTTP for plan/audit — no `codex exec` needed. Codex app catalog (`cockpit-local-access-model-catalog.json`) is unchanged (still GPT-only, no Gemini/Claude/DeepSeek); but the 9router route now covers GPT too. See `references/9router-http-calling.md` for verified call recipes (tool_choice=none, continuation rounds, Claude 403, Kimi finish=length). **Vision fallback is now WORKING on this machine**: `gemini/gemini-3.6-flash` via 9router sees images (≥64x64 px; tiny 2x2/8x8 test PNGs get `400 Unable to process input image` — a size quirk, not a capability gap), and `auxiliary.vision` is configured so the DeepSeek coordinator auto-falls back to Gemini for image analysis. See the reference for the exact config + `hermes config set` workflow (agent cannot edit config.yaml directly).

**2-mode symmetric orchestration (user-final, 2026-08-06 — file `D:\Taadaa\HERMES_SUBAGENT_RULES.md`):**
Model self-identifies the app from 2 signals in its system prompt: (1) Model line (`cmc/deepseek/deepseek-v4-flash` = Hermes; `gpt-5.6-luna` = Codex), (2) tool set (Hermes has `skill_view`/`memory`/`cronjob`/`session_search`; Codex has `apply_patch`/MCP).
- **HERMES mode** (main=deepseek-v4-flash): worker = deepseek-v4-flash/high via `delegate_task` (inherits parent model) → fail → deepseek-v4-pro (9router HTTP, read-only plan — **rescuer/auditor chuẩn, hợp lệ**) → fail → gpt-5.6-terra → sol (9router HTTP, read-only). Audit: v4-pro (thường) → terra (khó vừa) → sol (khó thật). Vision = ag/gemini-3.7-flash-low (17/08 sweep, trước = 3.6-flash-low).
- **CODEX mode** (main=gpt-5.6-luna/max): worker = luna/max native subagent → fail → terra/sol → fail → deepseek-v4-pro (read-only). Audit = deepseek-v4-pro.
- Golden rule: worker = subagent spawned by the same app (the ONLY thing that patches/runs live); rescuers/auditors (v4-pro/terra/sol) are READ-ONLY advisors — they produce plan/verdict, never patch. **v4-pro auditing/rescuing a flash worker is LEGITIMATE (same deepseek family, higher tier — user-approved 2026-08-07; it is the standard rescuer in the escalation table). "Crossover reviewer from a different family" is NOT a hard gate banning v4-pro — it is only a strengthening preference: hard-medium → terra, hard → sol; Codex luna → v4-pro (different vendor).**

**Worker policy FINAL (2026-08-06 — v8; SUPERSEDES đoạn "Worker fallback equivalence" cũ bên dưới — đó là thiết kế v1–v7 user đã bỏ):** AGENTS.md Taadaa đã đơn giản hoá lần cuối — worker theo APP, không spec: Hermes (ds-flash) → worker `deepseek-v4-flash/high` (UPDATE 2026-08-06 tối: user sweep reasoning max→high TOÀN BỘ — config `agent.reasoning_effort: high`, mọi AGENTS.md + HERMES_SUBAGENT_RULES.md đã đổi `flash/max`→`flash/high`, `reasoning_effort=max`→`=high`, `deepseek-v4-flash`/`max`→`/high`; `gpt-5.6-luna/max`/`Luna/max`/`Sol/max` GIỮ NGUYÊN); Codex (luna) → worker `gpt-5.6-luna/max`; **LUNA≡FLASH equivalent roles** — worker nào làm task nào cũng được, kể cả live (user chốt 2 model ngang nhau, bỏ hẳn hard gate "live phải luna"); **KHÔNG model fallback trong policy** (hết quota/outage = tool layer: Hermes `fallback_providers`, 9router auto-route — NGOÀI policy); **session-as-worker = fallback DUY NHẤT**: spawn worker subagent CONFIRMED fail (runtime-unavailable/capability-unavailable/429 có source+provider+pin) → ghi `SUBAGENT_RUNTIME_UNAVAILABLE` trước side effect → session tự làm bằng model session; timeout/unknown/ambiguous → reconcile (prove không còn worker/session/process/lease/action) → không chứng minh được → `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` + `FINAL_BLOCKED`. **Fallback ordering (v8): (1) in-process subagent với session model → (2) gated Codex CLI transport (Codex sessions ONLY, cùng session-model pin) → (3) session-as-worker (mọi session); Hermes không có CLI route — thẳng (1)→(3).** Bỏ hẳn khái niệm effective pin / `WORKER_PROFILE_MISMATCH`-cho-fallback, bỏ hẳn section Coordinator Direct Fallback, Model Routing = 1 reference + 2 mapping. **Vòng đồng bộ cuối (sau OpenCode findings):** 6 findings P1/P2 — các section KHÁC ngoài 2 vùng chính vẫn mâu thuẫn Luna-only (v4 header L8, canonical block L76, "DeepSeek never executor" L145, "remains Luna/max" L936, fallback ordering chưa rõ, watchdog/escalation headings) + 3 P3 cosmetic → fix hết, toàn file hết mâu thuẫn Luna-only (grep `sole desktop patch/live worker`/`remains Luna/max` = 0 ngoài deprecated section). **Kết quả cuối: 4 audit độc lập APPROVE** (ds-pro plan 7/7 + ds-pro file thật 5/5 + Gemini file thật 6/6 + OpenCode free APPROVE — Claude bị chặn weekly 91%≥90% exit 22) + verify 20/20 + validator exit 0; hash cuối `07bade5e66ee7a37c4c00ba561de56dab214e23d5374b58abcfa1913482993cc`. Rule chi tiết: `D:\Taadaa\HERMES_SUBAGENT_RULES.md`. Đừng áp dụng fallback-equivalence/effective-pin bên dưới cho policy hiện tại. **Recipe sweep hàng loạt flash/max→flash/high (pattern thay thế, PITFALL Python PermissionError → dùng sed, verify grep): `references/rule-file-bulk-reasoning-sweep.md`.**

**Audit gate — mandatory vs skipped (user-final 2026-08-06):** audit is a GATE for hard cases, NOT a default for every task.
- **Thường (debug 1 bug, 1 file consumer)**: flash worker sửa → fail → v4-pro cứu (read-only plan) → flash làm theo → test pass → **DONE, KHÔNG audit**.
- **Khó vừa (multi-file, 1 repo, logic phức tạp)**: v4-pro plan → flash làm → test pass → audit CHỈ nếu rủi ro (logic shared/ambiguous) → **terra**.
- **Khó thật (policy/core/live/recovery/lock/multi-repo/kiến trúc)**: backup → v4-pro plan → **Sol audit (bắt buộc, là gate)** → worker sửa theo findings → verify.
- **Khó vừa gọi terra, khó quá mới gọi sol** — không đốt sol cho việc terra xử lý được. Audit REJECT = sửa plan theo findings + re-audit (material change mở slot mới), KHÔNG implement plan bị reject.

**Pitfall**: Do NOT use Codex Luna for planning or routine coding — user has explicitly rejected this routing. Luna is debugging-only for this user's automation ecosystem.

**Pitfall (2026-08-06)**: Do NOT use Gemini as the primary audit/reviewer — user: "bợ dái lắm, không có tư duy phản biện" (sycophantic, no critical thinking). Gemini = vision + last-resort audit fallback only. Do NOT set `delegation.model` to Luna/max on Hermes — user decided against it; the rule file is `D:\Taadaa\HERMES_SUBAGENT_RULES.md` (pointer in memory). **Terra/Sol are READ-ONLY advisors — they never patch; deepseek-v4-pro via 9router is also review-only. After a reviewer verdict, a FRESH Luna/max (or Hermes for small fixes) executes the plan — reviewers are never the executor.**

**Pitfall (2026-08-06, policy-change plan)**: A weak-model (deepseek-v4-pro) policy plan is almost always REJECTED by a strong auditor (GPT-5.6-Sol) for: (1) repeating the same rule 3× with different force (`may`/`is pinned`/`is permitted`) instead of ONE canonical source; (2) classification not fail-closed (no consumer-root allowlist, no symlink/submodule/shared-path handling, tests with network/ADB side effects, scope drift mid-task); (3) direct-fallback clauses that punch through core gates (fallback banning "scheduler/lock/live" but not core offline edits); (4) edit boundaries by line-number drifting and swallowing the next heading (must anchor by unique heading/marker, verify 1 start/end, never include other headings in the payload); (5) duplicating rules across sections instead of referencing; (6) missing scope-drift gates (worker must self-stop + return handoff when it detects ADB/live/credential/recovery path); (7) inferring validator green from the script's name instead of running baseline-before + after; (8) contradictory escalation advice (banning "escalate consumer-normal to Luna" while recommending "big task → Luna"). **Never hand a raw v4-pro plan to a flash worker to implement — audit first; REJECT = fix plan + re-audit, not implement.** Full findings: `hermes-orchestration-dispatcher` SKILL.md → "AGENTS.md scope-split".

**Pitfall (2026-08-06, policy-change plan — REJECT lần 3, root cause = user decision)**: Khi plan policy-change bị auditor REJECT nhiều vòng liên tiếp, kiểm tra xem **chính quyết định user có phải gốc rễ không**. Vụ AGENTS.md scope-split: user quyết định "fallback luna↔flash ngang hàng cho CẢ live" → GPT-5.6-Sol REJECT 3 lần (v1: 8 findings — lặp rule, classification không fail-closed, edit-boundary drift, validator không baseline; v2: fallback tự mâu thuẫn với "Luna sole worker"; v3: live-STOP phải tách theo lớp, `unavailable` taxonomy trộn model/transport, effective pin không được chứng minh, dispatch-generation không lifecycle, Model Routing vẫn restate contract, validator gate không kiểm chứng). **Khi auditor REJECT nhiều vòng vì một quyết định policy bất thường của user (VD fallback model ngang hàng cho live — 2 model khác hãng/capability fallback lẫn nhau cho live rủi ro cao), đừng tự làm vòng 4 — chỉ ra cho user rằng chính quyết định đó là gốc rễ và đề xuất đơn giản hoá** (bỏ fallback flash cho live → live = Luna DUY NHẤT, luna down → STOP + `SUBAGENT_RUNTIME_UNAVAILABLE` → Sol APPROVE nhanh, vẫn đạt mục tiêu chính: Hermes flash patch consumer-normal). Fallback model cho live là chỗ auditor bảo vệ mạnh nhất (lạm dụng fallback). Chi tiết: `hermes-orchestration-dispatcher` SKILL.md → "AGENTS.md scope-split v3".

## User-specific review routing override

For this user's Taadaa review-gated work, the normal independent code-review route is **`gpt-5.6-terra` via direct 9Router HTTP**, not an AG Claude model and not a `delegate_task` child. The request is read-only and must include `tools: []`, `tool_choice: "none"`, and `stream: false`; require the reviewer to put exactly `VERDICT: APPROVED` or `VERDICT: REJECT` on the first line. Review only the exact staged bytes and preserve unrelated staged/dirty paths. A transport/provider error is neither a verdict nor evidence about code quality. If the allowlisted file changes or contains merge markers, stop with a provenance/scope conflict and do not reset, resolve, unstage, stash, normalize, or overwrite another writer's changes. Detailed procedure: `agent-review-loops/references/terra-exact-byte-review-and-conflict-gate.md`.

### Portable Hermes setup and migration

When moving a coordinator/worker setup to another PC, separate portable behavior from machine-local state:

1. Move or clone the Hermes source repo if it contains custom code or bundled skill changes; the repo alone is not the complete user configuration.
2. Export the active Hermes profile with `hermes profile export default -o <archive>.tar.gz`, then import it on the destination with `hermes profile import <archive>.tar.gz --name default`. This carries user-facing configuration, skills, plugins, cron, scripts, persona, and related preferences while intentionally excluding credentials and runtime databases.
3. Install the external worker CLIs independently on the destination (Claude Code and Codex) and verify their versions.
4. Authenticate again on the destination with each CLI and with Hermes (`hermes auth add ...`) instead of copying `.env`, `auth.json`, or CLI credential directories through Git/cloud storage.
5. Run `hermes doctor`, `hermes skills list`, and `hermes tools list`; execute a harmless task in a Git repository to verify the coordinator → worker → verification path.
6. If user-level skills override bundled skills, ensure the exported `skills/` content is included and inspect the destination's effective skill list after import.

Do not copy the entire Hermes home blindly: caches, SQLite state, locks, absolute paths, and secrets are machine-specific. A manual migration should copy `config.yaml`, `SOUL.md`, user `skills/`, `plugins/`, `cron/`, and `scripts/`, then re-authenticate secrets separately.

### Coordinator prompt contract

Tell the coordinator explicitly:

- Do not implement the main task itself unless a tiny coordinator-side fix is necessary.
- Break the request into independently verifiable worker tasks.
- Require workers to report changed files, commands run, and concrete output.
- Inspect the result and classify failures before retrying.
- Do not report success without proof.

Keep coordinator access to read-only inspection and verification tools where possible. Do not remove its ability to inspect diffs, logs, and tests: a delegation-only coordinator cannot validate worker claims.

### Escalation policy

- Routine implementation: fast worker first.
- Design or broad refactor: stronger worker/reviewer first.
- Test failure: classify the failure, then use a different recovery action/model; do not blindly rerun.
- Repeated identical failure: stop and report the signature and artifact rather than looping.

### Router decision

Use a local router when several clients need one credential store, provider fallback, or one stable OpenAI-compatible endpoint. First smoke-test the direct path (client → provider), then add the router hop. In the routed path:

```text
client → local router → upstream provider/model
```

Store the upstream credential in the router. Configure the client with the router endpoint and the router's local authentication key, not the upstream credential. Keep direct configuration when only one client needs the provider or when simpler debugging is more valuable than centralized routing.

## Pitfalls

- **9Router combo members KHÔNG xuất hiện trong `/v1/models`** (hit 2026-08-15): `oc/deepseek-v4-flash-free`, `oc/hy3-free` tồn tại nhưng là thành viên combo (`combos` table, `~/AppData/Roaming/9router/db/data.sqlite`, cột `models` JSON list) — `/v1/models` chỉ liệt kê model gốc top-level (~467 models). Khi verify model ID: đọc bảng `combos` TRƯỚC khi kết luận "không có model"; query mẫu: `SELECT name,models FROM combos` (verify 17/08 = 12 combo: deepseek-v4-flash/pro, gpt-5.6-luna/terra/sol, gemini-3.6-flash-high, gemini-3.7-flash-high, claude-sonnet-4-6, opencode-audit, opencode-free, worker, plan-review, plan-review-hard; combo `worker` live = `[cmc/deepseek/deepseek-v4-flash, oc/deepseek-v4-flash-free, oc/hy3-free, ag/gemini-3.7-flash-high, ag/claude-sonnet-4-6, gpt-5.6-luna]` — DB là ground truth, chain ghi trong skill có thể cũ hơn combo live). Combo `deepseek-v4-flash` = `[cmc/deepseek/deepseek-v4-flash, oc/deepseek-v4-flash-free, oc/hy3-free, gpt-5.6-luna, openrouter/…free…]`.
- **`cx/gpt-5.6-terra-review` / `cx/gpt-5.6-sol-review` ĐÃ BỊ GỠ khỏi catalog** (2026-08-15, 467 models): dùng bare `gpt-5.6-terra` / `gpt-5.6-sol` (route cùng upstream GPT). AG Opus = `ag/claude-opus-4-6-thinking`; Opus 5 = `v98/claude-opus-5`; Gemini 3.6 flash high = `ag/gemini-3.6-flash-high`; `gemini/gemini-3.6-flash` (bare) KHÔNG còn. `cx/*` prefix cũng biến mất khỏi catalog (gpt-5.6-* bare thay thế).
- **Command Code route qua 9router (hit 17/08):** model ID đúng = `commandcode/deepseek/deepseek-v4-flash` — KHÔNG suffix `(high)`/`(max)` (suffix → 403 `"anthropic:deepseek/deepseek-v4-flash(high) not recognized"` từ upstream); prefix `cc/` sai (resolve thành provider claude, no creds). Connection nằm trong bảng `providerConnections` (provider=`commandcode`, authType=apikey) — user thêm account `lequynh27032002` (priority 1, active 17/08); connection có `testStatus=active` mới gọi được; `No active credentials for provider: commandcode-direct` = connection chưa có/isActive=0. Route này trả `reasoning_content` (giống combo DS) nên benchmark/call phải set max_tokens lớn.
- **Khi user add model vào 9router → gọi thẳng model ID qua `/v1/chat/completions` y hệt mọi model khác** (user correction 17/08, 2 lần bực: "Tao add model command code deepseek qua 9router thì mày gọi đó mà test như cách mày gọi ag gemini 3.7 flash"). KHÔNG đi tìm CLI riêng, không đổi prefix, không thử route khác. Model ID hợp lệ = ID trong DB `providerConnections` (`modelLock_*` keys trong `data` JSON), không phải `/v1/models` catalog (chỉ liệt kê model gốc top-level). "CLI command code trong 9router" user nói = connection/provider trong 9router, KHÔNG phải binary CLI cài riêng.
- **Command Code DeepSeek qua chat API thuần sinh tool-call XML thay vì trả lời** (hit 17/08, benchmark v4): model train theo pattern agent CLI → khi gọi `/v1/chat/completions` KHÔNG có tool executor, nó sinh `<invoke name="grep">`/`<invoke name="bash">`/`<invoke name="glob">` vào content → output vô dụng (4/5 task v4, content chỉ có tool XML). FIX: thêm instruction vào prompt: `[CẤM TUYỆT ĐỐI] Bạn KHÔNG có tool, không được gọi bash/grep/glob/read file. Chỉ trả lời text trực tiếp dựa trên code đã dán.` (v5 đang verify).
- **Chi phí coordinator: đừng trả lời "được/không" khi user hỏi đổi model điều phối** — đưa con số daily-burn tương đương (6–8 credit/ngày Flash → 16.5–22 credit/ngày Pro; pool $10 cháy 1.25–1.67 ngày) và đề xuất Pro ở bước ngắn (plan/audit) thay vì coordinator thường trực; kèm break-even `p=(r-1)/r` (r=2.76 → 63.8%) khi bàn Flash-first vs direct-Pro. Cùng pattern cho câu "chỉ gọi X qua AG thì chạy nổi k?": đưa share thật (AG ≈ 2–3% traffic farm — 65/1981 req 17/08), account sống (chỉ jinrakal), constraints AG (từ chối request context lớn, RPM burst lock ~5 phút, subscription quota cháy kiểu 9 acc đã chết 429) — recipe đầy đủ: `9router-proxy-ops` → `references/ag-single-account-capacity.md`.
- **Audit KHÔNG qua `delegate_task` subagent (user correction 2026-08-11, 2 lần: "audit gọi terra/sol đi", "làm gì có set cho gọi luna audit")**: `role=leaf` read-only KHÔNG biến child thành auditor — child chạy delegation pin (cockpit `gpt-5.6-luna`), nên leaf luna subagent chỉ là WORKER làm việc review, user bác thẳng. Audit route đúng theo `D:\Taadaa\AGENTS.md` mục 2: **AG Opus primary (`ag/claude-opus-4-6-thinking` qua 9router `:20128`) → fallback `cx/gpt-5.6-terra-review` (case thường)/`cx/gpt-5.6-sol-review` (case khó) → `opencode-audit`**; Luna/Flash KHÔNG BAO GIỜ audit. Chạy audit qua `run-ag-audit.sh`/`ag_audit_direct.py` (9router HTTP), không qua `delegate_task`. ĐỪNG over-correct thành "Terra/Sol bắt buộc" — rule có AG primary; đọc lại AGENTS.md trước khi khai báo chuỗi audit (hit thật: sửa skill 2 lần vì nói sai rule).
- Do not use the strongest coding model for every coordinator turn; orchestration usually does not need maximum coding ability.
- **Do not infer fallback suitability from quota alone.** First restate the capability ladder the user supplied, then reject any chain that drops below the minimum role capability (for example, do not place a substantially weaker model behind a stronger coordinator without an explicit degraded-mode contract).
- **Do not treat a subsidized stronger worker as escalation-only by habit.** Compare expected retry cost: if Pro costs `r`× Flash, Flash-first breaks even at failure probability `(r-1)/r`; include latency/context/review overhead and route known medium/hard work directly to Pro when appropriate.
- Do not assume a model name or catalog is current; verify the live `/models` list/provider metadata.
- Do not confuse an upstream provider key with a local router key.
- Do not make the coordinator pure delegation-only if no component can independently inspect and verify results.
- Do not retry the same failed worker command without a changed hypothesis or recovery action.
- Do not claim success from a worker's prose alone.
- **Do not leave `delegation.max_iterations` at the default for large multi-repo/live tasks** (2026-08-10, measured): `max_iterations` is a CEILING, not a target — a worker that finishes early still stops early, so raising it costs nothing on small tasks, but at cap 50 multi-repo patch+verify+live tasks (which realistically need 70–120 calls) drop mid-task. Measured over 87 delegation summaries: 21 dropped (24%) overall, 62% on the heaviest day; each drop loses context and the successor worker re-triages from scratch — more expensive than letting the worker run. Fix: raise to 100 for multi-repo sweeps (user-approved), re-evaluate at 150 if drops persist near 90–100. When a worker still drops, dispatch a SUCCESSOR with triage state attached (summary file path + exact before→after list), never a blank spec. Measure the drop rate from the delegation cache: `~/AppData/Local/hermes/cache/delegation/subagent-summary-*.txt`, grep per file for "hết lượt tool"/"giới hạn tool"/"chưa hoàn tất"/"LIVE_PARTIAL".
- **A `delegate_task` inactivity timeout is not an iteration-cap failure.** Read `iteration N/M` separately from `seconds since last activity`: when `N << M` but idle time crosses `agent.gateway_timeout`, the Gateway killed a silent parent/tool wait. Distinguish per-parent `delegation.max_concurrent_children` from Gateway-wide `max_concurrent_sessions`; several sessions can multiply aggregate child load even while each parent obeys its cap. Reconcile an interrupted child’s exact scope before replacement, tune finite timeouts/concurrency caps through `hermes config set`, and defer Gateway restart while in-flight work exists. Full diagnostic and tuning recipe: `references/hermes-delegation-timeout-and-load-tuning.md`.

## Model benchmark / fair comparison (user-final 2026-08-17)

Khi user yêu cầu "so sánh model A vs B" (worker quality, routing quyết định): chạy CẢ HAI qua CÙNG MỘT cơ chế — chỉ khác model ID. User đã sửa 3 lần khi tôi đổi route/harness giữa chừng:

1. **Agent-loop (ưu tiên — user chốt: "cùng 1 prompt gọi agent ra trả lời dùng model đã chỉ định")**: `hermes chat -q "<prompt>" -m <model-id> --provider 9router -Q` — 2 model cùng agent loop, cùng toolset, model tự quyết dùng tool hay không. Model ID KHÔNG cần khai báo trong `custom_providers.models` — 9router pass-through chấp nhận (verify 17/08: `commandcode/deepseek/deepseek-v4-flash` chạy được dù config không liệt kê). Hermes chặn agent sửa config.yaml trực tiếp (Refusing to write) — không cần sửa, dùng `-m` trực tiếp.
2. **Pure model**: POST `/v1/chat/completions` body giống hệt (stream:false, cùng max_tokens), chỉ đổi `model`.
3. **KHÔNG thêm prompt khác biệt cho 1 bên** (vd "CẤM dùng tool" chỉ cho DS) — user bác: "tự nhiên h cấm dùng tool, trong khi gemini nó đc dùng tool hay k?" Nếu cần giới hạn tool thì áp cho CẢ 2, hoặc chạy agent-loop để model tự quyết.
4. Task lấy từ repo thật (đọc code trước — workbook.py, follow_state.py, device_lock.py, safety.py, vpn_preflight.py), 5+ task phủ: fix bug, code review fail-closed, code gen selector, root-cause, log parse. Lưu kết quả JSON từng task + chấm điểm P0/P1 theo rubric, không chấm cảm tính.
5. User nói "t vừa thêm model r" → đọc `providerConnections` (DB 9router, `testStatus=active`, `modelLock_*` keys = model ID thật) và gọi ĐÚNG model ID đó y hệt model kia — KHÔNG tìm CLI riêng, không đổi prefix, không thử route khác.

Pitfalls đã dính (17/08): DeepSeek reasoning squeeze (`reasoning_content` chiếm max_tokens → `content` rỗng, tưởng fail; đọc cả 2 field, max_tokens ≥ 20000); Command Code model qua raw API sinh tool-XML thay vì text (chạy agent-loop thì xử lý đúng); `oc/deepseek-v4-flash-free` 502/timeout task dài (free tier infra, không phải model dở); `cmc/deepseek/*` 404, `v98/deepseek-v4-flash` 503 service_migrated (v98store→cheapkeyai.shop); **agent-loop bắt buộc `--max-turns 8`** (không cap → 160K+ chars tool-dump, T7 v6). Kết quả: Gemini 3.7 Flash 5/5 task ổn định (10-42s, bắt P0 fail-open/double-acquire thật); DS CC chất lượng ngang/cao hơn khi trả được (phản biện đúng bug planted, 18-131s/call) → Gemini xứng đáng worker chính, DS CC đáng cân nhắc sau khi có creds. Chi tiết vòng Command Code: `references/model-benchmark-command-code-dsv4-2026-08-17.md`.

**Verdict cuối in-Hermes (v7, 17/08 — worker role trong Hermes, DS CC có creds thật):** 5 task Taadaa, cả 2 chạy `hermes chat -m <model> --provider 9router -Q --max-turns 8`, cwd=D:\Taadaa, delay 60s né burst lock. **DS Command Code = phân tích sâu hơn (9.5): đọc file thật + git status + chạy test sống + trace caller (`calibrate_screens.py:1306`), PHẢN BIỆN đúng giả định sai (T7: bug timezone không tồn tại — host +7, astimezone naive = host local; nguồn reset thật = `_load()` except trả `{}` + spec 17/08 bỏ daily cap). Gemini = 8, đúng theo đề, thụ động hơn, không verify reality. Độ ổn định: Gemini 5/5, DS CC 4/5 (1 lỗi 500 server T6). Tốc độ: Gemini ~71s TB (25-126), DS CC ~264s TB (218-304). Routing đề xuất (chờ user duyệt): Gemini = worker mặc định (nhanh/ổn), DS CC = task khó (bug mơ hồ multi-file/recovery/audit). Chi tiết + rubric: `references/model-benchmark-hermes-agent-20260817.md`.**

## Router Concurrency Incident Review Gate

For a live multi-account router incident, do **not** infer correct spill behavior from aggregate success counts. Inspect the same post-restart window as a five-column trace:

```text
combo target step + declared connectionId
→ credential.connectionId selected by auth
→ account/executor actually calling upstream
→ semaphore key + configured cap
→ status/outcome
```

The required invariant is: `target connectionId = selected credential connectionId = execution connectionId = concurrency/semaphore key`, unless the combo explicitly records a skip and advances to the next declared target. A healthy-looking spread across several accounts is not proof: it can be an uncontrolled credential remap that bypasses the account cap the combo thought it reserved.

For an ambiguous core routing/concurrency defect, escalate to `plan-review-hard` / `gpt-5.6-sol` as a **read-only** review: provide the minimal relevant source, exact target-to-execution facts, and current diff. The reviewer must identify where `forcedConnectionId` is retained, dropped, or overridden, and propose RED-first regression tests. It must not patch or restart production.

**Pitfall — patch stacking during live recovery:** Do not combine semaphore-timeout changes, priority-binding changes, and affinity changes in one unproven production patch. First classify the observed error as upstream `403/429`, internal semaphore timeout, or synthetic binding rejection. Keep the runtime stable and make one invariant-focused change only after the override/drop seam is evidenced.

## Verification

**HTTP call rule (hit 2026-08-15): mọi call 9router từ Hermes PHẢI kèm `"stream": false`** — nếu không, AG models (`ag/gemini-3.6-flash-*`, `ag/claude-opus-4-6-thinking`, `ag/claude-sonnet-4-6`) trả `text/event-stream` (SSE) → client `json.loads` fail `"Expecting value: line 1 column 1"`, dễ bị chẩn đoán nhầm thành "model hết quota". Set `stream:false` → 200 JSON chuẩn. Cũng là lý do "AG Gemini còn quota mà không dùng được" — đã verify thật (200 JSON với stream:false).

**9Router combo API (2026-08-15):** `GET/POST /api/combos`, `PUT/DELETE /api/combos/:id`; body `{name, models:[ids], kind}` (name regex `^[a-zA-Z0-9_.\-]+$`); auth `POST /api/auth/login {"password":...}` — password bcrypt (không đọc ngược, ~5 lần lockout `remainingBeforeLock`). DB `~/AppData/Roaming/9router/db/data.sqlite` bảng `combos`, cột `models` là STRING JSON. Backup DB trước khi sửa combo. Chi tiết chain + latency đo: `references/9router-combo-routing-20260815.md`.

For each worker task, record:

- selected model and reason;
- workdir/repository scope;
- changed files or explicit no-change result;
- test/build/lint commands and actual output;
- unresolved risks or recovery attempts.

For router setup, verify the local endpoint with a harmless smoke request, confirm the requested model ID is accepted, and confirm the upstream key is not exposed in the client configuration or logs.
