---
name: agent-review-loops
description: "Điều phối implement/review đến APPROVED với fallback reviewer khi Claude hết quota."
version: 1.2.0
metadata:
  hermes:
    tags: [orchestration, codex, claude, opencode, review-loop, preflight, live-validation]
    related_skills: [claude-code, codex, agent-model-routing, hermes-orchestration-dispatcher]
---

# Agent Review Loops

Dùng khi user yêu cầu điều phối coding agent, review chéo, hoặc làm đến khi hoàn tất.

## Quy trình bắt buộc

0. **Phân loại task**: SIMPLE (1-2 file, mechanical, không đụng shared core/sensitive) hay COMPLEX (core/shared/sensitive/multi-machine).
1. **SIMPLE → Hermes tự sửa code + test + verify.**
   **COMPLEX → viết task spec rõ ràng** vào file `tasks/<date>-<slug>.md` với đầy đủ: Goal, Scope, Acceptance Criteria, Constraints → dispatch Codex implement/sửa (background, pty=true, notify_on_complete=true).
2. **Claude/OpenCode CHỈ audit review** (KHÔNG BAO GIỜ implement). Dispatch Claude review **code thực tế** với prompt chuẩn (quota gate theo `D:\Taadaa\AGENTS.md`).
3. Nếu Claude/OpenCode trả `REJECT` hoặc `MINOR_FIXES`: **Hermes tự sửa theo findings** (SIMPLE scope) hoặc **dispatch Codex sửa** (COMPLEX scope), sau đó re-review.
4. Lặp đến khi reviewer trả `APPROVED`; không dừng ở suite xanh hoặc ad-hoc pass.
5. **Vẫn fail 2+ vòng CÓ DẤU HIỆU LẶP** (cùng findings, cùng chỗ treo/fail, không tiến triển) → **chuyển hẳn Codex implement**: phiên MỚI, kèm what-was-tried/why-failed + materially different plan (theo AGENTS.md), không lặp y hệt prompt. Claude/OpenCode vẫn chỉ review.
6. Verify cuối: chạy test, kiểm tra artifact.
7. Không hỏi user giữa loop; chỉ báo kết quả APPROVED/DONE hoặc hard stop an toàn.

### Claude Review Prompt Format

```
claude -p "Bạn là reviewer. Review TOÀN BỘ thay đổi code so với git HEAD.
[context về project và yêu cầu]

Trả lời DUY NHẤT một trong: APPROVED / MINOR_FIXES / REJECT.
Nếu MINOR_FIXES hoặc REJECT: list finding cụ thể, phân loại MAJOR/MINOR/NIT."
--allowedTools "Read,Bash(git *)" --max-turns 15
```

### Codex Fix Round Prompt Format

```
codex exec --sandbox danger-full-access "Sửa các lỗi từ code review:
MAJOR:
1. [finding cụ thể + fix]
MINOR:
2. [finding cụ thể + fix]
Sau khi sửa, chạy pytest verify."
```

## Audit Loop qua 9router HTTP (không cần CLI wrapper)

Khi cần planner/auditor từ Hermes mà model không phải deepseek-cha: gọi thẳng endpoint local 9router `http://127.0.0.1:20128/v1/chat/completions` (key `NINEROUTER_API_KEY`) — KHÔNG qua `codex exec`/CLI. Chi tiết model IDs, workaround, timeout: `references/9router-http-dispatch.md`.

**Workflow đã chứng minh (2026-08-06, AGENTS.md scope-split):**
1. **backup + sha256** file policy trước khi làm bất cứ gì (`cp file file.pre-scope-<ts>.bak`).
2. **v4-pro lên plan** (read-only, `tools:[]`, `tool_choice:"none"` — v4-pro tự phát minh `<tool_calls>` giả khi không ép).
3. **Sol/terra audit plan** (khác loài — Sol bắt lỗi v4-pro thật).
4. REJECT → sửa plan theo findings → audit lại (material change = mở slot mới).
5. Chỉ khi APPROVE mới cho worker (flash) thực thi sửa file thật.

**Bẫy Sol audit:**
- Sol chạy lâu (plan 15-30KB → 4-8 phút): chạy background script + `timeout=840`, KHÔNG foreground 300s.
- Output hay bị cắt (`finish=length`) — đọc file artifact đã ghi, không tin tail process; nếu cắt giữa, gọi vòng tiếp "trả lời NGẮN phần còn thiếu".
- Sol audit = gate thật: REJECT 5 vòng liên tiếp nghĩa là **vấn đề cấu trúc, không phải nội dung** (xem Pitfalls).
- **GPT upstream (Sol/Terra) hay 401 `token_invalidated` / 429 khi hết quota trong 9router** — khi đó fallback audit bằng `cmc/deepseek/deepseek-v4-pro` (cùng vai trò, khác loài với planer nếu planer cũng là deepseek — vẫn hợp lệ; nếu planer là v4-pro thì đổi sang Kimi `cmc/moonshotai/Kimi-K2.6` cho khác loài).

**Gemini audit — ĐÃ BỊ LOẠI KHỎI AUDIT ROUTE (2026-08-08, policy v5):** `gemini-3.6-flash` không còn trong audit route ("Removed models" trong AGENTS.md v5). Cả 3 wrapper gemini (`invoke-gemini-9router-audit.ps1`, `invoke-gemini-api-audit.ps1`, `invoke-gemini-audit.ps1`) đã bị ghi đè thành stub `GEMINI_AUDIT_DISABLED_POLICY_V5` + **exit 23** (backup `.bak-v5-<ts>` giữ bản gốc) — gọi chúng luôn exit 23, đừng đổ thời gian retry. Primary Auditor mới: `invoke-ag-audit.ps1` (AG Claude `ag/claude-sonnet-4-6` reasoning high qua 9router; escalation `ag/claude-opus-4-6-thinking`; exit-code taxonomy 0/20/21/22/1 + verify recipe: `9router-proxy-ops` skill §AG audit wrapper).

## OpenCode Free Audit Layer (2026-08-06 — đã set up, ĐỨNG TRƯỚC Gemini)

User yêu cầu: **lớp audit OpenCode nằm sau GPT review, trước fail-closed**. Audit chain ĐÃ CHỐT v6 (2026-08-09, user chốt sau Sol vs AG cross-exam):
`AG Claude (invoke-ag-audit.ps1, chính) → GPT review (Terra/Sol) → opencode-audit combo → AUDIT_ALL_ROUTES_FAILED`. Gemini/Command Code/`cmc/*` loại hẳn.

**Cách chạy (wrapper đã test OK):**
```
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\tools\invoke-opencode-audit.ps1 \
  -RepoRoot "D:\Taadaa" -Prompt "<audit prompt>" -OutputDirectory "D:\Taadaa\reports\opencode-audit"
```
- **Model cascade (2026-08-09, user chốt — combo `opencode-audit` trong 9Router):**
  `oc/nemotron-3-ultra-free` → `oc/big-pickle` → `oc/longcat-2.0-free` → `oc/ling-3.0-tiny-free`.
  **KHÔNG dùng `oc/deepseek-v4-flash-free`/`opencode-free`** — resolve thành DeepSeek Flash = worker Hermes (user chỉnh 2026-08-09). Có thể ép 1 model bằng `-Model <id>` (phải nằm trong combo).
- **Hồ sơ model free đã test (2026-08-06):** `nemotron-3-ultra-free` = mạnh nhất (NVIDIA) nhưng **hay 502 `ResourceExhausted (32/32)`** khi chạy agent+json — cascade xuống model kế (thử lại lần sau thường OK vì limit reset); `ling-3.0-flash-free` = ổn định, verdict thật; `longcat-2.0-free`/`north-mini-code-free` = verdict thật; **loại:** `mimo-v2.5-free` (trả template verdict giả, chỉ echo format — không audit thật), `laguna-s-2.1-free` (không output), `freemodel/gpt-5.6-*` (401 Insufficient balance — cần key riêng). **Rule: model free hay đổi — trước khi thêm model mới vào cascade phải smoke-test thật** (`opencode run --dir <repo> --agent taadaa-review --format json --model <m> "Reply VERDICT: APPROVE"`), đừng tin tên model.
- **Auto-update model free (user hỏi 2026-08-06):** wrapper đọc `opencode models` LIVE mỗi lần chạy (filter `opencode/.+-free`) nhưng cascade pin model cố định → model mới không tự vào. **Khuyến nghị: tự vào lấy** (`opencode models` + smoke-test) thay vì auto-đổi cascade — model free hay đổi, auto chọn nhầm model dở (như mimo template-giả). Không làm cron auto-sync trừ khi user yêu cầu.
- Agent: `taadaa-review` (đã có ở `~/.config/opencode/agents/taadaa-review.md`).
- **Output JSONL là UTF-16** (`b'\xff\xfe'`) — đọc bằng `open(path, encoding='utf-16')`, parse từng dòng JSON, text nằm trong `part.type=='text'`; verdict + findings ở các text block cuối. Đừng decode utf-8 (UnicodeDecodeError).
- Verdict có thể không đúng chữ `APPROVED` — suy luận từ findings: hết MAJOR/MINOR → APPROVED; P1/P2/P3 là phân loại mức độ (P1 = mâu thuẫn trực tiếp, P3 = cosmetic).

**Giá trị riêng của OpenCode audit:** phát hiện **findings xuyên section** mà ds-pro/Gemini (chỉ xem vùng được trích) không thấy — vụ AGENTS.md v8: OpenCode đọc TOÀN file, bắt 6 findings Luna-only ở các section khác ngoài 2 vùng đã sửa (v4 header, canonical block, "DeepSeek never executor", "remains Luna/high", fallback ordering, watchdog/escalation headings). **Dùng OpenCode khi cần audit policy toàn file / tìm mâu thuẫn cross-section**; ds-pro/gemini khi chỉ cần xác nhận vùng sửa.

**Bẫy:** wrapper Gemini (`invoke-gemini-9router-audit.ps1`) **đã bị stub exit 23** (policy v5, 2026-08-08) — không gọi nữa; dùng `invoke-ag-audit.ps1` (AG Claude) hoặc OpenCode trước. `freemodel/*` (gpt-5.6-luna free) → 401 Insufficient balance — không dùng được.

## Khi nào cần plan + audit (gate, không mặc định)

| Độ khó | Ví dụ | Rescuer/Auditor |
|---|---|---|
| Thường | debug 1 bug, sửa 1 file consumer | KHÔNG audit — flash → v4-pro cứu → xong |
| Khó vừa | nhiều file, logic phức tạp 1 repo | **terra** (plan/audit) |
| Khó thật | policy/core/live/recovery/lock/multi-repo | **sol** (plan/audit BẮT BUỘC) |

- Audit = gate cho case khó thật, không tự chạy cho task thường (debug sửa xong là DONE).
- Khó vừa gọi terra, khó quá mới sol — không đốt sol cho việc terra xử lý được.
- Rescuer/auditor (v4-pro/terra/sol) READ-ONLY — chỉ plan/hướng fix/verdict, worker patch.
- Fallback model (hết quota) = cơ chế **tool layer** (Hermes `fallback_providers`, 9router) — KHÔNG ghi vào policy AGENTS.md; policy chỉ: worker nào làm task nào, spawn fail → `SUBAGENT_RUNTIME_UNAVAILABLE`.

## Model Fallback Khi Claude Review Hết Quota

Khi `claude -p` không review được do quota/session limit, rate limit, billing hoặc provider unavailable, **không chờ reset và không bỏ review gate**.

**Claude audit timeout ≥10 phút (600s):** Full Claude audit có thể chạy vài phút. Luôn set `timeout_ms=600000` (hoặc wait ≥600s) trước khi kết luận Claude fail. **Timeout ngắn của wrapper KHÔNG phải bằng chứng quota/auth/Claude fail** — phải phân loại lỗi thật trước khi fallback (theo `D:\Taadaa\AGENTS.md`).

Quota gate (theo `D:\Taadaa\AGENTS.md`): trước mỗi call Claude chạy `D:\Taadaa\tools\claude-quota-preflight.ps1 <ledger>` — exit 0 = allow; 20 = 5h ≥85% block; **22 = weekly ≥90% block (dừng hẳn Claude, không dùng nữa)**; 21 = unavailable block. Weekly 90% là dừng cứng, không chờ reset 5h.

Fallback chỉ thay vai trò **reviewer/auditor**, không thay Codex implementer.

Thứ tự model fallback:
1. `freemodel/claude-opus-4-8` (`opencode run --agent plan --auto --variant max`)
2. `opencode-go/grok-4.5` (FreeModel thường hết nhanh)
3. `opencode-go/glm-5.2`

Smoke-test trước lần dùng đầu: `opencode run --model <m> 'Respond with exactly: OPENCODE_FALLBACK_READY'`.

Prompt phải giữ scope read-only, verdict `APPROVED | MINOR_FIXES | REJECT` ở dòng đầu.

Nếu shell vỡ quote (dấu nháy đơn), viết prompt ra `.txt` rồi `PROMPT=$(cat file.txt); opencode run --agent plan --auto --model <m> --variant max "${PROMPT}"`.

`APPROVED` từ fallback reviewer thay thế gate Claude cho run hiện tại. Lần sau ưu tiên Claude nếu quota đã hồi phục.

### Codex Reviewer Fallback Cuối

Chi tiết lệnh, schema, Windows sandbox và verification gate: `references/codex-independent-reviewer.md`.

### Codex Implementer Model Escalation (Sol high → extra high → ultra)

Khi dispatch Codex **implementer** và model mặc định fail/treo/không ghi file:

1. Thử trước: model mặc định route được (hiện `gpt-5.6-sol`) + `-c model_reasoning_effort="high"`.
2. Nếu vẫn fail (treo, không ghi file, lỗi liên tục): escalate **extra high**: `-c model_reasoning_effort="extra_high"`.
3. Nếu vẫn fail: escalate **ultra**: `-c model_reasoning_effort="ultra"`.
4. **Mỗi nấc là một phiên Codex MỚI hoàn toàn** (không resume/reuse session fail, không `--continue` session cũ). Chỉ dừng khi hết nấc hoặc xong.
5. **Tăng effort KHÔNG được lặp y hệt prompt/cách làm cũ.** Theo `D:\Taadaa\AGENTS.md`: mỗi handoff phải kèm "what was tried, why it failed, and a materially different next hypothesis/patch/plan". Trước mỗi nấc: phân tích vì sao nấc trước fail (treo ở đâu, file nào chưa ghi, test nào fail) → thay đổi prompt (bớt/dẻo hóa phạm vi, chỉ rõ file/dòng, đưa evidence, đổi hướng implement) hoặc thay cách tiếp cận. Không gửi cùng prompt với model mạnh hơn.
6. Smoke-test trước mỗi nấc: `codex exec -m gpt-5.6-sol -c model_reasoning_effort="<effort>" "Respond with exactly: READY"`.
7. Sol/ultra chỉ dùng khi có independent shards (theo Automatic Ultra Gate trong `D:\Taadaa\AGENTS.md`), không mặc định cho task khó.
8. Codex thường treo ở CUỐI sau khi đã ghi xong code/test (output đứng yên, process còn sống) — trước khi kill, kiểm tra file/test thật; đừng kill vội khi code đã ghi.

### Fallback OpenCode Free Khi Codex + Claude Đều Fail

Theo `D:\Taadaa\AGENTS.md` (audit order Claude → OpenCode → Codex fallback; wrapper `taadaa-review` + `invoke-opencode-audit.ps1`):

- Khi Codex implementer + Claude review đều fail/treo/hết quota → dùng combo **`opencode-audit`** của 9Router làm audit/review (read-only): `oc/nemotron-3-ultra-free → oc/big-pickle → oc/longcat-2.0-free → oc/ling-3.0-tiny-free` (KHÔNG deepseek — tránh trùng worker, xem OpenCode Free Audit Layer).
- Chỉ thay vai trò **audit/review**, không thay implementer.
- Invocation: `opencode run --agent plan --auto --model <free-model> '<prompt>'` (hoặc wrapper `D:\Taadaa\tools\...invoke-opencode-audit.ps1` khi có), read-only, verdict `APPROVED | MINOR_FIXES | REJECT` dòng đầu.
- Smoke-test trước: `opencode run --model <free-model> 'Respond with exactly: OPENCODE_FALLBACK_READY'`.
- Kết quả label `OPENCODE_AUDIT`; không bao giờ gọi là Claude approval.
- Nếu OpenCode cũng unavailable → `OPENCODE_RUNTIME_UNAVAILABLE` → Codex reviewer độc lập fallback cuối (`CODEX_FALLBACK_AUDIT`).

Nếu Claude và toàn bộ OpenCode reviewer đều hết quota, thiếu balance, timeout hoặc unavailable:
- Chạy **Codex phiên mới độc lập**, không resume/reuse session implementer.
- Dùng `codex exec --ephemeral --sandbox read-only -c model_reasoning_effort="high"` với model mặc định đã route được tới Sol (hiện là `gpt-5.6-sol`) và prompt review toàn bộ diff. Không ép `-m sol` nếu alias đó route sang provider thiếu credential. Verdict `APPROVED | MINOR_FIXES | REJECT`.
- Nên dùng `--output-schema` để ép verdict có cấu trúc và `--output-last-message` để lưu artifact review.
- Không dùng subagent do chính implementer spawn làm approval gate chính; shared context/assumptions làm giảm độc lập review.
- Nếu reviewer trả finding, dispatch một phiên Codex implementer mới để sửa; sau đó dùng một phiên Codex reviewer mới review lại đến `APPROVED`.

## Validate `DONE` Trước Khi Gọi Thành Công

Report wrapper/CLI `DONE` chỉ nghĩa report đã được ghi — không đồng nghĩa target `SUCCESS`. Phải đọc summary outcome per-target (JSON/XLSX) trước khi báo thành công. Ví dụ: wrapper in `DONE: result=...xlsx`, nhưng summary bên trong ghi máy `locked`.

Khi user hỏi ngắn như `xong chưa`:
- Trả lời ngay câu đầu `Xong` hoặc `Chưa`, không mở đầu bằng diễn giải.
- Nếu chưa, chỉ nêu gate còn thiếu và hành động đang chạy; không lặp lại toàn bộ lịch sử.
- Chỉ gọi `Xong` khi test/proof và reviewer gate đều hoàn tất. Nếu code/test pass nhưng reviewer chưa `APPROVED`, trạng thái vẫn là `Chưa`.

## Tiếp Quản Phiên Bị Đứt Context/API

1. Tìm đúng session cũ và đọc cửa sổ cuối cùng, gồm tool output; không dựa riêng vào ảnh chụp hoặc lời tóm tắt.
2. Lập checkpoint gồm: target, action live cuối, process/reviewer đang chờ, diff hiện tại, test đã chạy và completion gate còn thiếu.
3. Process nền thuộc session cũ có thể không còn trong process registry của session mới. Không giả định nó vẫn chạy; xác minh bằng output session cũ và trạng thái thực tế hiện tại.
4. Với trạng thái live có thể đã đổi (VPN/device/lock/process tree), probe lại trực tiếp trước khi retry. Không lặp action live nếu proof hiện tại đã đạt.
5. Tiếp tục đúng target/gate còn dở; không chạy lại toàn batch hoặc phần đã có proof.
6. Mọi báo cáo từ coding agent phải được Hermes kiểm chứng bằng test/diff/proof thật trước review gate.

Chi tiết và checklist: `references/interrupted-session-takeover.md`.

## Reviewer Quota/Treo

- Reviewer process in thông báo quota/session limit nhưng không exit phải được coi là provider-unavailable, không phải review đang tiến triển.
- Poll output sau khoảng chờ hợp lý; nếu thấy quota/rate-limit/billing/session-limit, kill process treo và fallback ngay theo chuỗi model đã định.
- Không báo `APPROVED`, không gọi task `DONE`, và không để user chờ reset quota.
- Smoke-test fallback trước, sau đó review toàn bộ diff thực tế. Nếu fallback cũng lỗi, chuyển model kế tiếp thay vì lặp cùng command.

### Heuristic: output đứng yên = process treo (không phải đang suy nghĩ)

`codex exec`/`claude -p` chạy background qua Hermes hay treo ở TAIL sau khi việc chính đã xong:
- Dấu hiệu: cùng một đoạn output (diff/test snippet) lặp lại y hệt qua 2-3 lần poll (≥ 180s), `tokens used` đứng nguyên, không có python child đang chạy.
- Hành động: **kill process, đừng đợi nữa**. Verify bằng artifact thật: `git status --short`, `git diff --stat`, file mtime, chạy test trực tiếp bằng tay. Codex exec thường đã GHI được file trước khi treo — output lặp ≠ chưa làm gì.
- Ngoại lệ: `node_repl/js`/`mcp:` xuất hiện liên tục nghĩa là reviewer đang chạy công cụ — còn chạy thật, cho thêm 1-2 poll.
- Kiểm tra `tasklist | grep -iE 'codex|claude'` để phân biệt process treo vs đã exit; `wmic process where "ProcessId=N" get CommandLine` xác định đó là exec task nào.

### Verdict nằm ở ĐẦU buffer log, không phải tail

Reviewer (Claude/OpenCode/Codex) in verdict `APPROVED/MINOR_FIXES/REJECT` ở
**dòng đầu**, rồi liệt kê findings phía sau, rồi TREO. `wait`/`log` (tail) chỉ
hiện findings → tưởng "chưa có verdict" trong khi verdict đã có ở đầu.

- Khi output đứng yên: `process(action="log", limit=40, offset=0)` để đọc ĐẦU
  buffer — verdict nằm đó. Đọc xong mới kill.
- OpenCode free có thể không in verdict dòng đầu
  theo đúng format (viết "Không còn MAJOR/MINOR chặn. Chỉ còn NIT..." =
  APPROVED tương đương) — suy luận từ nội dung findings, không cần chữ
  APPROVED đúng nghĩa.
- Nếu chỉ có NIT → coi là APPROVED (NIT không bắt buộc fix trước merge); có
  MINOR → dispatch Codex sửa rồi review lại; có MAJOR → REJECT.

### Baseline trap khi dispatch reviewer: implementation nằm trong commit, diff HEAD trống

Khi Codex implementer vừa COMMIT xong rồi mới dispatch reviewer độc lập, `git diff HEAD` chỉ còn thay đổi chưa commit (vd chỉ version bump) → reviewer tưởng "implementation chưa có" → REJECT oan.

- Luôn nói rõ baseline trong prompt reviewer: "xem CẢ HAI: `git diff HEAD -- <files>` (working tree) VÀ `git show <commit> --stat` (commit gốc implementation)".
- Nếu reviewer REJECT vì "diff không chứa implementation", kiểm tra `git log --oneline -3` trước — khả năng cao implementation đã commit, chỉ là baseline trap.
- Finding từ review lần đầu vẫn có giá trị (MAJOR/MINOR/NIT thật) — tách riêng phần baseline hiểu lầm với phần finding thật, fix finding rồi review lại.
- `codex exec --sandbox read-only` không chạy được pytest (không tạo được temp/cache) — reviewer báo "test không chạy được do môi trường" là hạn chế sandbox, không phải test fail; tự chạy test bằng tay với PYTHONPATH trỏ `src`.

## Watcher Validation Checklist

### Lock proxy readiness chặn START_VPN

Lock acquisition đòi `wait_for_proxy_ready` tạo vòng lặp `VPN-off → lock denied → START_VPN never runs`. Fix: per-event proxy-recovery lock dùng `bypass_proxy_readiness=True`, vẫn giữ central machine/serial exclusivity.

### Worker không treo khi lock retained/dead owner

- Dead PID retained lock: takeover theo central policy. Core re-validates atomically.
- Live owner: bounded timeout (10s) → `SKIPPED_DEVICE_LOCKED` → worker tiếp tục poll.

### Worker không chết im lặng

Exception từ `watch_device_reconnect`/`wait_until_unlocked`: bắt per-iteration, telemetry sanitized (machine+serial+status+error ≤300 chars), bounded backoff, re-enter monitoring. Mapping serial đổi → restart worker.

### Telemetry phân biệt nguyên nhân

Lock timeout, readiness failure, mapping reload/mismatch, proxy-set failure, telemetry-write failure — mỗi loại dùng status riêng, không tái sử dụng.

### Verify process tree thật

Task `Enabled` không đủ chứng minh watcher đang chạy. Phải verify scheduler/tray parent, launcher child và worker command cùng sống.

## Pitfalls đã học

- **Audit policy file THẬT phải gồm cả các file con (2026-08-06):** sau khi sửa AGENTS.md v8 (parent), audit bằng nemotron-3-ultra-free đọc TOÀN cây → bắt thêm **3 file con** (automation-core, consumer repos) vẫn giữ "Luna-only worker" trái parent equivalence. Lesson: khi sửa policy parent, **các file con kế thừa có thể giữ policy cũ** — phải grep toàn bộ cây (`rg "Luna/high" --glob 'AGENTS.md'`) + audit bằng model đọc toàn file (OpenCode) trước khi coi là xong. ds-pro/Gemini chỉ xem vùng trích → không bắt được cross-file.
- **Wrapper PowerShell tool có thể hỏng ngoài scope audit (2026-08-06):** `invoke-gemini-9router-audit.ps1` fail vì `[SHA256]::HashData` không tồn tại trên PowerShell cũ + 400 Invalid JSON với body 100KB. Không tự sửa wrapper tool (đã audit, đang dùng) — workaround: gọi API trực tiếp qua curl/urllib, model + reasoning_effort giữ nguyên.
- **Model free của OpenCode thay đổi theo thời gian — smoke-test trước khi tin (2026-08-06):** mimo trả template verdict giả, laguna không output, nemotron 502 khi concurrent — chỉ ling/longcat/north cho verdict thật. Trước khi thêm model vào cascade: `opencode run --dir <repo> --agent taadaa-review --format json --model <m> "Reply VERDICT: APPROVE"` — đọc output thật, đừng tin tên model.

- **Line-ending CRLF/LF của policy file phải GIỮ NGUYÊN khi sửa (2026-08-06):** patch tool / write_file trên Windows hay convert line-ending toàn file (LF→CRLF hoặc ngược) — 1 patch nhỏ có thể đổi 35+ dòng, làm byte-diff lệch backup (vi phạm release gate; Sol v6 từng cảnh báo "byte-diff có BOM/line-ending"). Đã gặp khi sửa 4 file AGENTS.md (parent + 3 con): patch tool LF-hoá/CRLF-hoá 3 file, phải khôi phục từ backup. **Quy trình đúng khi sửa policy file có line-ending hỗn hợp:** (1) backup từng file + sha256; (2) sửa bằng python đọc `open(path,'rb')` → decode → `text.replace(old, new)` — nếu file dùng CRLF, thử variant `old.replace("\n","\r\n")` trước; pattern bị ngắt giữa dòng (`pinned\n  Luna/high`) thì dùng `re.search(r'pinned\s*\n\s*Luna/high worker')`; (3) ghi lại bằng `open(path,'wb').write(text.encode('utf-8'))` — KHÔNG qua patch tool/write_file, KHÔNG dùng `open(...,'w',newline='')` (sẽ LF-hoá); (4) verify: đếm CRLF vs backup (`cur.count(b'\r\n') == bak.count(b'\r\n')`), đếm content-diff line vs backup (phải = số thay đổi chủ đích, không phải 35+), grep remnant sau khi loại cụm hợp lệ (`re.sub(r'\([^)]*Luna/high or flash/max[^)]*\)','',t)` rồi mới tìm term thật — đừng đếm cả cụm hợp lệ làm remnant). Bẫy `\r\r\n` (double CR) xuất hiện sau nhiều lần ghi lẫn lộn — grep `\r\r\n` và replace về `\r\n`. Chạy validator (`check-claude-quota-policy.ps1` exit 0) sau khi sync xong.
- **Policy file 2 section cùng chủ đề → audit REJECT mãi (2026-08-06):** AGENTS.md Taadaa có 2 section cùng nói worker model (Delegation L70-215 + Model Routing L710-770). Mọi bản sửa 2 section đều vô tình DUPLICATE với section còn lại → Sol bắt "lặp contract" mỗi vòng → REJECT 5 vòng liên tiếp dù nội dung mỗi bản tốt hơn. Bài học: trước khi sửa policy file, **inventory toàn file** tìm mọi chỗ nói cùng chủ đề; nếu có ≥2 section cùng chủ đề thì phải sửa ĐỒNG THỜI hoặc thiết kế 1 canonical + các section khác chỉ tham chiếu. Nếu REJECT lặp vì cùng lý do cấu trúc 2 vòng → dừng, đổi cách tiếp cận (đừng sửa mãi trong cùng 2 section).
- **Skill 2 nơi dễ lệch — sửa xong phải sync cả 2 (2026-08-03):** skill này tồn tại ở profile-local (`C:\Users\Kibe\AppData\Local\hermes\skills\`) VÀ git repo `D:\Taadaa\Hermes\skills\` (nguồn chính thức, push lên `thanhdatbui/hermes-agent.git`). Sửa skill ở local KHÔNG tự động vào git — phải chủ động copy + commit + push. Đã gặp: local có thêm pitfall nhưng git repo vẫn bản cũ/thiếu. Kiểm tra lệch: `diff <local SKILL.md> <git SKILL.md>` + `git status --short skills/`. Workflow chuẩn: sửa local → copy sang git → commit → push → `/reset`.
- **ModuleNotFoundError dù module có trong src** (2026-08-03): env python cài `automation-core` bị **dist-info dở dang** (version 0.4.22 dist-info nhưng site-packages thiếu file `usb_popup.py` — wheel 0.4.22 chưa tồn tại). Import fail `No module named 'automation_core.usb_popup'`. Fix: kiểm tra `pip show automation-core` version vs `ls site-packages/automation_core/` (file thiếu), rồi `pip install --force-reinstall <đúng wheel>` theo pin consumer. Chạy test với `PYTHONPATH=<repo>/src` để dùng bản src thay vì site-packages cũ. Nghi ngờ env nhiễm/lệch: dùng `env -i PATH=... HOME=... USERPROFILE=...` để cô lập sys.path khỏi hermes venv.
- **Đừng giả định format output CLI** (2026-08-03): viết regex parse output của `claude /usage`, `adb`, `dumpsys`... trước tiên PHẢI chạy lệnh thật lấy sample, đừng tự bịa format. Regex `Weekly usage:` sai vì output thật là `Current week (all models):` — mock test pass nhưng end-to-end ra null. Quy tắc: chạy lệnh thật → nhìn raw output → viết regex → test trên sample thật.
- **Android UI selector debugging**: `find_by_fields` dùng exact match; `resource_id=""` không match.
- **`dumpsys window policy` false-positive**: match chỉ `mShowingLockscreen=true`/`isStatusBarKeyguard=true`.
- Không coi `pytest` pass là production-ready nếu chưa đọc workbook/config thật.
- **Soft reboot recovery**: 3× fail → `adb reboot` + 120s wait + 60s boot + wake + swipe.
- **Worker conflict Codex**: dùng `write_file` hoặc dispatch single leaf + kill worker cũ.
- **Lock takeover chỉ khi eligibility khớp chính xác central gate**.
