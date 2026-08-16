---
name: hermes-orchestration-dispatcher
description: "Điều phối: task đơn giản Hermes tự sửa → Claude/OpenCode audit review → lặp fail mới Codex implement."
version: 1.5.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [orchestration, dispatch, codex, claude, opencode, workflow, audit, review]
---

# Hermes Orchestration Dispatcher

## Quy tắc cứng (theo D:\Taadaa\AGENTS.md)

**KHI SKILL NÀY ĐƯỢC LOAD:** Hermes phân loại task rồi điều phối theo ladder dưới đây. Hermes KHÔNG bao giờ tự ý implement thẳng khi chưa qua audit review, trừ task đơn giản trong phạm vi dưới.

**Routing-policy analysis** (user hỏi "đọc config/policy/catalog, đề xuất workflow model theo quota", thường kèm `CHỈ PHÂN TÍCH`): làm theo `references/routing-policy-analysis-method.md` — quy trình 6 bước (1 planner OpenCode mạnh không-DeepSeek-Flash → 1 AG Claude/high critique + health-test → fallback GPT/high → OpenCode khác), đúng 5 mục output, facts probe 9Router đã verify (opencode-free==deepseek-v4-flash-free, auditor hallucinate catalog, probe 429 re-test).

### COORDINATOR-WRITE GUARD (user duyệt 2026-08-07 — BẮT BUỘC)

- **Session chính = COORDINATOR, chỉ điều phối**: KHÔNG tự write/edit/build/deploy. Write tools (write_file/patch/terminal-write) CHỈ dùng READ/VERIFY (đọc, diff, test đọc) — không sửa.
- **MỌI thay đổi → dispatch đúng 1 fresh worker subagent** (role=leaf, inherit session model) scope độc quyền. Worker xong → session verify độc lập (diff+test+CRLF), KHÔNG tin self-report.
- **Plan/audit case khó TRƯỚC khi worker sửa**: **PLAN = deepseek-v4-flash TẠI SESSION ĐIỀU PHỐI** (read-only, plan không phải write; không spawn subagent riêng, KHÔNG dùng v4-pro cho plan — bỏ 2026-08-07) → **PLAN-AUDIT bắt buộc = gpt-5.6-luna/max** → **CONSENSUS 2 MODEL** (flash plan + luna/max APPROVE) trước khi worker flash implement (read-only, 9router HTTP/CLI); dễ (1 bug/1 file) → flash plan nhanh + luna/max audit nhanh → worker flash; khó vừa (nhiều file 1 repo) → flash plan → luna/max audit → worker làm → audit nếu rủi ro (terra); khó thật (policy/core/live/multi-repo) → flash plan → luna/max audit → **bắt buộc Sol audit gate** → worker sửa theo plan → verify. Không đồng thuận (luna REJECT/MINOR_FIXES) → sửa plan vòng 2 → luna/max audit lại → lặp tới APPROVE. Sau sửa code case khó → dispatch subagent audit RIÊNG (role=leaf, context=diff+spec, verdict APPROVED/MINOR_FIXES/REJECT) — worker KHÔNG tự duyệt. Model mạnh (Sol/Terra/luna/OpenCode/Claude) qua CLI wrapper hoặc 9router HTTP (Hermes subagent không chọn model per-task).
  - **PITFALL "user không hiểu mình đang làm gì" (2026-08-08, core handoff bị luna REJECT ×3)**: khi plan bị auditor REJECT nhiều vòng với findings kỹ thuật chồng chất (atomic 2-alias, fencing TOCTOU, back-compat wire status...), user dễ mất mạch: *"tóm lại t vẫn chưa hiểu cái m định làm là cái gì"*. Đừng tiếp tục sửa plan vòng 4 — **dừng, giải thích lại VẤN ĐỀ GỐC bằng ngôn ngữ thường** (không thuật ngữ: "2 script chạy cùng máy, 1 cái reboot giữa lúc 1 cái đang đăng → cần chữ ký tạm dừng"), rồi hỏi lại mục tiêu thật. Thường lộ ra **feature không cần thiết**: kiểm tra xem vấn đề thực tế đã có handler chưa (popup draft sau reboot ĐÃ có `_dismiss_resume_draft_popup`/`_delete_all_profile_drafts` → bỏ hẳn core change, user: *"đúng bỏ hẳn"*). Quy tắc: **trước khi thiết kế cơ chế mới, verify vấn đề thực tế đã có flow xử lý chưa**; 3 vòng REJECT cùng gốc = đơn giản hoá HOẶC bỏ, không bao giờ vòng 4.
  - **PITFALL audit vòng tròn “chưa có exact artifact”**: auditor có thể REJECT một plan live vì script/harness và test evidence chưa tồn tại, trong khi policy lại cấm chạy live trước exact-script approval. Không cố sửa abstract plan vòng 4. Tách scope thành hai authorization độc lập: **Phase 1 offline-only** (worker chỉ tạo harness/fake tests trong thư mục artifact, live APIs hard-disabled; audit plan chỉ cần duyệt quyền tạo artifact này) → parent verify bytes/hash/tests/no-side-effect → **audit exact artifact** → mới cấp token cho **Phase 2 live**. Plan approval không bao phủ code chưa tồn tại; exact-artifact audit không được đòi bằng chứng live trước khi authorize live. Nếu finding thực tế là harness gọi helper sai precondition, sửa harness—not production—and không tạo commit giả.
- **Session-as-worker = fallback DUY NHẤT**: session tự làm CHỈ KHI spawn worker CONFIRMED fail (runtime-unavailable/capability-unavailable/dispatch-429 có source+provider+pin) → ghi SUBAGENT_RUNTIME_UNAVAILABLE trước side effect → session làm worker. Timeout/unknown → reconcile → LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH → FINAL_BLOCKED. **KHÔNG có ngoại lệ "mechanical edit"/"task đơn giản"** — mọi write qua worker trước (bài học 2026-08-07: sweep 55 file trực tiếp = vi phạm, dù mechanical).
  - **PITFALL "delegation báo completed nhưng zero files" (2026-08-13, Phase 9B.1 — 3/3 delegate gpt-5.6-luna fail)**: banner `[ASYNC DELEGATION BATCH COMPLETE ... status=completed]` kết thúc bằng `API call failed after 8 retries: cannot convert float infinity to integer` = harness crash ở bước finalize → session terminal của worker (nơi chứa file worker ghi) bị mất toàn bộ. **KHÔNG tin status completed**: verify độc lập ngay `git status --short` + `test -f` từng path allowlist + handoff artifact tồn tại. 2-3 lần liên tiếp cùng pattern → dừng delegate, **session-as-worker làm trực tiếp** (terminal persistent, write đáng tin) — như 9B.1: tự implement 5 file + test + AG audit + commit thành công. Handoff JSON của worker phải **string-only** (bỏ mọi field float/duration — `float infinity` chính là thứ crash finalize) và dùng path Windows `C:/...` trong Python (MSYS `/c/...` resolve sai drive → file lạc chỗ).

### Phân biệt vận hành (run) vs phát triển (build/fix) — user chốt 2026-08-15

- **Lệnh vận hành** ("chạy script repo X máy Y", "run batch", "chạy feed") → **KHÔNG plan, KHÔNG Kanban, KHÔNG chain model đắt**: Flash (session/worker) chạy canonical script + params đúng, theo dõi log, báo kết quả. Không sửa file. Gọi Pro ở bước này = phí tiền (user: "t ra lệnh chạy script repo xxx máy xxx" → đi thẳng).
- **Lệnh phát triển** (build script mới / fix bug / sửa automation) → mới vào model chain plan/review (xem `agent-model-routing` — finalized chains 2026-08-15).
- **Reviewer KHÔNG dùng Flash** (user 2026-08-15: "Reviewer sao dùng flash dỏm quá k?"): review/audit dùng plan/review chain (`gpt-5.6-terra → ag/claude-opus-4-6-thinking → cmc/deepseek/deepseek-v4-pro`; khó: `gpt-5.6-sol → v98/claude-opus-5 → cmc/deepseek/deepseek-v4-pro`).
- **Ưu tiên HTTP model chain hơn profile/Kanban roles** cho plan/review (user 2026-08-15: "sao phải thêm profile nghe phức tạp v gọi sub agent ra làm k đc à" → sau đó "Http pro. ... pro chỉ là fallback thôi"): `delegate_task` không chọn model per-call nên không có "subagent Pro"; gọi 9Router HTTP trực tiếp với chain theo độ khó. Profile/Kanban roles chỉ khi cần durable board (task sống qua crash).

### Phân loại task

- **SIMPLE** (Hermes tự sửa được): task 1-2 file, mechanical edit, bug rõ ràng, có test hiện có, không đụng shared core (`automation-core`), không sensitive (account/OTP/lock/workbook policy), không multi-machine. → **Hermes tự sửa trực tiếp** *(⚠️ 2026-08-07: theo AGENTS.md v8 canonical, session = coordinator read-only — MỌI write kể cả SIMPLE/mechanical/bulk phải dispatch worker subagent. Mục này còn giữ nguyên tắc cũ "Hermes tự sửa" cho phân loại NHANH nhưng KHÔNG được phép tự write thẳng — xem `references/coordinator-write-enforcement.md`)*.
- **COMPLEX** (dispatch Codex implement): đụng `automation-core` hoặc shared recovery/lock/verifier/scheduler, cross-consumer, account/OTP/2FA safety, sensitive workbook policy, multi-machine/incident, architecture refactor. → **Codex implement** (Sol/high, ladder escalation).
- **BOUNDED_RESEARCH/AUDIT** (delegate review): read-only exploration, log/artifact analysis, test chạy, independent review. → **Claude/OpenCode audit**.

## Cross-consumer recovery migration gate

Khi một shared recovery/control-plane đã ship nhưng user nói "triển khai" tiếp, không đồng nhất core shipped với fleet auto-recovery. Tách bốn trạng thái: core shipped; adapter migrated; runtime-connected; live-proven. Trước consumer edit phải đọc audit/report đã duyệt, lập plan thật có matrix từng consumer, rồi audit plan bằng AG Opus (fallback ladder chỉ khi route failure cụ thể). Pilot một consumer có strict registry + runtime caller thật; nếu registry chỉ ở scheduler/preflight thì phải có discovery phase, không đoán insertion point. Mỗi consumer dùng một worker/worktree độc quyền, tuần tự, contract tests RED→GREEN cho no-hook/missing handler/HARD_STOP/NON_RETRYABLE/exception/budget/verifier/lock-retention/restart/redaction, rồi AG audit và commit riêng. Core remains app-neutral; adapter owns taxonomy and business flow; no second retry loop; no live/secret/workbook/ADB validation. Cuối cùng báo riêng N/9 adapter đã runtime-connected và consumer còn PENDING/NEEDS_PROOF. Chi tiết matrix/evidence ở `references/cross-consumer-recovery-migration.md`.

## Vòng lặp điều phối chuẩn

```
1. Phân loại task (SIMPLE / COMPLEX / AUDIT).
2. SIMPLE  → Hermes tự sửa code + test + chạy verify.
   COMPLEX → viết spec tasks/<date>-<slug>.md → dispatch Codex implement.
3. Dispatch AUDIT REVIEW (v5: AG `ag/claude-opus-4-6-thinking` primary; cx `gpt-5.6-luna`/`terra`/`sol` workhorse; Claude CLI `claude-opus-5` high hard-case; fallback OpenCode free → Command Code).
   Claude/OpenCode CHỈ review/audit — KHÔNG bao giờ implement.
4. Reviewer trả APPROVED / MINOR_FIXES / REJECT.
   - APPROVED → xong (verify cuối: test + diff).
   - MINOR_FIXES/REJECT → Hermes tự sửa theo findings (SIMPLE scope) HOẶC Codex sửa (COMPLEX scope).
5. Re-review (vòng 2+).
6. Vẫn fail CÓ DẤU HIỆU LẶP (cùng findings, cùng chỗ treo/fail, 2+ vòng không tiến triển)
   → Chuyển hẳn cho Codex implement: phiên MỚI, kèm what-was-tried/why-failed + materially different plan (theo AGENTS.md), không lặp y hệt prompt.
7. Codex xong → review lại → APPROVED → verify cuối.
```

## Nguyên tắc vai trò (refresh 2026-08-06 — xem cả mục "Escalation ladder đã chốt" bên dưới)

- **Hermes (deepseek-v4-flash)**: tự sửa task SIMPLE + triage + **debug vòng lặp nhanh** (user: debug để deepseek — nhanh; dựng script/bài mới → Codex). Viết spec; dispatch; verify cuối. KHÔNG implement task COMPLEX thẳng tay. **Reasoning = HIGH (từ 2026-08-06 tối — user sweep max→high TOÀN BỘ: config `agent.reasoning_effort: high` + mọi AGENTS.md/rule `flash/max`→`flash/high`; Luna/high, Sol/max giữ nguyên).**
- **Codex gpt-5.6-luna/high**: worker implement/live cho task COMPLEX + sửa findings khi Hermes lặp fail. Spawn subagent cùng hệ sinh thái GPT (luna/terra/sol) cho mượt trong app.
- **deepseek-v4-pro**: rescuer khi worker fail + auditor cho case khó vừa (READ-ONLY — đưa root-cause/plan cứu, KHÔNG patch; worker thực thi lại là deepseek-v4-flash hoặc Luna/high cho fix nhỏ). **KHÔNG dùng v4-pro làm planner thường nữa** (user đảo quyết định 2026-08-07: plan = flash tại session điều phối; v4-pro chỉ còn vai rescuer khi worker fail, plan/audit kèm luna/max).
- **gpt-5.6-sol**: plan tổng + case khó nhất.
- **Claude (v5)**: primary auditor/planner = AG `ag/claude-opus-4-6-thinking` (Antigravity qua 9Router, reasoning high); hard-case = CLI `claude-opus-5` high — quota-gated (preflight `claude-quota-preflight.ps1`, <85% 5h AND <90% weekly), invoked TRƯỚC `cx/gpt-5.6-sol`; CLI quota blocked → AG `ag/claude-opus-4-6-thinking` (high).
- **OpenCode**: reviewer fallback (free model), CHỈ ĐỌC. Không bao giờ implement.
- **Gemini 3.6 flash**: CHỈ VISION cho deepseek (auxiliary vision). **KHÔNG còn trong audit route từ v5 (2026-08-07)** — user bỏ hẳn: "bợ dái lắm, không có tư duy phản biện" (sycophant) + bị thay bởi AG claude/cx GPT. Xem mục `Audit Routing v5`.
- **Codex (cx route v5)**: workhorse audit `cx/gpt-5.6-luna` (dễ) / `cx/gpt-5.6-terra` (khó vừa) / `cx/gpt-5.6-sol` high (khó thật) qua 9Router codex transport + implementer task COMPLEX + sửa findings khi Hermes lặp fail. **Bỏ "fresh Codex reviewer độc lập"** (v5 — trùng transport cx route).

## Escalation ladder đã chốt (2026-08-06, user duyệt)

```
Hermes deepseek-v4-flash (task simple/vừa + debug nhanh)
  └─ fail (đã hiểu vì sao) → Codex gpt-5.6-luna/high (worker, làm khác đi)
      └─ vẫn fail → deepseek-v4-pro HOẶC gpt-5.6-terra (review READ-ONLY, đưa root-cause/plan mới)
          └─ fresh Luna/high làm theo plan mới
              └─ case khó nhất → gpt-5.6-sol (high→extra_high→ultra, session MỚI mỗi nấc)
```

- **Reviewer (terra/pro/sol) KHÔNG BAO GIỜ patch** — chỉ review + plan; executor là Luna/high (hoặc Hermes cho fix nhỏ).
- Cùng 1 evidence chỉ review 1 lần (1 audit slot) — không review 2 lần.
- **Audit route & execution**: giữ một model xuyên suốt cùng task (bắt đầu Sol → Sol đến verdict); reasoning HIGH, không max. Audit thường dùng history; blind audit dùng diff-only để kiểm chứng độc lập. Chỉ tiếp tục với P0/P1 concrete code path. **Xem `references/audit-loop-execution.md`** cho decision-before-side-effect, 50-call budgeting, handoff, communication, và exit quality gate.
- **Question ≠ execution (user-corrected 2026-08-09)**: câu hỏi kiểu “có gây loop không?”, “phân tích đi”, “có cách nào không?” chỉ được phân tích và nêu trade-off; TUYỆT ĐỐI không patch skill/AGENTS/config, restart gateway, dispatch worker hay đổi workflow trong cùng turn. Chỉ hành động sau chỉ thị rõ như “chốt phương án X”, “update rule”, “chạy tiếp”, “restart ngay”. Khi user nói “chốt phương án nào”, nêu recommendation trước; chỉ cập nhật khi họ xác nhận/ra lệnh thực thi.
- **50-call worker protocol (user-chốt 2026-08-09)**: hard cap 50 là guardrail. Scope cùng file/component chia theo phase **tuần tự**, không parallel: implementation/detection khoảng 25–30 calls, giữ 10–15 calls cho focused tests, full verification, docs và EOL/diff-check. Khác repo/file mới parallel. Handoff phải ghi code đã đổi, test pass/fail, EOL, temp artifacts và đúng một bước còn lại. Nếu 2 workers liên tiếp cùng component cạn quota trước verification, không tự spawn worker thứ ba scope mơ hồ; coordinator thu hẹp checklist/batch verification hoặc báo user.
- **PITFALL "delegation hết budget API calls chứ không phải tool calls" (2026-08-16, follow-integration worker 1+2)**: banner báo `status=completed, api_calls=100, 719s` / `api_calls=100, 1054s` — worker dừng vì **hết budget API calls (~100 lần LLM gọi)** chứ KHÔNG phải `max_iterations` (tool calls, config `delegation.max_iterations: 50`). 2 workers liên tiếp: worker 1 hết budget khi phân tích (0 file sửa), worker 2 hết khi mới xong RED (tests sửa, code chưa). Task lớn (5 file code + 6 test files + TDD) **không fit 1 worker**: phân tích + RED ngốn ~80-100 calls. FIX: (a) cho worker chỉ implement, parent tự chạy baseline/verify; (b) chia phase: worker A sửa code core, worker B sửa tests; (c) khi 2 workers liên tiếp hết budget ở phase đầu → **session-as-worker làm tiếp phase còn lại trực tiếp** (worker đã làm xong phân tích/RED = "nửa task đã tiêu budget", session tiếp GREEN theo plan APPROVED, KHÔNG cần audit lại plan). User nhầm `calltool cài lên 100` với budget API calls — 2 thứ khác nhau, giải thích khi user thắc mắc.
- Đổi model = phải **làm khác đi**, không lặp patch.
- Chi tiết đầy đủ: `D:\Taadaa\HERMES_SUBAGENT_RULES.md` (file rule Hermes riêng, ngoài git, đọc theo memory).

## Model Fallback Khi Claude Review Hết Quota

Khi `claude -p` trả quota/session limit, rate limit, billing error:
- **KHÔNG bỏ review gate, KHÔNG chờ reset.**
- Fallback chỉ thay **audit/review**, không thay Codex implementer.
- Thứ tự: `freemodel/claude-opus-4-8` → `opencode-go/grok-4.5` → `opencode-go/glm-5.2`, `--variant max`.
- **Escalation backup v5**: CLI quota blocked mà case vẫn khó → `ag/claude-opus-4-6-thinking` (reasoning high) qua 9Router.
- `opencode run --agent plan --auto --model <m> --variant max '<prompt>'` (read-only, quyền đọc external dir).
- Prompt phải có verdict `APPROVED | MINOR_FIXES | REJECT` dòng đầu.
- Smoke-test: `opencode run --model <m> 'Respond with exactly: OPENCODE_FALLBACK_READY'`.
- Shell vỡ quote → viết `.txt`, `PROMPT=$(cat file); opencode run ... "${PROMPT}"`.
- `APPROVED` từ fallback thay thế gate Claude cho run hiện tại.
- Nếu toàn bộ Claude/OpenCode reviewer hết quota hoặc unavailable, dùng **cx route** làm fallback cuối: `cx/gpt-5.6-sol` reasoning high qua 9Router codex transport (v5: "fresh Codex reviewer độc lập" ĐÃ BỎ — trùng transport cx route; khi cần CLI: `codex exec --ephemeral --sandbox read-only`); prompt verdict `APPROVED | MINOR_FIXES | REJECT`. Không reuse/resume session implementer và không để implementer tự spawn subagent để tự duyệt thay đổi của chính nó.
- Nếu Codex reviewer trả finding, Hermes sửa (SIMPLE scope) hoặc dispatch Codex implementer mới (COMPLEX scope), rồi review lại.

## Hermes App: Subagent Model Routing — `delegate_task` KHÔNG chọn model per-subagent

Kiểm chứng 2026-08-05 (source `hermes-agent/tools/delegate_tool.py`, xem `references/hermes-subagent-model-routing.md`). **Đã re-verify ở bản 0.20.0 (update 2026-08-05): `delegate_task` vẫn KHÔNG có per-task model — `_MODEL_HIDDEN_TASK_FIELDS = {"acp_command", "acp_args"}` chỉ che transport, không phải model; giới hạn \"delegation 1 model\" còn nguyên ở bản mới nhất.**

- `delegate_task(goal, context, tasks, max_iterations, role, background)` — **KHÔNG có tham số model**. Model subagent do config `delegation.*` quyết định; tool không nhận model từ prompt.
- Config `delegation` chỉ có `max_iterations` → subagent **inherit model parent** (vd `cmc/deepseek/deepseek-v4-flash` từ 9router) → KHÔNG phải Luna/high → KHÔNG đạt rule AGENTS.md "fresh pinned Luna/high worker".
- **KHÔNG mix được model theo vai qua subagent trong Hermes app**: mọi subagent chạy cùng 1 model (delegation.*). "Worker Luna/high + planner Sol + auditor Gemini qua subagent" là bất khả ở Hermes. Plan/audit model khác phải đi qua CLI wrapper. (Codex app cũng chỉ spawn subagent được trong catalog GPT — xem mục "Codex app: subagent chỉ trong catalog GPT" bên dưới.)

Để Hermes app chạy đúng rule "worker Luna/high" (thêm vào `config.yaml`):
```yaml
delegation:
  provider: cockpit
  model: gpt-5.6-luna
  reasoning_effort: high
  max_iterations: 50
```
- Provider `cockpit` đã có sẵn trong config (`custom_providers`: `http://localhost:60818/v1`, `api_mode: codex_responses`, models gpt-5.6-luna/sol/terra) + `COCKPIT_API_KEY` trong `.env`. Kiểm chứng được: `resolve_runtime_provider('cockpit','gpt-5.6-luna')` trả đúng bundle (provider custom, codex_responses, base_url cockpit) và endpoint `/v1/models` còn sống.
- `delegation.reasoning_effort: false` = tắt thinking cho subagent (boolean được giữ nguyên, không bị ép thành inherit).
- Set `delegation.provider` → subagent **không kế thừa ACP transport của parent** (dùng API direct); `api_mode` cũng không inherit khi provider khác parent (tránh 404 sai endpoint).
- **QUYẾT ĐỊNH 2026-08-06 (user): KHÔNG pin `delegation.model`.** Config trên đĩa chỉ có `delegation: {max_iterations: 50}` — model/provider/reasoning_effort TRỐNG → subagent inherit model cha (deepseek-v4-flash). User chọn: tạo file rule riêng `D:\\Taadaa\\HERMES_SUBAGENT_RULES.md` (ngoài mọi git repo, KHÔNG auto-load → không đụng AGENTS.md, không phát sinh policy audit) + pointer trong memory. Memory là cơ chế DUY NHẤT để model biết đọc file rule nào (inject mọi session). Trước khi delegate ở Taadaa → đọc file rule đó.
- **Delegation concurrency (user hỏi "số worker chạy mỗi lần ra lệnh" 2026-08-08)**: config hiện tại KHÔNG set → **default = 3 worker song song** (`tools/delegate_tool.py:118 _DEFAULT_MAX_CONCURRENT_CHILDREN = 3`, đọc `delegation.max_concurrent_children` từ config.yaml > env `DELEGATION_MAX_CONCURRENT_CHILDREN` > default 3); `max_spawn_depth` không set → 1 (flat, worker không spawn được worker con); `max_iterations: 50`. Dispatch 1 task = 1 worker; batch N task = tối đa 3 cùng lúc, phần còn lại xếp hàng. Tăng >10 có warning log (mỗi child tiêu token độc lập, chi phí nhân tuyến tính — `delegate_tool.py:368-376`).

### Đặt file rule Hermes ở đâu — cơ chế context file (source `agent/prompt_builder.py`)

- Priority cứng, **first match wins — chỉ LOAD 1 file, KHÔNG merge**: `.hermes.md`/`HERMES.md` (walk cwd → git root) → `AGENTS.md` (cwd only) → `CLAUDE.md` (cwd only) → `.cursorrules` (cwd only). (`build_context_files_prompt` ~dòng 1987.)
- `D:\Taadaa` KHÔNG phải git repo → `.hermes.md` ở root chỉ load khi cwd trực tiếp = `D:\Taadaa`; chạy trong repo con (automation-core, Tiktok_Reg...) walk dừng ở git root con → KHÔNG thấy. Và khi cwd=root, `.hermes.md` CHE hoàn toàn AGENTS.md (mất policy chung) → đặt `.hermes.md` root là phương án TỆ NHẤT.
- Tên `hermes.md` (không dấu chấm) KHÔNG bao giờ auto-load — chỉ `.hermes.md`/`HERMES.md` (`_HERMES_MD_NAMES`, dòng 82).
- Model/app KHÔNG tự chọn được cấu hình: app chọn file context theo priority cứng; model chỉ thấy nội dung được inject (thấy tên model trong system prompt nhưng không biết đường dẫn file rule). Cơ chế "trỏ tới file rule" bền vững = **memory**.
- `hermes config get` KHÔNG tồn tại (chỉ `show/edit/set/path/env-path/check/migrate`); `hermes config show` không hiển thị section delegation → muốn xem delegation phải đọc thẳng config.yaml.

Plan/audit bằng model khác (AG Claude/Sol/Terra/OpenCode/Command Code) trong Hermes app: gọi **CLI wrapper trong terminal** — AG audit qua `D:/Taadaa/reports/ag-audit/ag_audit_direct.py` (wrapper `tools/invoke-ag-audit.ps1` ĐÃ DEPRECATED 2026-08-10 — xem mục Audit wrapper bên dưới), `invoke-opencode-audit.ps1`, `invoke-command-code-9router-audit.ps1`, `claude-final-audit` (khi quota gate cho phép), hoặc `codex exec --model gpt-5.6-sol` (plan audit). KHÔNG qua subagent. **3 wrapper gemini cũ (`invoke-gemini-9router-audit.ps1`, `invoke-gemini-api-audit.ps1`, `invoke-gemini-audit.ps1`) ĐÃ BỊ VÔ HIỆU (2026-08-08, stub `GEMINI_AUDIT_DISABLED_POLICY_V5` + exit 23, backup `.bak-v5-*` giữ cạnh file)** — đừng gọi, đừng đọc chúng làm nguồn tham chiếu param nữa.

### Audit wrapper invocation quirks (live 2026-08-08 — 3 wrapper fail, đã chẩn đoán + thêm AG wrapper)

Khi gọi wrapper audit từ bash (git-bash) trên Windows, tránh các lỗi này:

0. **AG audit — `invoke-ag-audit.ps1` ĐÃ DEPRECATED (2026-08-10)**: header ghi rõ *"KHÔNG DÙNG wrapper này — thay bằng `bash D:/Taadaa/reports/ag-audit/run-ag-audit.sh <repo-path> <commit> [model] [timeout]`"* (wrapper treo ở `Invoke-RestMethod` PowerShell 5.1, timeout không trigger). Chính nó gọi `python D:/Taadaa/reports/ag-audit/ag_audit_direct.py <prompt-file> <model> <out> <timeout>` — **dùng thẳng `ag_audit_direct.py` cho audit pre-commit custom prompt** (như Phase 9B.1: build prompt file qua builder, gọi `python .../ag_audit_direct.py <prompt.txt> ag/claude-opus-4-6-thinking <response.md> 600`). Đọc prompt từ file (không cần `git show`); model default `ag/claude-sonnet-4-6`, luôn truyền `ag/claude-opus-4-6-thinking`; body kèm `reasoning_effort: high`; `max_tokens: 6000`; cần `NINEROUTER_API_KEY`; đọc response từ file OUT (dòng đầu = verdict). Verdict parse: `AG_AUDIT_VERDICT=APPROVED|MINOR_FIXES|REJECT|UNPARSEABLE`. **PITFALLS 2026-08-15 (audit plan không-có-diff qua `ag_audit_direct.py`):** (a) truyền **Windows path** — MSYS `/tmp/...` → `FileNotFoundError` (bash heredoc tạo file ở MSYS temp, Python Windows không thấy; viết prompt bằng `write_file` vào `%TEMP%` với Windows path rồi truyền path đó); (b) response dạng `## Verdict\n\n**APPROVED**` → wrapper in `AG_AUDIT_VERDICT=UNPARSEABLE` dù model đã APPROVE (regex không khớp markdown) — **đọc file RESPONSE để lấy verdict thật, không tin stdout wrapper**; (c) chạy >500s (prompt dài + thinking high) → chạy background `notify_on_complete=true` (foreground max 600s không đủ). Full recipe: `references/ag-audit-direct-path-verdict-pitfalls.md`.

1. **`invoke-gemini-9router-audit.ps1`**: `-ContextPath` là `[string[]]` — truyền `@("a","b")` TỪ BASH bị bash nuốt (`syntax error near unexpected token '('`) → **bỏ `-ContextPath` hoàn toàn**, prompt mô tả đủ đường dẫn file (prompt đã nêu path; wrapper chỉ cần `-RepoRoot` + `-PromptFile`). Nếu 9router trả `NINEROUTER_REQUEST_FAILED status=400 {"error":{"message":"Invalid JSON body"}}` với `context_files: []` → là payload từ chối (context trống hoặc body lỗi) — chuyển fallback model kế, không retry y hệt.
2. **`invoke-opencode-audit.ps1`**: `-Prompt` là text (KHÔNG phải file) — đọc file trước: `PROMPT_TEXT=$(cat file); powershell ... -Prompt "$PROMPT_TEXT"`. Nếu opencode cascade `OPENCODE_AUDIT_FAILED_NON_QUOTA_EXIT_1` (nemotron→ling đều exit 1) → opencode CLI hỏng/unavailable, chuyển Command Code/Codex — KHÔNG coi là quota (non-quota exit khác `OPENCODE_AUDIT_EXHAUSTED`).
3. **`invoke-command-code-9router-audit.ps1`**: có `#requires -Version 7.0` → **bắt buộc `pwsh`, KHÔNG `powershell` (5.1 fail `ScriptRequiresUnmatchedPSVersion`)**. Pitfall: `which pwsh` trả `C:\Users\Kibe\.codex\shell\pwsh` — đó là shim 5.1, KHÔNG phải PS7. Kiểm tra `pwsh -Command '$PSVersionTable.PSVersion'` Major=7 mới dùng; PS7 thật ở `C:\Program Files\PowerShell\7\pwsh.exe` (nếu máy chưa cài → báo user cài PowerShell 7, hoặc nhảy thẳng Codex fallback).
4. **Fallback cuối — Codex reviewer độc lập** (khi cả 3 wrapper trên đều fail): `codex exec --ephemeral --sandbox read-only` + model route tới Sol (`gpt-5.6-sol`) + reasoning high; prompt verdict `APPROVED | MINOR_FIXES | REJECT` dòng đầu; KHÔNG reuse/resume session implementer.

5. **PITFALL PROMPT LỚN >30KB qua CLI audit (2026-08-09, audit ladder 4 tầng Tiktok-video)**: prompt audit gộp diff ~47KB → 3 lỗi liên tiếp cùng nguyên nhân:
   - `claude -p "$(cat prompt.txt)"` → bash **"Argument list too long"** (Windows/MINGW argv giới hạn ~32KB) — KHÔNG phải lỗi Claude. FIX: `--append-system-prompt-file prompt.txt` + `-p "Audit theo appended system prompt. Trả verdict dòng đầu: APPROVED|MINOR_FIXES|REJECT"`.

6. **PITFALL `claude -p ... | tail -N` CẮT MẤT FINDINGS (2026-08-16, audit plan follow-integration 11 vòng)**: audit plan qua `claude -p --append-system-prompt-file <file> "..." | tail -20/35/40` — **2 lần bị cắt mất findings quan trọng** (vòng 7: "2 điểm cần bổ sung" mất; vòng 8: F1-F3 đầu mất vì tail 20). Verdict nằm cuối nên tưởng đủ, nhưng **phần đầu (F1/F2 blocker) hoặc phần cuối (action cần thêm) bị mất** → sửa plan thiếu findings, audit vòng lặp kéo dài. FIX: **redirect ra file thay vì pipe tail**:
   ```bash
   claude -p --settings '{"reasoning":{"effort":"high"}}' --append-system-prompt-file <prompt.txt> "..." > <out.txt> 2>&1
   ```
   rồi đọc file đầy đủ sau khi process xong (background + notify_on_complete). Nếu bắt buộc tail, dùng `tail -60+` và đọc cả 2 đầu (`head` + `tail`).
   **PITFALL liên quan — audit vòng lặp dài là BÌNH THƯỜNG khi findings giảm dần**: plan follow-integration mất 11 vòng MINOR_FIXES trước APPROVED; mỗi vòng bắt thêm 1-3 test sót/timing ambiguity (pattern "mỗi vòng 1-3 findings mới" = auditor đang verify từng chi tiết thật, TỐT). Ngưỡng: findings giảm dần + core design không đổi → tiếp tục; findings mới toàn bộ + design đổi mỗi vòng → dừng, giải thích lại vấn đề gốc cho user (PITFALL "user không hiểu mình đang làm gì" 2026-08-08).
   - `codex exec "$(cat prompt.txt)"` → **cùng lỗi argv**. FIX: pipe stdin `cat prompt.txt | codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol -c model_reasoning_effort="high"` — codex tự đọc prompt từ stdin khi [PROMPT] trống.
   - `invoke-ag-audit.ps1` (AG) với prompt 47KB + reasoning high: **chạy >500s không ghi verdict file gì** (wrapper timeout 480s → kill, file 0 bytes) dù smoke-test `ag/claude-opus-4-6-thinking` 200/2.2s. Nguyên nhân: prompt dài + thinking high làm AG nghĩ rất lâu — KHÔNG phải model chết. Nguyên tắc: **smoke-test model trước bằng curl prototype; nếu prompt >30KB thì ưu tiên Claude CLI `--append-system-prompt-file` hoặc Codex stdin trước AG wrapper**; khi AG chạy, set `-TimeoutSeconds 600+`.
   - Claude CLI trả `API Error: Internal server error` (500) sau ~4 phút → transient server, retry/đổi route, không phải lỗi prompt.
   - **Kết quả thực 2026-08-09**: Sol qua stdin chạy thành công nhất (exit 0, verdict REJECT 8 P1 + 2 P2 đầy đủ) — khi Claude CLI lỗi server + AG treo, nhảy thẳng `codex exec --sandbox read-only --model gpt-5.6-sol` với stdin là đáng tin nhất.

6. **PITFALL `claude -p ... | tail -N` CẮT MẤT FINDINGS (2026-08-16, audit plan follow-integration 11 vòng)**: audit plan qua `claude -p --append-system-prompt-file <file> "..." | tail -20/35/40` — **2 lần bị cắt mất findings quan trọng** (vòng 7: "2 điểm cần bổ sung" mất; vòng 8: F1-F3 đầu mất vì tail 20). Verdict nằm cuối nên tưởng đủ, nhưng **phần đầu (F1/F2 blocker) hoặc phần cuối (action cần thêm) bị mất** → sửa plan thiếu findings, audit vòng lặp kéo dài. FIX: **redirect ra file thay vì pipe tail**:
   ```bash
   claude -p --settings '{"reasoning":{"effort":"high"}}' --append-system-prompt-file <prompt.txt> "..." > <out.txt> 2>&1
   ```
   rồi đọc file đầy đủ sau khi process xong (background + notify_on_complete). Nếu bắt buộc tail, dùng `tail -60+` và đọc cả 2 đầu (`head` + `tail`).
   **PITFALL liên quan — audit vòng lặp dài là BÌNH THƯỜNG khi findings giảm dần**: plan follow-integration mất 11 vòng MINOR_FIXES trước APPROVED; mỗi vòng bắt thêm 1-3 test sót/timing ambiguity (pattern "mỗi vòng 1-3 findings mới" = auditor đang verify từng chi tiết thật, TỐT). Ngưỡng: findings giảm dần + core design không đổi → tiếp tục; findings mới toàn bộ + design đổi mỗi vòng → dừng, giải thích lại vấn đề gốc cho user (PITFALL "user không hiểu mình đang làm gì" 2026-08-08).

### Codex app: subagent chỉ trong catalog GPT — audit model khác hệ cũng phải CLI

Kiểm chứng 2026-08-05 (`~/.codex/cockpit-local-access-model-catalog.json` — file Codex desktop app tải về, nguồn sự thật cho model app hiển thị/spawn được):

- Catalog app chứa ĐÚNG 10 model, toàn hệ GPT: `gpt-5.6-sol/terra/luna`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`, `gpt-5.3-codex-spark`, `GPT Image 2`, `codex-auto-review`. KHÔNG có Gemini/Claude/DeepSeek/Command Code.
- 9router (`localhost:20128`) chỉ khai báo trong `config.toml` CLI (`[model_providers.9router]`, `wire_api="responses"`), KHÔNG trong catalog app → **Codex GUI không spawn được subagent model ngoài GPT**.
- → Audit bằng Gemini/Claude/Command Code/OpenCode/DeepSeek: **cả 2 app đều phải qua CLI wrapper** (cùng endpoint 9router `:20128`). Chỉ Luna/Sol/Terra/GPT là native trong Codex app (qua `codex_local_access` cockpit `:60818`).

### Subagent model khác DeepSeek Flash (cùng provider) — Hermes làm được — ĐÃ XÁC MINH LIVE

`delegation.*` là 1 model cố định cho MỌI subagent, nhưng model đó KHÔNG bắt buộc trùng main session: vì cùng provider 9router, đặt `delegation.provider: 9router` + `delegation.model: cmc/deepseek/deepseek-v4-pro` → subagent chạy DeepSeek v4 Pro qua subagent (không cần CLI). Rule tổng quát: **model khác main nhưng CÙNG provider → subagent OK; model khác provider → CLI**. Lưu ý: đổi `delegation.*` = toàn bộ subagent đổi model, không mix theo vai.
- **Xác minh live 2026-08-06**: curl `POST http://127.0.0.1:20128/v1/chat/completions` model `cmc/deepseek/deepseek-v4-pro` → 200, trả `model: deepseek/deepseek-v4-pro` + `reasoning_content` → deepseek-v4-pro gọi in-app được, KHÔNG cần CLI.
- **UPDATE 2026-08-06 (user add GPT upstream vào 9router)**: `gpt-5.6-luna/terra/sol` (bare hoặc `cx/` prefix) giờ **cũng gọi được qua 9router HTTP** → Hermes gọi terra/sol in-app cho plan/audit KHÔNG còn bắt buộc `codex exec --model ...`. Claim cũ "Terra/Sol = Codex CLI-only" đã hết hiệu lực. Catalog app Codex (`cockpit-local-access-model-catalog.json`) vẫn GPT-only — điểm khác biệt giữa 2 app nằm ở SUBAGENT spawn (Codex app spawn được terra/sol native; Hermes phải HTTP/CLI), không phải ở khả năng gọi model.
- Ladder theo vai cho Hermes: worker=flash (main) → plan=deepseek-v4-pro in-app (9router) → review/audit=terra/sol qua 9router HTTP (hoặc Codex CLI) → case khó=sol.
- Recipe gọi 9router HTTP (tool_choice=none chống fake tool_calls của deepseek-pro; Claude upstream 403 payload lớn → đổi model; Kimi finish=length → chia vòng): xem `agent-model-routing` → `references/9router-http-calling.md`.

### 2-mode symmetric orchestration (user chốt 2026-08-06 — file `D:\Taadaa\HERMES_SUBAGENT_RULES.md`)

Model tự nhận diện app từ 2 tín hiệu trong system prompt: (1) dòng Model (`cmc/deepseek/deepseek-v4-flash`=Hermes; `gpt-5.6-luna`=Codex), (2) bộ tool (Hermes có `skill_view`/`memory`/`cronjob`/`session_search`; Codex có `apply_patch`/MCP).
- **HERMES mode**: worker = deepseek-v4-flash (delegate_task inherit) → fail → deepseek-v4-pro (9router HTTP, read-only) → fail → gpt-5.6-terra → sol (9router HTTP, read-only). Audit = terra/sol.
- **CODEX mode**: worker = luna/high native subagent → fail → terra/sol → fail → deepseek-v4-pro (read-only). Audit = deepseek-v4-pro.
- Golden rule: worker = subagent spawn cùng app (THẰNG DUY NHẤT patch/live); rescuer/auditor (v4-pro/terra/sol) READ-ONLY — chỉ plan/verdict, KHÔNG patch. **v4-pro audit/rescue flash worker là HỢP LỆ (cùng deepseek family nhưng cấp cao hơn — user duyệt 2026-08-07; đây là rescuer chuẩn theo bảng Escalation). "Crossover reviewer khác loài" KHÔNG phải hard gate cấm v4-pro — chỉ là ưu tiên tăng cường: khó vừa → terra, khó thật → sol; Codex luna→v4-pro vì khác hãng.**
- **Fallback worker khi spawn fail (chốt 2026-08-06 — session-as-worker, xem mục scope-split v4→v7)**: KHÔNG có model fallback trong policy; tool layer (Hermes `fallback_providers`, 9router) lo quota/outage. Worker subagent spawn CONFIRMED fail → `SUBAGENT_RUNTIME_UNAVAILABLE` → session tự làm worker bằng model session. Luna/high ≡ flash/max NGANG NHAU (không downgrade).

### Hermes vision fallback cho main model text-only (DeepSeek Flash không xem ảnh) — ĐÃ HOẠT ĐỘNG

Hermes có sẵn auxiliary vision router (`agent/auxiliary_client.py`): khi main provider/model bị catalog `agent/image_routing.py::_lookup_supports_vision` đánh dấu text-only (DeepSeek nằm trong đó), `vision_analyze`/`browser_vision` tự fallback sang vision backend khác → trả text cho main model xử lý tiếp. **Đã cấu hình + verify E2E 2026-08-05**: model vision sống qua 9router là **`gemini/gemini-3.6-flash`** (chính là model rule audit `invoke-gemini-9router-audit.ps1` — 1 model dùng chung audit + vision). Cấu hình:

```yaml
auxiliary:
  vision:
    provider: custom
    base_url: http://127.0.0.1:20128/v1
    model: gemini/gemini-3.6-flash
    # api key tự lấy từ env NINEROUTER_API_KEY — KHÔNG cần field api_key
```

Cách set + verify (đầy đủ trong `agent-model-routing` → `references/model-capability-matrix.md`):
- **PHẢI set qua `hermes config set auxiliary.vision.<key> <value>`** — agent bị chặn ghi thẳng `config.yaml` (security guard: "Agent cannot modify security-sensitive configuration"). Set xong hiệu lực sau restart/session mới.
- Verify E2E: `async_call_llm(task='vision', messages=[...image_url...])` — **bắt buộc `task='vision'`** để nó đọc config `auxiliary.vision`; bỏ task= → dùng main model → báo "không xem được ảnh" dù đường vision vẫn chạy. Hoặc test qua `vision_analyze_tool(image_url=<file>, user_prompt=...)`.
- **Pitfall ảnh test**: ảnh PNG tí hon (2x2/8x8 px) bị 9router từ chối `400 "Unable to process input image"` — đây là lỗi KÍCH THƯỚC, không phải model thiếu vision. Dùng ảnh ≥ ~64x64 px hoặc screenshot thật khi probe.
- **Pitfall suffix**: model trong dashboard hiển thị `gemini/gemini-3.6-flash(high)` — suffix `(high)` là hiển thị thinking level, KHÔNG được truyền vào model name (400).
- `gemini/gemini-2.5-pro` qua 9router: text OK nhưng vision FAIL dù ảnh đủ lớn → dùng `gemini-3.6-flash` cho vision.
- Test 2026-08-05 trước đó ("chưa có model vision sống") đã lỗi thời — nguyên nhân là ảnh test quá nhỏ + prefix `gc/` sai, không phải thiếu vision.

## Audit Routing v5 (user chốt hướng 2026-08-07 — thay thế "Gemini 3.6 Flash" trong route)

User đổi route audit (chi tiết test + ladder đầy đủ: `references/audit-routing-v5-models.md`):

- **Bỏ hẳn Gemini 3.6 Flash khỏi audit route** (vẫn giữ làm vision aux — `auxiliary.vision` riêng, không liên quan audit).
- **PRIMARY = `ag/claude-opus-4-6-thinking`** (Antigravity qua 9router, reasoning high). Sonnet 4.6 qua CLI KHÔNG dùng — sonnet-4.6 CHỈ qua 9router (legacy backup khi opus-4-6-thinking 429/401).
- **Claude CLI user**: `claude-opus-5`/high (task khó) — `sonnet-5` ĐÃ BỎ khỏi route (2026-08-08). Quota gate 85%/5h + 90%/tuần. **PITFALL: flag `--reasoning-effort` không tồn tại — dùng `--settings '{"reasoning":{"effort":"high"}}'`** (smoke-test OK cả 2 model).
- **GPT route = `cx/*` qua 9router codex** (test OK): `cx/gpt-5.6-luna` (dễ) / `cx/gpt-5.6-terra` (khó vừa) / `cx/gpt-5.6-sol` reasoning high (khó thật). **CẤM `v98/gpt-5.6-*-max`** (429 new_api_error upstream, không phải quota — đừng retry mù).
- Bỏ mục "fresh Codex reviewer độc lập" riêng — trùng cx route (cùng key 9router).
- Escalation: `ag/claude-opus-4-6-thinking` (khi CLI hết quota mà case vẫn khó).
- **One-slot làm rõ**: 1 evidence audit 1 lần; worker sửa xong = evidence MỚI → re-audit hợp lệ (material change = slot mới). KHÔNG cấm audit tiếp sau sửa — chỉ cấm review cùng evidence 2 lần.
- **ĐÃ CHỐT (2026-08-08 — policy v5 vào AGENTS.md)**: Claude CLI `claude-opus-5` medium đặt TRƯỚC `cx/gpt-5.6-sol` (phương án A — quota-gated qua preflight nên không đốt quota Pro). **BỎ hẳn `sonnet-5` khỏi CLI audit** — user: "bỏ luôn sonnet 5 high, chỉ dùng opus5 medium cho task khó; task dễ/trung bình tự chui cx GPT trước" → CLI Claude chỉ còn 1 vai: opus-5 medium cho task khó thật.
- **Vá fail-closed sau AG audit thật (2026-08-08)**: chạy audit thiết kế v5 bằng chính `ag/claude-sonnet-4-6` (reasoning high, prompt verdict) → **acc Antigravity KHÔNG bị ban sau 1 slot audit thật** (dùng acc mới cho audit thật là cách test ban hợp lệ, không chỉ smoke); verdict REJECT với 5 HIGH (ladder không exit condition, fail-closed thiếu, mơ hồ ai quyết chuyển lớp, one-slot material-change không định lượng, audit gate không enforce) → vá 2 điều khoản vào AGENTS.md: (1) `Fail-closed hard stop` — MỌI route fail → `AUDIT_ALL_ROUTES_FAILED: <last_error>`, dừng task, KHÔNG deploy/merge/commit/live-act, báo user 1 dòng; (2) `Audit route switching` — chỉ coordinator chuyển lớp, dựa signal cụ thể (HTTP 429/401, timeout >60s, empty response, non-zero exit), ghi `AUDIT_ROUTE_SWITCH: layerX -> layerY, reason=<signal>`; verdict usable dừng ladder ngay. One-slot = 1 evidence 1 lần; worker sửa = evidence MỚI → re-audit hợp lệ (user xác nhận đúng: "audit xong worker sửa chưa vừa ý thì audit tiếp chứ" — material change mở slot mới, không vi phạm one-slot).
- **NÂNG CLI Claude lên HIGH (2026-08-08 — chốt tiếp theo policy v5)**: user: "bên opus cũng set high cho t luôn, nói chung mức reasoning tất cả đều set high nếu có thể" → Claude CLI `claude-opus-5`/high cho task khó (nâng từ mức cũ); sweep sạch mọi chỗ `sonnet-5` mô tả route ACTIVE (AGENTS.md 6 chỗ sót + SKILL.md dòng user) → CLI Claude CHỈ còn đúng 1 vai: `claude-opus-5`/high. Mọi reasoning effort trong audit route = HIGH: worker flash/luna, AG sonnet-4-6, AG opus-4-6-thinking, cx luna/terra/sol, Claude CLI opus-5.

## Codex Model Ladder (theo D:\Taadaa\AGENTS.md)

Khi dispatch Codex implement, chọn model theo độ khó (không phải mặc định):

- **Luna / high**: task bounded rõ output (scan, log/XML extraction, structured summary, test fixture, mechanical edit có spec).
- **Luna / high**: bounded work cần tracing/verification thêm.
- **Terra / high**: scoped implementation/recovery patch, code-path tracing, non-mechanical patch, targeted retry, review Luna evidence. **Terra là recovery patch owner.**
- **Sol / high**: trước khi đổi `automation-core`, shared recovery/lock/verifier/scheduler, account/OTP/2FA sensitive, multi-consumer. Không phải mặc định chỉ vì task liên quan automation.
- **Sol / ultra**: chỉ khi ULTRA_GATE=YES (independent shards/deepest investigation).
- Luna không được là final decision-maker cho live automation outcomes, SUCCESS/FINAL_BLOCKED, root-cause, recovery choices, account/device/workbook actions — Terra/Sol phải review evidence/diff/verifier trước.
- Model choice không authorize live actions ngoài scope user; live/recovery luôn theo recovery state machine + verifier proof.

## Codex Implementer Escalation (Sol high → extra high → ultra)

Khi Codex implementer fail/treo ở model mặc định: nâng dần `-c model_reasoning_effort="high"` → `"extra_high"` → `"ultra"`. **Mỗi nấc là phiên Codex MỚI hoàn toàn (không resume session cũ)** và **phải làm khác đi nấc trước** (theo `D:\Taadaa\AGENTS.md`: kèm what-was-tried/why-failed + materially different plan, không lặp y hệt prompt). Sol/ultra chỉ khi có independent shards (Automatic Ultra Gate). Smoke-test trước mỗi nấc (`Respond with exactly: READY`). Codex hay treo ở cuối sau khi đã ghi xong file — kiểm tra file/test trước khi kill.

## Fallback OpenCode Free Khi Codex + Claude Đều Fail

Theo `D:\Taadaa\AGENTS.md`: audit order **AG `ag/claude-opus-4-6-thinking` → cx luna/terra → Claude CLI `claude-opus-5` (trước cx sol) → OpenCode free → Command Code**. Khi Claude hết quota/fail và Codex cũng fail/treo → dùng **model free của OpenCode** làm audit/review read-only: ưu tiên `opencode/deepseek-v4-flash-free`, fallback free model khác khi quota/rate-limit. Dùng wrapper `taadaa-review`/`invoke-opencode-audit.ps1` nếu có; smoke-test trước; verdict `APPROVED | MINOR_FIXES | REJECT`; label `OPENCODE_AUDIT` (không gọi là Claude approval). OpenCode unavailable → `OPENCODE_RUNTIME_UNAVAILABLE` → cx route sol (`CODEX_FALLBACK_AUDIT`) hoặc `ag/claude-opus-4-6-thinking` (case khó).

> **OpenCode catalog đổi (live 2026-08-07, UPDATE 2026-08-16) — model free HOẠT ĐỘNG hiện tại = `opencode/nemotron-3-ultra-free`**:
> `invoke-opencode-audit.ps1` mặc định cascade nemotron→ling. `opencode/deepseek-v4-flash-free`
> KHÔNG còn trong allowlist (`MODEL_UNAVAILABLE`/`MODEL_NOT_ALLOWED`); `opencode/ling-3.0-flash-free`
> cũng không (catalog hiện chỉ `ling-3.0-tiny-free`, `nemotron-3-ultra-free`, `longcat-2.0-free`,
> `north-mini-free`). **2026-08-07 chạy OK với `longcat-2.0-free` (verdict MINOR_FIXES đầy đủ),
> NHƯNG 2026-08-16 `longcat-2.0-free` FAIL `err_ee0a749e` còn `nemotron-3-ultra-free` chạy OK**
> (audit plan 3 quyết định mới → MINOR_FIXES 2 MUST FIX đầy đủ). Thứ tự thử khi cần
> OpenCode free: `nemotron-3-ultra-free` → `ling-3.0-tiny-free` → `longcat-2.0-free`; đừng mặc định
> theo tên model cũ ghi trong rule — **model free đổi availability thường xuyên, smoke-test từng cái trước khi dùng**. Nếu cascade trả `OPENCODE_AUDIT_FAILED_NON_QUOTA_EXIT_1` →
> opencode CLI hỏng/unavailable → chuyển Command Code/Codex (không coi là quota).

## Audit/Read-Only Dispatch

- `delegate_task(role=leaf)` không chọn model audit; child kế thừa model của session. Không dùng một Luna/Flash worker subagent để giả làm auditor. Audit plan/code phải đi đúng AG Opus primary hoặc fallback route theo rule workspace, thường qua wrapper/CLI. Giữ cùng model xuyên suốt re-audit của cùng evidence; chỉ worker mới được patch.

1. Viết audit spec (hoặc dùng diff thực tế).
2. Codex đọc file + phân tích (nếu COMPLEX) HOẶC bỏ qua (SIMPLE).
3. Hermes cross-verify CRITICAL/HIGH findings (`read_file()` ok).
4. Review v5 (AG `ag/claude-opus-4-6-thinking` → cx luna/terra/sol → Claude CLI `claude-opus-5` → OpenCode free → Command Code) → CONFIRMED/REJECTED.

## Trigger

"dùng rule điều phối", "dispatch codex claude", "gọi audit review", "gọi model ra review"

**BẮT BUỘC (bước 0 — mọi task có write trong repo Taadaa):** bất kỳ task nào yêu cầu write/edit/patch/build/deploy file code trong `D:\Taadaa` (kể cả khi user nói "làm đi", "sửa đi", "fix đi", "chạy lại") → **LOAD SKILL NÀY TRƯỚC** rồi mới phân loại + dispatch worker. Không load skill trước khi write = vi phạm COORDINATOR-WRITE GUARD (bài học 2026-08-07 lần 2: session tự patch core ui.py/device_recovery.py + social_reg_v1.py nhiều lần vì bỏ qua bước 0).

## Pitfall: AG audit hallucinate source + Claude "File access denied" → prompt audit phải SELF-CONTAINED (2026-08-16, release-always-lock)

- **AG `ag/claude-opus-4-6-thinking` audit plan bịa TOÀN BỘ source ảo**: response chứa một `device_lock.py` khác hẳn repo thật (API `device_name`/`lock_file`/`_try_acquire`/`_StaleLockReaped`/single-file lease — KHÔNG tồn tại; line numbers + docstring khác hẳn). `AG_AUDIT_VERDICT=UNPARSEABLE`, stdout lẫn source. Auditor không đọc được file thật (D:\ path) nên tự bịa. **KHÔNG BAO GIỜ tin response audit có source dump lạ — đối chiếu API reference với repo thật trước khi dùng verdict; bỏ audit đó, chuyển route.**
- **Claude CLI opus-5 "File access denied"** khi không đọc được D:\ path — vẫn cho verdict dùng được (MINOR_FIXES) vì prompt đã paste đủ verified facts. **Kết luận: prompt audit PHẢI self-contained** — paste REAL source (path + line numbers thật + hàm/signature/status sets) + đánh dấu rõ "đây là API THẬT (verified bởi coordinator); đừng bịa API khác; KHÔNG đọc file ngoài" + pitfalls repo + plan summary + open questions Q1..QN.
- Recipe đầy đủ + skeleton prompt + bằng chứng 3 vòng: `references/self-contained-audit-prompt-recipe.md`.
- **Full session log 5 vòng (REJECT → APPROVED) + quy trình reuse**: `references/plan-audit-multiround-release-always-2026-08-16.md` — gồm bảng timeline từng vòng (AG hallucinate → cx disconnect → Claude REJECT → MINOR_FIXES ×2 → APPROVED), quy trình 7 bước đã chứng minh (self-contained prompt, verify assumption bằng code, Δ-audit, route-switch, chặn audit lặp, worker TDD + verify độc lập, cấm git stash), và thiết kế v4 cuối cùng.
- cx route fail (`ERROR: stream disconnected` cockpit :60818) → đúng ladder chuyển Claude CLI opus-5, không retry cùng thứ (không phải lỗi prompt).
- **Verify assumption của auditor bằng code thật TRƯỚC khi sửa plan**: auditor giả định "state.json gate failed-locked chặn re-run" → đọc `serve()` thấy KHÔNG có gate → resolution theo USER INTENT (retry daily intentional — lock = mutex thuần), KHÔNG thêm gate ngoài yêu cầu. Ghi "VERIFIED/SUPERSEDED by code" cho từng finding vào plan.
- **Re-audit chỉ audit Δ** (vòng sau gửi "v2 findings → v3 resolutions + verified facts + checklist") — vòng 3 nhanh hơn hẳn. Findings giảm dần + design không đổi = đúng quỹ đạo.

## Pitfall: đổi constants scheduling phải grep validator files NGOÀI allowlist (2026-08-16, follow-integration)

Đổi constants dùng chung (sessions_per_block, block_anchors, pair_gap, inter_block_gap, slot_grid) → **grep toàn repo TRƯỚC khi chốt allowlist** — không chỉ file định nghĩa:
- `manifest.py` hardcode validate: `session_index not in (1,2)` reject, `len(block_entries) != 2` reject, `pair_gap not in (60,75,90)` reject, `session_slots != build_block_sessions(...)` (so sánh tuple chính xác), inter-block `< 180` reject → **3 sessions CRASH ngay khi picker gọi validate_manifest** nếu manifest.py không sửa.
- `models.py` có `SLOT_GRID_MINUTES = 15` (grid 15) — đổi grid 5 phải sửa cả đây (ngoài allowlist).
- Test files hardcode giá trị cũ (6 sessions, 07:00 anchors, len(entries)==6, golden vector hash CONSTRAINTS, len(grid_slots)==77) → đỏ hàng loạt.
- FIX: **worker phát hiện sớm blocker này (báo parent, không tự sửa ngoài allowlist)**; parent mở rộng allowlist + user duyệt ("Sửa luôn") → dispatch lại worker với allowlist đầy đủ. Lesson: khi plan đổi "shape" (số lượng/schedule structure), allowlist 4 file + tests là thiếu — phải quét dependency của constants.

### Checklist sau khi code shape mới land — validator vẫn crash picker (2026-08-16, test-fix phase9-authority)

Kế thừa mục trên: dù picker.py/manifest.py ĐÃ sửa theo plan, validator còn 5 gap khiến **picker CRASH trên chính output của nó** (44 test đỏ; premise "CHỈ SỬA TESTS — code đúng" là SAI, phải sửa production tối thiểu):
1. `required_keys` block thiếu field mới (`jitter_minutes` — picker emit 13 keys, validator đòi đúng 12) → reject MỌI block. Thêm field vào block dict = phải thêm vào validator.
2. `len(block["entry_ids"]) != 2` còn sót → reject 3-session.
3. `session_slots` canonical check gọi `build_block_sessions(...)` KHÔNG truyền `jitter_minutes` → jittered slots reject.
4. Inter-block gap `<90'` so trên slot THỰC (jittered) → gap thực 65-85' bị reject oan; fix = so **nominal (unjittered)** slots — anchors 06:00/12:30/19:00 + max pair gap 60 luôn để nominal ≥90' (design: "anchor cố định quyết định, KHÔNG enforce runtime").
5. **Anchor block 1 = window start (06:00) + jitter âm → s1 05:45/05:40 trước window → RESERVED_BLOCK_CONFLICT** → picker clamp `if block_index == 1 and jitter < 0: jitter = 0` (block 2/3 giữ ±20, anchor sâu trong window).
- Probe khi picker self-validation crash: monkeypatch `manifest_mod.validate_manifest = noop` (KHÔNG patch `picker_mod` — picker import validate_manifest BÊN TRONG `_pick_locked`).
- Golden vector recompute bằng stdlib hash đúng công thức test; source_revision/block_id KHÔNG đổi khi đổi shape, assignment/entry đổi.
- Checklist đầy đủ (dependency map, probe RNG, pattern sửa test hardcode): `references/scheduling-shape-change-validator-checklist.md`.

## Pitfall: test concurrency bằng CÔNG CỤ THẬT của farm (2026-08-16, max_workers test)

User hỏi "max_worker bao nhiêu vừa đủ — test chính xác kiểu gì": **đừng test bằng công cụ cũ/mô phỏng sai**:
- Sai lần 1: `adb shell uiautomator dump` — farm ĐÃ chuyển qua ATX service (port 7912) → user: "t chuyển qua dùng atx service hết r mà".
- Đúng: gọi API thật của atx-agent — `POST http://127.0.0.1:7912/uiautomator` (trong code: `_atx_http_request`, capture_recovery.py:1114) — forward `adb -s <dev> forward tcp:7912 tcp:7912` trước.
- Mô phỏng phiên thật: mở TikTok (`am start -n com.ss.android.ugc.aweme/.main.MainActivity`) + chờ load (S7 chậm → 8s) + 15 lần (đọc UI + swipe). Kết quả thật: parallel 30 = 0 lỗi (20/30 OK, 40 có 2 transient) → chốt max_workers 30.
- **Bài học kép**: (a) test tải phải dùng công cụ production (không phải công cụ mà farm đã bỏ); (b) mô phỏng phải kèm bước mở app + chờ load (không chỉ gọi API 1 lần) — tải thật nặng hơn nhiều.
- Pool worker semantics: "máy nào xong → máy khác vào ngay" = ThreadPoolExecutor đã có sẵn (multi_machine_feed_session.py:1048) — KHÔNG cần "tick 15' phức tạp" (user: "cứ max worker tại 1 thời điểm là bn thì máy nào chạy xong máy khác tham gia vào là đc mà"). Stagger per-machine cũng đã có sẵn (`_machine_start_stagger_ms = (2000, 8000)`, build_machine_launch_plan).

## Audit: session hiện tại đang ở lớp agent nào

Khi user hỏi "session của Hermes qua các lớp agent nào" / audit cấu trúc agent: xác định lớp bằng env signals (`HERMES_KANBAN_TASK`, `HERMES_UI_SESSION_ID`, `HERMES_SESSION_ID`, `delegation` config) + code locations (`AIAgent`→`init_agent`→`run_conversation`, `delegate_tool.py`, `kanban_tools.py`, `gateway/session.py`) — recipe + template kết quả: `references/agent-layer-identification.md`. Không cần chạy app; đọc env + code là đủ.

## Các section chi tiết (trim 2026-08-09)

> dispatch-history-and-ops-notes.md

