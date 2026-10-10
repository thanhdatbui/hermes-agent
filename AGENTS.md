<!-- WORKER-ROLE-GATE:START -->
## Built-in/direct worker role gate (highest precedence)

When the current built-in/direct session was created with `agent_type=worker`, it is the final worker/executor for its assigned scope. Its binding is:

- `role=worker`, `can_delegate=false`, `executor_scope=current_assigned_scope`, `execution_tools=shell/apply_patch`.
- Ignore every passage that applies only to a coordinator. Do not spawn, delegate, probe a tool/worker registry, or turn into a coordinator.
- If shell/tools are available, continue executing the current assigned scope. If the real execution tool remains unavailable after binding, use `WORKER_RUNTIME_NOT_VERIFIED`.
- `SUBAGENT_RUNTIME_UNAVAILABLE` is reserved for a coordinator before a child exists; a worker must never use or assign that label.
- This role-gate has precedence over all later coordinator-only text in this file.

<!-- WORKER-ROLE-GATE:END -->

<!-- SESSION-START-CONTEXT:START -->
## Session-start context (bắt buộc mỗi session mới — CHỐNG PHÌNH CONTEXT)
- Khi session mới bắt đầu (vừa `/new`, resume, hoặc đổi máy): trước khi hỏi user hoặc tự làm gì, chạy đúng 4 bước có chọn lọc:
  1. Đọc file `AGENTS.md` này. Nếu có `HANDOFF.md`, CHỈ đọc phần `Current State / Blockers / Next Task` (nếu file >20KB thì không nạp toàn bộ lịch sử).
  2. Tìm trong `.hermes/plans/` (nếu có): CHỈ đọc **đúng 1 file `.md` mới nhất theo timestamp**. KHÔNG đọc toàn bộ thư mục plans.
  3. Kiểm tra git: `git status --short` + `git log --oneline -5`.
  4. Tổng hợp thành 1 báo cáo ngắn ("Task đang dở / bước kế tiếp / trạng thái git") rồi hỏi xác nhận TRƯỚC khi tiếp tục — CẤM tự đoán task và tự làm tiếp.
- Mục đích: chống phình context (không nạp hàng trăm KB startup), giữ mạch làm việc qua các lần /new và đổi máy.
<!-- SESSION-START-CONTEXT:END -->

# Shared Taadaa Workspace Rules

> **Canonical policy precedence:** `D:\Taadaa\HERMES_SUBAGENT_RULES.md` marker `CANONICAL-POLICY-PRECEDENCE-2026-10-05` is authoritative; khi conflict, marker canonical thắng. This file only points to that policy and does not duplicate it.


## Quy tắc kỷ luật chạy Script & Nhập Password toàn Farm (MANDATORY TOÀN BỘ REPO)
1. **HARD ROUTING ALERT (CẤM NHẦM REPO/RUNNER):** Khi nhận Farm Alert (`🚨 [MÁY N] DỪNG PHIÊN` / `• Script:`), BẮT BUỘC parse trường `Script:` để cd đúng repo và gọi đúng runner sở hữu:
   - `tiktok-follow` ➔ `D:\Taadaa\tiktok-follow` (`follow_runner/run_follow.py`)
   - `multi-machine-feed-session` / `feed` ➔ `D:\Taadaa\tiktok-luot nuoi acc` (`run_tiktok.py`)
   - `social_reg` / `tiktok-reg` ➔ `D:\Taadaa\Tiktok_Reg`
   - `tiktok_upload` ➔ `D:\CodexRuntime\tiktok-video`
   - `tik3_render` ➔ `D:\Taadaa\tik3_render`
   Tuyệt đối CẤM dùng runner của repo nuôi acc (hoặc repo khác) để chạy canary cho script không thuộc quyền sở hữu. CẤM suy diễn runner từ context cũ.
2. **CẤM gõ mật khẩu bằng `adb shell input text` thô:** Shell sẽ nuốt/thoát các ký tự đặc biệt (`@`, `!`, `&`, `#`, `$`, `%`...) làm sai lệch mật khẩu dẫn tới lỗi "Sai mật khẩu" giả tạo (sự cố m76).
3. **BẮT BUỘC dùng cơ chế nhập chuẩn:** Mọi thao tác điền mật khẩu/chuỗi nhạy cảm phải qua `AdbKeyboard` base64 hoặc helper chuẩn của repo có escape ký tự (`_input_password`).
4. **TUÂN THỦ SCRIPT CỦA REPO — CẤM TỰ Ý GÕ TẮT BẰNG TERMINAL:** Khi user ra lệnh chạy batch/task, phải thực thi bằng script/runner của repo. Gặp màn hình mới hoặc blocker KHÔNG được tự ý gõ lệnh terminal shell thô can thiệp vào máy.
5. **XỬ LÝ ALERT [MÁY N] & CẤM QUÉT ĐỆ QUY Ổ ĐĨA:** Khi nhận Farm Alert (`🚨 [MÁY N]`), lệnh trích xuất hiện trường DUY NHẤT được phép chạy là `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc lệnh ADB Read-Only theo serial máy (`dumpsys`, `screencap`, `uiautomator dump`). CẤM TUYỆT ĐỐI `adb shell input tap/swipe` bấm tay qua màn hình lỗi thay cho sửa code. CẤM TUYỆT ĐỐI tự viết script Python có `os.walk`, `glob(recursive=True)`, `find`, `grep -r`, `search_files` quét diện rộng trên toàn bộ ổ đĩa `D:\` hoặc `.ai-runs` gây treo timeout 900s.
6. **PHÂN VAI & THANG ĐIỀU PHỐI THỰC CHIẾN (COORDINATOR vs GEMINI WORKER):**
   - **Case sửa code ít (T1 hiện trường):** Đúng 1 file, $\le 15$ dòng diff, không đổi signature, có focused test < 30s $\to$ Coordinator Gemini **TỰ SỬA TRỰC TIẾP O(1)** để thông đường nhanh cho farm, không bắt ép spawn subagent rườm rà.
   - **Case khó / Kiến trúc (T2):** Sửa $\ge 2$ files, thay đổi logic $> 15$ dòng, đụng chạm watchdog/lock/database schema $\to$ **BẮT BUỘC spawn subagent Gemini (`ag-gemini-pool-3`)** qua `delegate_task` để giữ sạch context Coordinator. Subagent chạy thần tốc 1-3s/turn, timeout 180s, hard budget $\le 15$ calls (call 16 tự động bị chặn).
   - **Hàng rào chốt chặn đầu ra (Outcome Verification Gates):**
     1. **Canary máy thật (Tử huyệt):** Chạy trên $\ge 1$ máy thật rảnh, bắt buộc có ảnh `MEDIA:<path>` kết quả + WinRT OCR gửi User duyệt.
     2. **Closeout Gate $\ge 85$:** Sol Reviewer chấm $\ge 85/100$ qua `closeout_gate.py` mới được phép push git remote khi User ra lệnh.
     3. **Bảo vệ hệ thống:** Cấm đụng `tools/hooks/**`, `farm_policy.py`, `closeout_gate.py`, credentials, `.env`.
   - `clarify` chỉ dùng cho quyết định nghiệp vụ, thiếu quyền, hoặc thao tác không đảo ngược/tốn phí tiền thật. Cấm dùng để xin phép L0-L2 hoặc trốn timeout. Clarify phải có evidence, 2-3 phương án, đề xuất của agent và mặc định an toàn; xóa/tốn phí mặc định là KHÔNG làm.
   - Nếu Gate fail: thu hẹp contract, hoặc L2 nếu đủ điều kiện kích hoạt; không đủ điều kiện thì BLOCKED kèm evidence; không đóng băng task. DỪNG UI sau 3 lỗi chỉ nghĩa là dừng vòng UI của nick/máy đó, chuyển BLOCKED, không đóng băng toàn phiên.
7. **COMPLETION PROTOCOL & CANARY GATE (CHỈ ÁP DỤNG KHI FIX CODE AUTOMATION):**
   - CHỈ áp dụng bắt buộc khi sửa code AUTOMATION (các script/flow điều khiển thiết bị phone farm Android). Tuyệt đối KHÔNG áp dụng cho docs, cấu hình, tool thuần, backend web, data sync.
   - Định nghĩa DONE cho fix code automation: Task CHỈ ĐƯỢC coi là hoàn thành khi thỏa mãn 4 Gates:
     1. Unit test / Linter pass.
     2. Git commit SHA được ghi nhận.
     3. **CANARY VERIFIED:** Chạy `python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path_anh_hoac_log>` đạt Exit Code 0 (bắt buộc chạy trên $\ge 1$ máy thật nếu farm có máy rảnh).
     4. Đính kèm bằng chứng OCR / `MEDIA:<path_anh>` theo chuẩn Gate 6.
   - Thiếu Canary khi máy rảnh ➔ Task luôn là `IN PROGRESS`, tuyệt đối cấm báo DONE/hoàn thành.
8. **ANTI-CONFABULATION & TRUTH-TELLING PROTOCOL (CẤM LẤP LIẾM & BÀO CHỮA):**
   - CẤM TUYỆT ĐỐI phản xạ bao biện, thanh minh ("em tưởng", "thừa 1 nhịp hỏi", "lần sau sẽ cẩn thận", "khắc cốt ghi tâm").
   - Khi bị người dùng bắt bẻ hoặc phát hiện thiếu sót/lỗi, format phản hồi DUY NHẤT được chấp nhận:
     ```text
     [FAULT-CONFIRMED]: <Tên lỗi cụ thể>
     - Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
     - Root Cause: <Nguyên nhân kỹ thuật thực tế>
     - Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
     - Verification: <Lệnh chạy kiểm chứng thực tế>
     ```
9. **INVARIANT: CHATGPT-WEB-POOL ADVISOR ("Sol-Web") IS NOT gpt-5.6-sol**
   - "Sol" trong context plan-review (combo `plan-review-hard`, 9Router port 20128, model `gpt-5.6-sol`) và "Advisor Sol" trong context ChatGPT-Web pool (OmniRoute port 20129, model `gpt-web-sol` 115 accounts) là HAI BACKEND KHÁC NHAU HOÀN TOÀN.
   - Mọi lời gọi tới Advisor Sol ChatGPT-Web Pool BẮT BUỘC đi qua script duy nhất: `python D:/Taadaa/tools/consult_advisor.py <prompt>`. CẤM gọi HTTP trần hoặc tự đoán model ID.
   - KHI `consult_advisor.py` trả lỗi / `ADVISOR_UNAVAILABLE`: Coordinator CHỈ ĐƯỢC báo trạng thái `ADVISOR_UNAVAILABLE` nguyên văn kèm reason/detail. CẤM TUYỆT ĐỐI fallback sang bất kỳ model/provider khác (bao gồm Gemini, Luna, Terra...) để thay thế ý kiến của Sol.
   - CẤM TUYỆT ĐỐI mạo danh output của bất kỳ model nào khác là "Sol" / "Advisor Sol" dưới mọi hình thức.
## 📘 QUY TẮC BẮT BUỘC ĐỐI CHIẾU & CẬP NHẬT DOCS/FARM-AUTOMATION-CASES.MD (ALL FARM REPOS)
1. **TRƯỚC KHI HANDLE SCRIPT / SỬA CODE FARM:** BẮT BUỘC đọc và đối chiếu toàn bộ các Case Fix thực tế & Anti-Pattern trong `docs/farm-automation-cases.md`, bao gồm: UI/Popup, Cron/Reaper/Watchdog, Sync/Workbook/Data integrity, Device Lock/ADB. Tuyệt đối không tái phạm các lỗi đã được xử lý trong file này.
2. **KHI CHỐT PHIÊN (NẾU TASK LIÊN QUAN TỚI FARM AUTOMATION):** Trước khi Model Review và Commit, BẮT BUỘC phải cập nhật Case Fix thực tế và Anti-Pattern tương ứng vừa xử lý vào file `docs/farm-automation-cases.md` sang các repo liên quan. Khóa chặt chống hồi quy bằng Focused Regression Test trong test suite.
## Task Contract and Scope Lock (MANDATORY)

This gate applies to every task, repository, worktree, skill, worker, and tool
sequence under `D:\Taadaa`.

- **Latest request wins.** The latest explicit user request is the only active
  task authority. A previous plan, summary, TODO, handoff, worker report,
  session context, or stale acceptance list is background only; it must not
  revive or widen the task without current user approval.
- **Contract before action.** Before the first state-changing action, record a
  compact task contract: `Goal`, exact `In-scope allowlist`, `Non-goals /
  forbidden scope`, `Acceptance criteria`, and `Stop condition`. If the user
  request is already clear, do not ask them to restate it; derive the contract
  narrowly from that request.
- **Scope checkpoint.** Before touching a new file, route, repository,
  worktree, device, account, worker, delegate, broad test suite, or live
  surface, ask: “Is this directly required by the current Goal and inside the
  allowlist?” If not, classify it `OUT_OF_SCOPE`, do not inspect/edit/run/
  delegate it, and report or ask for explicit expansion.
- **No implicit permission from a plan.** A plan is an implementation aid, not
  authorization to execute every phase. Adopt only the phases and files that
  the latest request explicitly covers; ignore stale plan sections.
- **Focused verification first.** Run only acceptance tests needed for the
  current scope. Do not expand to full-suite, adjacent-route, regression, or
  cleanup work unless the contract requires it or the user approves it.
- **Worker binding.** Every delegated worker receives the same contract,
  allowlist, non-goals, acceptance criteria, and stop condition. A worker that
  discovers scope drift must stop and hand off; it must not widen the scope.
- **Stop when done.** Once acceptance criteria pass, stop. Unrelated failures,
  adjacent improvements, and newly discovered routes are not follow-up work by
  default.

### Taadaa Scope Override

- A narrow coordinator fallback for deterministic local repository maintenance
  (local Git worktrees, local branches/refs, and untracked or generated
  artifacts under `D:\Taadaa`) is allowed only after the user gives explicit
  authorization. This legacy maintenance exception does not by itself
  authorize other cleanup, write, implementation, build, deployment, or live
  operation. The separately named Coordinator Direct Fallback below is the
  only additional user-authorized exception for an exact offline repository
  file scope after both worker routes fail, and it has its own preimage, lease,
  reconciliation, and verifier gates.
- The authorization and preflight must name an exact allowlist of repository,
  worktree, branch/ref, artifact, and operation targets. Before any action, the
  coordinator must verify that every target is contained under `D:\Taadaa`,
  record the allowlist, capture the relevant status/diff/hash evidence, and
  create the lease/checkpoint artifacts for that scope.
- This exception is available only after the policy-compliant worker wait,
  shutdown, and lease reconciliation requirements have completed, worker
  runtime unavailability is confirmed for this exact maintenance scope, and
  `SUBAGENT_RUNTIME_UNAVAILABLE` is recorded with the evidence handoff. An
  eligible external Codex CLI worker is governed by the separate transport
  contract below; it is not this coordinator-maintenance fallback and never
  makes the coordinator the patch/live executor. A short wait timeout, empty
  status, or missing worker message alone never authorizes either route.
- The coordinator must use quarantine or another recoverable move for exact
  worktree/artifact targets and guarded deletion for exact local Git
  branches/refs. It must never use `git reset --hard`, `git checkout --`,
  `git clean -fdx`, `git worktree remove --force`, or force push.
- This maintenance exception never permits changes to remote refs, tracked
  source/code implementation, devices, accounts, the recovery state machine,
  runtime services, scheduler/watcher live actions, mailboxes, or workbooks.
  Every other write or live task remains subject to the fresh pinned session-model
  worker-only rule; the only coordinator write exception is the separately
  authorized, exact offline repository-file scope in Coordinator Direct
  Fallback, which never grants live or production authority.
- The existing lease/heartbeat requirements, five-minute checkpoint-request
  threshold, ten-minute same-no-signal takeover threshold, and 30-minute operational
  ceiling, along with `close_agent` shutdown semantics, are unchanged.
- A post-verifier must prove the exact allowlist was the only target, no remote
  ref changed, and no unintended tracked file changed. The coordinator must
  record the marker `COORDINATOR_LOCAL_MAINTENANCE_FALLBACK` together with the
  preflight, action, quarantine/ref, verifier, and handoff evidence.

## Delegation Policy

<!-- CODEX-DIRECT-WORKER-POLICY:START -->
## Coordinator -> direct worker boundary (canonical)

- The desktop/main session is coordinator/report surface only: it may perform read-only triage/research, dispatch and bind the worker, route handoffs, inspect artifacts/diffs, run deterministic read-only verification, and report. The coordinator does not execute the assigned side effect itself.
- For every write, edit, build, package, deployment, or other side effect, the coordinator must dispatch exactly one fresh, non-resumed, non-forked in-process direct worker pinned to the session's own model (`deepseek-v4-flash` for Hermes, `gpt-5.6-luna` for Codex), `reasoning_effort=high`, and `role=worker`, with an exclusive exact file/component/worktree scope. `gpt-5.6-luna/high` and `deepseek-v4-flash/high` are equivalent worker roles.
- Once the worker exists and its profile is verified, that bound worker is the final executor for the exact scope and uses its available shell/tools directly to patch, build, test, or perform authorized live work within that scope. It must not inherit, spawn, create, resume, fork, or delegate to another worker/agent/session, and must not turn itself into a coordinator.
- A bound worker must not probe a tool registry or other runtime surface to find, request, or create a worker executor. If the tool surface exposes delegation capability, fail closed with `NESTED_DELEGATION_FORBIDDEN` and do not call it.
- `SUBAGENT_RUNTIME_UNAVAILABLE` is reserved exclusively for the coordinator before a child worker exists, with the required machine-readable pre-create evidence and exact-scope reconciliation. A bound worker must never self-report or assign that label. If a required worker tool is unavailable, use `WORKER_RUNTIME_NOT_VERIFIED`; if shell/tools needed for the assigned action remain available, continue executing the exact scope and record the limitation.
- Terra/high, Terra/xhigh, Sol/high, and Sol/max are read-only planners/advisors/auditors; they never patch, build, or run live/side-effecting work.
- An external CLI transport is not the normal route. The coordinator may use it only as the separately gated fallback in the parent `D:\Taadaa\AGENTS.md`, after authenticated pre-create in-process `transport-unavailable`, machine-readable `capability-unavailable`, or in-process dispatch `429`, plus proof that no worker/session/process/lease/action exists for the exact scope. The same model/profile, reservation, binding, checkpoint, reconciliation, and post-verifier gates still apply.
- Failure labels are lifecycle-hard: `SUBAGENT_RUNTIME_UNAVAILABLE` is reserved exclusively for a pre-create transport failure, and only with machine-readable evidence plus exact-scope reconciliation proving that no child/worker, session, process, lease, tool event, or action exists. A worker that exists or is bound must never self-report or assign this code.
- Use `WORKER_PROFILE_MISMATCH` for a created worker with the wrong pin and `WORKER_RUNTIME_NOT_VERIFIED` when provider/profile binding cannot be verified. Use `WAIT_WINDOW_EXPIRED` when a bounded wait has no final while the worker remains active. A timeout never changes a label or becomes `SUBAGENT_RUNTIME_UNAVAILABLE`.
- A replacement may be initiated only by the coordinator after the current worker has shut down and exact-scope lease/process/tool-event/action reconciliation proves no overlap; replacements never run in parallel, and a worker must not self-replace or initiate replacement.
- If no valid direct worker exists, stop all write/live/side-effecting work. Coordinator direct fallback is allowed only when the current user request explicitly authorizes it, both worker routes have failed and been reconciled, and the parent contract permits exact-scope offline repository files; it never authorizes live work.
- Worker self-report, process status, scheduler status, or exit code is not completion proof; the coordinator must independently inspect the exact diff and run the deterministic verifier. A bound worker must not stop merely because it lacks a tool for creating a child worker.
<!-- CODEX-DIRECT-WORKER-POLICY:END -->

- Use a fresh **session-model sub-agent** (Hermes = `deepseek-v4-flash`, Codex = `gpt-5.6-luna`; equivalent roles) for every task that writes or edits any
  file, changes code, configuration, package, build, or deployment, or performs
  any other side effect. The normal transport is an in-process Sub Agent/MCP
  dispatch; the separately gated external CLI contract below may substitute
  only that transport after its eligibility proof. The worker dispatch must
  pin exactly model `gpt-5.6-luna` with `reasoning_effort=high` and
  `role=worker`. The required topology is exactly `coordinator -> direct
  worker`: once that fresh worker is successfully created and bound to the
   assigned exact scope, it is the sole final executor for that scope and may
   patch, build, and test directly. It must not inherit, spawn, resume, fork,
   or delegate to another agent, worker, or session; it does not need a child
   worker. If its tool surface exposes a delegation capability, it must fail
   closed with `NESTED_DELEGATION_FORBIDDEN` without calling it. The
  desktop/main session is the **coordinator** and may only perform read-only
  triage/research, artifact/diff inspection, deterministic read-only
  verification, coordination, and reporting.
- Good delegation targets include implementation, read-only exploration,
  research, log or artifact analysis, testing, triage, and independent review.
- The coordinator owns the outcome, plan, routing, and final deterministic
  read-only verification; the delegated worker owns the exclusive
  implementation/side-effect scope and returns inspectable artifacts.
- Large, architecture-sensitive, security-sensitive, or otherwise high-risk
  changes require an independent audit after the plan is final or after the
  important implementation block and local checks are complete.
- During debugging, delegate only after reproducing the failure or identifying
  independent hypotheses to investigate.
- Do not spawn subagents merely to give the same model a different role; a
  worker must own an exclusive execution scope and return inspectable artifacts.
- Write-heavy delegation requires exclusive file, component, or worktree
  ownership; do not let workers edit the same scope concurrently.
- A subagent's completion message or self-report is not proof of success. The
   main agent must inspect the artifacts and run the relevant verifier or tests.
- Terra/Sol are read-only advisors/auditors; they never patch files, change
  code, or run live/side-effecting work.
- Coordinator pre-create worker gate: if an in-process runtime cannot spawn the
  fresh, pinned session-model worker (Hermes = `deepseek-v4-flash`, Codex =
  `gpt-5.6-luna`), classify the failure before acting. An
  authenticated pre-create Sub Agent/MCP transport-unavailable, dispatch-429,
  or machine-readable
  capability-unavailable result may use that same fresh session-model role through
  the gated CLI transport. A capability-unavailable result must identify the
  active runtime/tool registry, timestamp, correlation/request id, and
  failure/payload hash, and prove that no child was created. Provider/model
  quota, authentication, policy denial, an unclassified 429, an ambiguous
  dispatch, or a failed CLI gate that prevents pre-create worker creation is
  not by itself `SUBAGENT_RUNTIME_UNAVAILABLE`; classify it as `INELIGIBLE` or
  `AMBIGUOUS` under the matrix and fail closed. `SUBAGENT_RUNTIME_UNAVAILABLE`
  is permitted only for a pre-create transport failure with machine-readable
  evidence and exact-scope proof that no child/worker, session, process, lease,
  tool event, or action exists. This error is reserved for the coordinator
  before a direct worker session exists; it is not a condition imposed on an
  existing or bound direct worker and never means that the direct worker must
  find, spawn, resume, fork, delegate, or replace another worker/session. If a
  worker session exists but its pinned profile is mismatched, use
  `WORKER_PROFILE_MISMATCH`; if its runtime/provider/profile binding cannot be
  verified, use `WORKER_RUNTIME_NOT_VERIFIED`. Do not relabel either case as
  `SUBAGENT_RUNTIME_UNAVAILABLE` or use an ambiguous generic worker-unavailable
  label.
  Terra/high, Terra, Sol, and auditors are never
  desktop/coordinator executors, EXCEPT that `deepseek-v4-flash/high` acts as
  the Hermes session worker / session-as-worker per `Coordinator/Worker
  Boundary` (equivalent worker role). The production-recovery DeepSeek executor
  exception is defined only in the deterministic consumer runtime below and
  does not change this desktop coordinator/worker policy.

### Coordinator/Worker Boundary

- For every task that writes or edits any file, changes code, configuration,
  package, build, or deployment, or performs any other side effect, the active
  desktop session is the **coordinator**. It MUST first attempt to dispatch a
  fresh worker subagent pinned to its own session model (Hermes =
  `deepseek-v4-flash`, Codex = `gpt-5.6-luna`), with `reasoning_effort=high` and
  `role=worker`. The coordinator MUST NOT perform the task directly EXCEPT via
  session-as-worker when worker subagent spawn is confirmed failed (below).
- **Worker equivalence:** `gpt-5.6-luna/high` and `deepseek-v4-flash/high` are
  EQUIVALENT worker roles. Either model may act as worker for any task scope,
  including live device/account/mailbox/workbook, recovery, lock, core
  infrastructure, deployment, or production actions. There is no
  task-classification gate; the worker model is simply the session's model.
- **Session-as-worker (the SOLE fallback):** when worker subagent spawn is
  CONFIRMED failed (runtime-unavailable, capability-unavailable, or
  dispatch-429 with a source, provider, and exact model pin — NOT a bare
  timeout, NOT an ambiguous outcome), the coordinator records
  `SUBAGENT_RUNTIME_UNAVAILABLE` BEFORE any local side effect, then performs
  the task directly as the worker using its own session model. This is the
  ONLY fallback. There is NO model substitution and NO reference to tool-layer
  fallback. **Fallback ordering:** (1) in-process subagent dispatch with the
  session's model; (2) for Codex sessions only, the gated external CLI
  transport (`External Codex CLI Worker Transport Fallback`) with the same
  session-model pin; (3) session-as-worker (all sessions). A Hermes session has
  no CLI route — it goes straight from (1) to (3). A bare timeout, unknown spawn outcome, or ambiguous dispatch is
  NOT a confirmed failure: the coordinator MUST reconcile state (prove no
  worker/session/process/lease/action exists for the scope) before proceeding;
  if exclusivity cannot be proven, the task records
  `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` and reaches `FINAL_BLOCKED` until
  deterministic reconciliation completes. The sole pre-granted offline Emergency Surgery L2
  exception defined in rule 6 is also permitted after its exact-diff, budget, scope,
  worker-termination, and focused-test gates pass; it never grants live/device/account authority.
- **Role transition (coordinator → worker mode):** when session-as-worker
  engages, the coordinator records its session model, FREEZES the assigned
  scope, and then acts as worker. If scope drift is detected, the session
  exits worker mode and returns to a fresh coordinator cycle (classify +
  record + spawn attempt); it MUST NOT expand scope while in worker mode.
- **Pre-dispatch record:** before dispatching any worker, the coordinator MUST
  record: the exact repo/path scope, command class, and model pin. If
  session-as-worker is used, record the session model. This record is part of
  the audit trail.
- **Scope-drift self-stop:** a worker (subagent or session-as-worker) MUST
  stop and return a handoff if it discovers its task has drifted outside the
  assigned scope. It MUST NOT continue or silently widen its scope.
- The coordinator MUST NOT edit the same implementation scope concurrently or
  perform it directly while a worker subagent is active on that scope. Its
  normal work is limited to read-only triage, artifact/diff inspection,
  deterministic read-only verification, coordination, and reporting — except
  when session-as-worker is active per the rule above.
- Pure read-only work, deterministic verification, integration inspection, and
  reporting may remain in the coordinator session. Any write,
  code/configuration, package/build/deployment change, or other side effect
  follows the worker rule (subagent first, session-as-worker on confirmed
  spawn failure), including small edits.
- The production recovery coordinator is deterministic code
  (watchdog/ledger/locks/state machine). It launches fresh model worker
  sessions; an LLM worker must not become a second control plane or bypass the
  coordinator's cap, lease, audit, or verifier gates.

<!-- The former "Coordinator Direct Fallback / Session-as-Worker Reference"
section is removed: session-as-worker is now defined solely in
Coordinator/Worker Boundary above. -->

### External Codex CLI Worker Transport Fallback

This is a narrowly gated transport fallback for **Codex sessions only**,
carrying the same fresh worker role (pinned to the session's own model —
`gpt-5.6-luna` for Codex) when an in-process Sub Agent/MCP dispatch cannot be
used. It is not a coordinator execution path, model/provider quota fallback,
audit route, scheduler/recovery loop, or second control plane. Hermes sessions
do not use this route (see `Coordinator/Worker Boundary` fallback ordering).
The coordinator remains
limited to orchestration, artifact/diff inspection, deterministic verification,
and reporting; only the bound external CLI child may patch or run live within
the reserved scope. The CLI path never replaces Terra/Sol or an independent
auditor, never uses a substituted model as a desktop/transport executor (the
Hermes `deepseek-v4-flash` session worker / session-as-worker per
`Coordinator/Worker Boundary` is the session's own model, not a substitution),
never grants
live authorization, never changes lock ownership, never adds an attempt, and
never resets an adapter cap or the recovery ledger. The separate production
recovery DeepSeek executor exception is not available to this transport path.
If any gate below is absent or fails, do not launch the CLI; record the runtime
handoff and evaluate the Coordinator Direct Fallback contract. The coordinator
must not patch or run live unless that separate contract has passed.

#### Exact allowlists and writers

Every launch reservation records two separate allowlists:

- For this policy task, the workspace mutation allowlist is exactly
  `D:\Taadaa\AGENTS.md`. No source file, live target, `automation-core`,
  consumer code, nearer/child `AGENTS.md`, configuration, package, build
  artifact, device, account, mailbox, workbook, or other file under
  `D:\Taadaa` is in scope. A different task must enumerate its own exact
  file/component allowlist before launch; a broad workspace root is not an
  implicit mutation grant.
- The orchestration metadata allowlist is exactly
  `D:\CodexRuntime\<project-id>\workers\<run-id>\`. It may contain only the
  reservation/owner/lease record, sanitized invocation/config, redirected
  JSONL stdout/stderr, heartbeat/checkpoint request and acknowledgement
  records, reconciliation and concurrent-churn ledger records, an immutable
  preimage snapshot/reference, and pre/post manifests for that run.
  Coordinator and launcher are the writers for these metadata paths during
  the whole lifecycle; the deterministic verifier may append its verification
  result there. The Codex child is not a metadata writer: it receives no
  `--add-dir` and is limited to `--sandbox workspace-write` with
  `--cd D:\Taadaa` and the exact workspace mutation allowlist. Sanitize argv,
  config, environment, and redirected output; never log API keys, tokens,
  cookies, credentials, or secret environment values. Because
  `workspace-write` is broader than one file, the launcher must bind and
  monitor the exact allowlist and fail preflight when it cannot reject a child
  write outside it; `--cd` is not permission for any other path. The
  post-verifier is an independent fail-closed check, not permission to widen
  the allowlist.

The reservation must state the writer and exact path for each artifact. The
minimum machine-readable set is `reservation.json` and `owner-lease.json`
(coordinator), `invocation.json` (launcher, sanitized argv/config/provider/
profile/environment plus CLI version and executable hash), `stdout.jsonl` and
`stderr.jsonl` (launcher redirects), `heartbeat.jsonl`,
`checkpoint-request.jsonl`, and `checkpoint-ack.jsonl` (coordinator/launcher),
`reconciliation.jsonl` and `concurrent-churn.jsonl` (coordinator), an immutable
preimage snapshot/reference, and mandatory `pre-manifest.jsonl`,
`post-manifest.jsonl`, and `verifier.json` (coordinator/verifier). The launcher
owns process-bound facts and redirected stdout/stderr; the coordinator owns
scope, lease, checkpoint, reconciliation, churn, preimage, and post-verifier
records. The post-verifier must read and cross-check this metadata set before
accepting the handoff. A metadata write must never be treated as a workspace
mutation or a live-action authorization.

#### Offline policy-only preimage, manifest, and scope verifier

For an offline policy-only task, before any child process is created the
coordinator must complete capture of an immutable, content-addressed preimage
(snapshot or byte-for-byte copy plus hash) of every path in the exact workspace
mutation allowlist and bind its reference/hash, the selected boundary, and the
completed `pre-manifest.jsonl` hash to the reservation `scope_hash`. Capture is
complete only after the selected paths and the exhaustive `AGENTS.md` inventory
have been enumerated, read, and hashed with the enumeration result recorded.
The preimage and pre-manifest are write-once and read-only after capture; a
missing, writable, changed, or mismatched reference is not evidence. The
mandatory `post-manifest.jsonl` must be captured after handoff for the same
selected scope and compare the pre-state rather than merely describing the
current files.

In this contract, `full-tree` means the full selected repository, worktree,
or exact allowlisted scope named by the reservation and `scope_hash`. It does
not mean the entire parent `D:\Taadaa` recursively, including nested
repositories/worktrees, unless those paths are explicitly selected. The
independent verifier must execute and retain a real no-index diff between the
immutable preimage and each current selected file (for example,
`git diff --no-index -- <immutable-preimage> <current-selected-file>`), with
the command, paths, status, and output. A self-diff/current-to-current
comparison, generated or synthetic diff/patch, or worker self-report is not
evidence; a missing no-index result is fail-closed.

The pre/post evidence must also contain an exhaustive inventory, separate from
the selected mutation manifest, of every nearer ancestor `AGENTS.md` that
governs a selected path and every child `AGENTS.md` reachable within the
selected boundary and its explicitly recorded enclosing parent workspace. The
reservation must record the exact canonical discovery command and scope; the
required command form is
`rg --files --hidden --no-ignore --follow --glob 'AGENTS.md' <canonical-boundary>`.
Its stdout path list, enumeration count/result, stderr/permission errors,
nonzero status, reparse traversal/cycle or out-of-boundary findings, and any
explicit exclusion must be retained. Hidden and ignored paths, reparse targets,
nested repositories, and worktrees within the boundary are included; an
exclusion cannot be implicit. Label each item `selected`, `governing-nearer`,
or `out-of-scope-audit-only`; inventory is audit evidence and never widens the
exact mutation allowlist. For every item record canonical path, content hash,
type, size, reparse metadata, encoding/EOL, and repository/worktree status; for
an unreadable item record the canonical path when available and the exact
read/permission error. No discovered item or enumeration error may be silently
omitted. `AGENTS.md` files outside the exact mutation allowlist must be
unchanged between pre and post inventories, and the post manifest must match
the exact pre path set and compare each recorded pre-state field. An unreadable
item, nonzero discovery, or permission error whose canonical path is outside
the selected and governing scope is retained as audit-only evidence and does
not by itself invalidate the selected reservation. A path or error that
overlaps the selected/worker scope, has unknown identity/boundary, or cannot be
classified as non-overlap remains fail-closed. Missing, incomplete, mismatched,
or boundary-unproven inventory or manifest, unexplained selected-scope
mutation, or metadata leakage is also fail-closed.

The pre-manifest must never be reconstructed, generated, or backdated after
handoff from current files, a worker self-report, last-write time, or a
generated diff/patch. `concurrent-churn.jsonl` is append-only and
artifact-backed. Every correction record must reference the original record
identifier and hash, preserve the original raw redacted observation/hash and
source artifact path, and include process/root/parent identity, timestamp,
canonical path extraction, boundary/scope, and the overlap decision. A
correction may add independently proven evidence but cannot overwrite the
original or turn an ambiguous/unproven observation into non-overlap by
assertion. A missing original artifact, missing correction source artifact,
unproven identity/path/boundary, or unproven overlap/non-overlap is fail-closed
and cannot be accepted as a handoff. Churn in a nested repository, another
scope, or a live run outside the allowlist is recorded as audit-only and is not
attributed to the worker when artifact-backed evidence proves non-overlap.
Such parent-workspace churn does not invalidate the reservation, widen the
selected boundary, or excuse a mutation inside it; an unknown or overlapping
path still fails closed.

#### Eligibility matrix

An external CLI launch is eligible only after the pre-create in-process
failure is authenticated and the same-scope absence proof is complete. The
absence proof must cover worker/session/process/lease/action, not merely a
missing local `worker_session_id`.

| Pre-create evidence | Decision and required action |
| --- | --- |
| A machine-readable, redacted Sub Agent/MCP transport-unavailable result, capability-unavailable result, or an in-process dispatch `429`, with runtime/tool identity, timestamp, correlation/request id, failure payload hash, and independent proof that no worker, session, process, lease, tool event, or action exists for the exact scope | `ELIGIBLE` for the gated external CLI contract after a new reservation; preserve the original evidence and do not count a second control plane or reset a cap |
| Provider/model quota exhaustion, authentication failure, policy denial, or a `429` not proven to be the in-process dispatch transport | `INELIGIBLE`; record the exact failure and `SUBAGENT_RUNTIME_UNAVAILABLE`, do not launch the CLI, and evaluate the separate Coordinator Direct Fallback only after exact-scope reconciliation and its explicit-authorization gates |
| The local `worker_session_id` is missing, empty, or not returned, by itself | `AMBIGUOUS`; missing identity is not proof that no worker was created; shut down/reconcile the exact same scope and do not launch in parallel |
| Any session/process/lease may exist, the dispatch outcome is ambiguous, a tool/action event exists, or child creation/side effect cannot be ruled out | `AMBIGUOUS`; preserve ownership, shut down and reconcile the exact same scope before any replacement; never relaunch in parallel |
| Evidence is incomplete or cannot distinguish transport failure from quota/auth/policy or child creation | Fail closed; treat it as `AMBIGUOUS` when a worker/process/lease/action may exist, otherwise `INELIGIBLE`; no external launch, and no direct fallback until exact-scope reconciliation proves that no worker/process/lease/action remains |

For an ambiguous case, the coordinator/launcher must reconcile the exact
worker/session/process/lease and all action evidence before any further work.
If a live side effect may have occurred, retain the target lock and record
`LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` with worker session, phase, target, last
progress, and evidence paths. A missing local identifier, a short wait, a
wrapper exit, or a status message is never an absence proof. No provider
quota/auth failure and no raw or unclassified 429 may enter this route.

#### Two-phase reservation and gated process contract

Phase 1 is pre-launch reservation. Before creating a child, the coordinator
records a unique `run_id`, `worker_session_id`, `correlation_id`, and launch
nonce; the exact workspace file/component scope and preimage hash; the
failure/eligibility evidence; the attempt number and adapter cap; the current
recovery state; a `lock_id` reference (or an explicit `none` for an offline
scope); and a positive integer `startup_handshake_timeout_seconds` no greater
than `120`. The reservation and owner/lease record are written atomically and
must be visible before process creation. The timeout is a startup-handshake
bound, not the five-minute checkpoint-request threshold, the ten-minute
confirmed-unavailable/stalled takeover threshold, or the thirty-minute
operational ceiling.

Phase 2 is the gated launch and binding. The launcher must capability-probe
the exact PID/session and provide a same-launch-process control channel for
checkpoint request/ack. It creates the child suspended, or an equivalent
fail-closed gate, then atomically records the root PID, process creation time,
executable path and hash, parent/root identity, and process-tree identity,
binds those facts to the reservation, and only then releases the child to
run. If the launcher cannot prove this gate, the external route is ineligible.
The first machine-readable startup event must be JSON `thread.started`; its
`codex_thread_id` is bound to the reserved `worker_session_id` and
`correlation_id` before any tool call, file action, device action, or other
side effect. No tool/action is allowed before that binding.

The control channel must be able to request the same worker's checkpoint and
verify an acknowledgement containing the nonce, root PID, process creation
time, `worker_session_id`, current phase, and evidence paths. Wrapper liveness,
an open stdout pipe, a process status, or an exit code is not an
acknowledgement. A raw noninteractive `codex exec` started without this
same-process control/checkpoint request-and-ack channel is ineligible.
At the five-minute threshold, the coordinator sends the request to the
coordinator-owned launcher for this exact `run_id`; the launcher issues the
same-process request and writes the request/ack records. The acknowledgement
must also echo `run_id` and `correlation_id`, and the coordinator records the
decision and evidence. This does not alter the existing ten-minute takeover
rule or authorize a replacement.

#### Exact CLI command and lifecycle

The child must be a fresh, non-resumed, non-forked invocation with the exact
semantics below (equivalent flag spelling is allowed only when the semantic
mapping is recorded and preflight rejects unknown, duplicate, missing, or
mismatched flags):

```text
codex exec --model gpt-5.6-luna --config model_reasoning_effort="high" --sandbox workspace-write --cd D:\Taadaa --skip-git-repo-check --strict-config --json <sanitized-task-input>
```

The launcher must explicitly select and verify the provider/profile and the
allowlisted environment, and record the CLI version and executable hash in
sanitized invocation metadata. The positional task input must be a sanitized,
single-use canonical UTF-8 JSON payload with `run_id`, `worker_session_id`,
`correlation_id`, `task_nonce`, `scope_hash`, and `payload_sha256` bound to the
reservation; do not interpolate an unbounded shell prompt or secret into argv.
The launcher verifies the canonical serialization and single-use nonce before
child release. Forbid resume/fork commands and flags,
`--add-dir`, `--ignore-rules`, and every dangerous approval, sandbox, or
workspace bypass flag (including their aliases). Reject duplicate or
unknown flags, path/scope mismatch, model mismatch, non-`max` effort, or an
unverified provider/profile/environment before child release. Do not pass or
log secret values; redacted argv/config/env must be sufficient to reproduce
the preflight decision.

The launcher records the numeric startup-handshake deadline before launch and
enforces it separately from the existing watchdog rules. If startup failure
is proven to be pre-binding and side-effect-free, record
`EXTERNAL_CLI_WORKER_START_FAILED` together with
`SUBAGENT_RUNTIME_UNAVAILABLE`, fail closed, and do not relaunch. If binding,
process identity, lease ownership, or side-effect status is ambiguous, shut
down/reconcile the exact same scope and do not relaunch. A bound worker stall
may use only the existing single-replacement rule after verified shutdown and
lease reconciliation; never run a parallel replacement or reset the cap.
The five-minute checkpoint request, ten-minute same-no-signal takeover rule,
and thirty-minute operational ceiling remain exactly as defined in the
watchdog section; the ceiling is not a hard kill when progress continues.

The runtime lease for this child is not a device lock and cannot substitute
for the existing device-lock identity `host` + `pid` + `lock_id`. Lock
retention, ownership, guarded release, recovery handoff, and cross-consumer
reclaim rules remain unchanged. Process exit, status, scheduler state, wrapper
liveness, and worker self-report are never completion proof.

#### Recovery and verification invariants

For live work, the external transport must preserve
`DETECTED -> CLASSIFIED -> RECOVERY_RESERVED -> RECOVERING -> RECAPTURED ->
RETRYING -> VERIFIED_SUCCESS | FINAL_BLOCKED`, the strict handler registry,
artifact-backed recapture, explicit verifier, owner lease/heartbeat,
fail-closed transitions, configured attempt cap, same-target Sol terminal
review and handoff ledger, and target lock retention/ownership. A transport
fallback cannot grant live authorization or bypass any gate. It also preserves
existing concurrency, random machine order, and bounded random stagger;
never force `MaxParallel=1`, reorder machines, or turn fallback into a
second recovery control plane.

The post-verifier must apply the offline policy-only contract above: compare
the immutable preimage to each current selected path with the retained real
no-index result, and cross-check the mandatory pre/post manifests, the
nearer/child `AGENTS.md` inventory, and the concurrent-churn ledger. For this
task, the accepted changed set is exactly `D:\Taadaa\AGENTS.md`: there must be
no encoding or EOL rewrite, every other child/nearer `AGENTS.md` hash and
status must remain unchanged, and parent/nested-repository churn cannot be
used to excuse a selected-scope mutation. Any extra or unexplained mutation,
metadata leakage, unproven selected-scope boundary, unproven binding, or
verifier gap is a fail-closed handoff. The coordinator must never apply the
patch directly unless the Coordinator Direct Fallback contract has passed and
the `COORDINATOR_LOCAL_MAINTENANCE_FALLBACK` marker is recorded.

### Shared Live Recovery Control Plane

- This is the common recovery rule for every live automation flow under
  `D:\Taadaa`, regardless of whether the flow is started by a schedule,
  manual command, CLI, watchdog, event, or another adapter. Every target must
  follow `DETECTED -> CLASSIFIED -> RECOVERY_RESERVED -> RECOVERING ->
  RECAPTURED -> RETRYING -> VERIFIED_SUCCESS | FINAL_BLOCKED`.
- A schedule/scheduler is only one trigger and adapter. It may emit detection
  and provide flow-specific configuration, but it must not own the per-target
  state machine, retry loop, completion proof, attempt cap, lease, or verifier.
  Schedule cadence and selection remain adapter policy; they do not create a
  second recovery control plane.
- The common control plane is per-target and must enforce the strict handler
  registry, artifact-backed recapture plus an explicit verifier, owner lease
  and heartbeat, fail-closed transitions, and a configured attempt cap.
  Preflight must reject a missing required handler through
  `RecoveryHandlerRegistry.validate_required()`; missing or invalid evidence,
  lease, verifier, or cap cannot be converted into a retry or success.
- The attempt cap is configuration supplied by the flow/consumer adapter and
  recorded before live execution. Model escalation, worker replacement,
  schedule re-fire, lock recovery, or process restart never resets or bypasses
  that cap. A cap is a bound, not live authorization.
- Provider, account, workbook, and business-flow policy stays in the consumer
  adapter. `automation-core` owns only the shared app-neutral enforcement and
  contract; consumer adapters supply the provider-specific handler and
  trigger/configuration binding.
- Editing policy, performing an audit, a worker handoff, a scheduler event, or
  a process/worker status update never starts live automation automatically.
  Live execution requires an explicit authorized scope and the same
  fail-closed control-plane gates.

### Worker Lease / Heartbeat Watchdog (session-model workers — Luna/high and flash/high)

- A fresh session-model worker (Luna/high or flash/high), whether reached through in-process Sub Agent/MCP
  transport or the eligible gated external CLI transport, has an initial
  reasoning grace period. A `wait_agent` timeout, launcher timeout, empty
  status, or absence of a final/output message is not proof that the worker is
  hung, unavailable, or stalled.
- For an in-process Codex worker, `read_thread` is the primary liveness probe:
  a thread reported as `active`/`inProgress`, any change to `updatedAt`, or new
  commentary, reasoning, or tool activity is worker activity. Each such signal
  resets the no-activity timer, including when a bounded wait has expired or
  `wait_agent` returned an empty status.
- Monitoring must be sparse and event-aware: take one initial `read_thread`
  snapshot after dispatch, then read it once after each bounded wait of about
  180 seconds. Do not continuously poll; use those snapshots and newly
  observed activity to avoid unnecessary telemetry overhead and quota use.
- For the session-model worker (Luna/high or flash/high), the coordinator must use a sufficiently long wait interval and
  must not busy-poll with repeated 1-second, 10-second, or 30-second waits. If
  the process is alive or the worker is still inferring, the coordinator
  continues waiting and must not kill it, start a parallel worker, or continue
  the same scope elsewhere. The external launcher's numeric startup-handshake
  timeout is recorded before launch and is separate from the five-minute
  checkpoint-request threshold, ten-minute confirmed-unavailable/stalled
  takeover threshold, and thirty-minute operational ceiling.
- If `close_agent` returns `previous_status:"running"`, or the external
  launcher's shutdown/reconciliation is pending, the coordinator must not
  spawn a replacement worker or continue the same scope until shutdown and
  lease reconciliation have been verified.

- Every fresh session-model worker (Luna/high or flash/high) assigned a write or
  live task must have one
  coordinator-owned owner record, an exclusive scope, a unique
  `worker_session_id`, and a lease artifact/checkpoint before work starts. The
  scope must identify the target and files/components it may change; two write
  workers must never run concurrently against the same target or file.
- After `preflight`, `patch`, `test`, and `handoff` (or an explicit reason a
  phase was not reached), the worker must emit the checkpoint through its
  approved control channel. The coordinator/launcher writes the checkpoint
  artifact and updates `heartbeat` and `last_progress`, identifies the current
  phase and worker session, and points to the relevant artifact, diff, test, or
  handoff evidence. An external CLI child never writes the metadata directory;
  its request/ack stream is the evidence the coordinator/launcher records.
- If five minutes pass with no heartbeat, tool activity, artifact/checkpoint,
  or file change, the coordinator sends a checkpoint request to the exact
  current worker identified by its `worker_session_id`. This five-minute
  threshold is only a checkpoint-request threshold; it must not by itself
  close, kill, or replace the worker.
- For an in-process Codex worker, do not send a checkpoint when the latest
  `read_thread` snapshot still shows activity, even if a bounded wait window
  has ended. Send it only when there is no actual activity and `updatedAt` is
  unchanged, at about five minutes from the last observed activity; one
  bounded wait can reach that point, so a second five-minute window is not
  required for the request. This does not change the existing ten-minute
  confirmed-unavailable/stalled close or takeover threshold.
- A wait or polling timeout is not proof that the worker is hung; it only
  bounds waiting for an observation and never authorizes a kill or close. If
  the current worker is alive or still processing, the coordinator continues
  sending input to that same worker and must not start a parallel worker. Only
  if the same no-signal condition persists for one further five-minute window
  (10 minutes total), and the current worker is confirmed unavailable or
  stalled, may the coordinator close or take over the same exclusive scope.
  There is no 15-minute threshold. A short wall timeout must not kill a live
  recovery worker that may already have caused a side effect; the recovery
  state machine and its bounded verifier remain authoritative.
- If heartbeat is lost after the worker enters a live or other side-effect
  phase, fail closed. Preserve and reconcile the target lock through its
  guarded owner/recovery path and record
  `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` with the worker session, phase, target,
  last progress, and evidence paths. A replacement worker may reconcile
  artifacts and lock state first, but may not perform further live action until
  that reconciliation is recorded and verified under the existing recovery
  state machine.
- Allow at most one replacement worker for the same exclusive scope before
  reporting a technical blocker. A replacement does not authorize parallel
  execution, revive the closed session, reset attempt caps, or bypass
  the coordinator-only pre-create `SUBAGENT_RUNTIME_UNAVAILABLE` gate, the
  Terra/Sol read-only boundary, or any
  required recovery handoff.
- The 30-minute worker limit is an operational ceiling, not a hard kill
  timeout. If heartbeat or other evidence of progress continues at that
  boundary, the coordinator must not kill the worker solely because the
  ceiling elapsed; any handoff or takeover remains subject to the lease,
  recovery, attempt-cap, and verifier rules above.
- Worker self-report, process exit, and scheduler/worker status are never
  completion proof. The coordinator must read the lease/checkpoint artifacts,
  inspect the diff and evidence, and run the applicable verifier before
  accepting the handoff or declaring success/blockage.

### Fresh Session-Model Dispatch and Wait Integrity (Luna/high and flash/high)

This section applies to every repository, worktree, consumer, and live flow
under `D:\Taadaa`. It clarifies the `Coordinator/Worker Boundary`, the
`External Codex CLI Worker Transport Fallback`, and this watchdog; it does not
weaken any exact-scope, lease, lock, recovery, audit, handler, verifier, or
attempt-cap requirement. The normal worker-only boundary remains active:
neither a user command nor a coordinator status observation grants the
coordinator direct patch or live authority, except the sole pre-granted offline
Emergency Surgery L2 defined in rule 6; that exception never grants live authority.

- Within one reserved workspace/exclusive scope, at most one fresh,
  non-resumed session-model dispatch (Luna/high or flash/high) may be active. Do
  not spawn a parallel worker,
  a replacement, or a second control plane while the current worker has not
  produced a final status or valid evidence of no-signal and the existing
  shutdown/lease reconciliation is incomplete. A status message, timeout,
  empty output, or user urgency does not change this rule. A harness-returned child timeout counts as a final status for retry and L2 purposes.
- A `429` or slot-unavailable observation may be retried only after it is
  classified and recorded as a redacted machine-readable event containing the
  runtime/tool identity, UTC timestamp, `run_id`/correlation id, exact scope,
  worker/session identity when known, failure code, response/request id or
  payload hash, backoff number, and evidence path. The bounded backoff windows
  are exactly `30s -> 60s -> 120s`; do not busy-poll, add unbounded waits, or
  perform a blind retry. The backoff is not a replacement authorization or a
  live-action authorization.
- The existing same-scope replacement cap remains one. A replacement requires
  the current worker to be finally stopped or independently proven unavailable
  under the existing heartbeat/lease/process reconciliation, with no
  overlapping worker, session, process, lease, tool event, or action. Never
  launch a replacement while those facts are ambiguous. A 429/slot signal
  must not reset an attempt cap, release a target lock, or bypass the recovery
  state machine.
- When a bounded wait/window expires, or `wait_agent` returns a timeout or
  empty status, classify that observation only as `WAIT_WINDOW_EXPIRED` with
  the scope, phase, wait interval, last heartbeat, lease/process/thread
  evidence, and timestamp. It is not `WORKER_TIMEOUT`, not
  `SUBAGENT_RUNTIME_UNAVAILABLE`, and not evidence that an in-process Codex
  worker died. `SUBAGENT_RUNTIME_UNAVAILABLE` remains reserved for the
  separately defined, machine-readable runtime/transport/capability evidence
  with the required pre-create absence proof.
  `WAIT_WINDOW_EXPIRED` is not permission to close, take over, replace, retry,
  or perform live action.
- A checkpoint request is only a request, never an acknowledgement. Record
  `checkpoint-ack`/ACK only after an actual acknowledgement contains the
  request nonce, `run_id`, correlation id, worker session identity, current
  phase, and heartbeat/lease/evidence references. Sending a request, reaching
  a timeout, observing an open pipe or process, receiving empty output, or
  reading a worker self-report is not an ACK. Sending the request or receiving
  no ACK leaves the current worker and lease in place and follows the existing
  watchdog thresholds.
- Close or takeover is permitted only after a final status, or after the
  existing no-signal threshold is met by independently retained heartbeat,
  lease, process, and applicable thread evidence: the five-minute
  checkpoint-request threshold followed by the further five-minute
  confirmed-unavailable/stalled window (ten minutes total), with guarded
  shutdown and exact-scope reconciliation.
  A request without ACK, an empty status, `WAIT_WINDOW_EXPIRED`, or a short
  caller wait is insufficient. Before any replacement, verify shutdown,
  lease ownership/reconciliation, target-lock retention, and absence of a
  concurrent same-target worker/action.
- These dispatch rules preserve the required per-target
  `DETECTED -> CLASSIFIED -> RECOVERY_RESERVED -> RECOVERING -> RECAPTURED ->
  RETRYING -> VERIFIED_SUCCESS | FINAL_BLOCKED` lifecycle, device-lock
  identity `host` + `pid` + `lock_id`, strict handler/verifier evidence,
  configured attempt cap, audit trail, random machine order, and bounded
  random stagger. They do not turn worker status, a wait window, or a user
  command into completion proof or expand live/production scope.

### Worker and Audit Roles

- A worker/recovery owner and an independent auditor are different roles. A
  worker handoff is not an audit of the worker, and using a worker does not by
  itself require another auditor.
 - Each goal has at most one independent read-only audit slot for an unchanged
    plan/diff/evidence set. When an audit is required, use the active order
   `plan-review` (gpt-5.6-terra via 9Router)/high -> `plan-review-hard` (gpt-5.6-sol via 9Router)/high -> Claude CLI (`claude-sonnet-5`/high for
   medium tasks or `claude-opus-5`/medium for hard tasks, quota-gated) -> OpenCode free (dynamic catalog). These are
    mutually exclusive alternatives, not cumulative reviews.
 - The worker cannot approve its own plan, patch, audit, or completion. Only a
   read-only auditor plus deterministic verifier evidence can support acceptance.
- A Terra/Sol read-only advisor does not consume the slot. A Terra/Sol agent
  explicitly assigned as the independent reviewer does consume
  that same slot; after its complete usable verdict, do not invoke an external
  provider on unchanged evidence.
- Open a second audit only after a material patch or evidence change, an
  unresolved P0/P1 disagreement, or an explicit new policy boundary. Main
  verification of tests, artifacts, and the final diff is always required and
  does not consume the audit slot.

### Configuration Policy Audit Gate

The consolidated policy/diff uses exactly one implementation/code audit slot.
The active order is `plan-review` (gpt-5.6-terra via 9Router)/high -> `plan-review-hard` (gpt-5.6-sol via 9Router)/high -> Claude CLI
(`claude-sonnet-5`/high for medium tasks or `claude-opus-5`/medium for hard
tasks, quota-gated)
-> OpenCode free (dynamic catalog). If the primary 9Router plan-review call is unavailable, advance through
the same active order on the recorded failure signal.

The overall-plan audit is separate under the Hermes route: the coordinator
first produces a read-only plan with `deepseek-v4-flash`, then
`gpt-5.6-luna/max` performs the read-only plan audit. Policy, automation-core,
live, and multi-repository tasks additionally require a `Sol` audit gate. A
hard task cannot pass its plan gate or reach implementation without this
recorded plan/audit evidence.

Any change that edits this workspace `AGENTS.md`, a custom-agent TOML profile,
global Codex configuration, the OneDrive Codex bundle, or two or more nearer
consumer `AGENTS.md` files is a policy change. Before declaring that change
complete, consume exactly one independent read-only audit slot for the
consolidated policy/diff. Use the active order above; a global
policy/configuration change is a hard task and also requires the Sol audit gate
after the separate overall-plan route. Do not
run both a configured subagent review and an external provider on the same
unchanged policy.
Record the auditor, scope, verdict, and any read-access limitation. This gate
is separate from live recovery attempts and does not authorize device,
account, mailbox, workbook, or production actions.

## Codex Model Routing

This workspace mainly builds automation scripts and operates/debugs recovery
failures. Classify the task briefly before acting; the user does not need to
select a model manually.

### Read-Only Models (never patch / never live)

- Use **Luna / high** only for read-only triage, research, diagnosis,
  artifact/log review, or other read-only work that needs deeper tracing. It
  is not an implementation or live executor.
- Use **Luna / high** only for clear, repeatable read-only support work with
  an objective output: repository/artifact scans, log/UI XML extraction or
  classification, structured summaries, and test/fixture analysis. It must
  not edit files or run live/side-effecting work.
- **Terra / high or xhigh** and **Sol / high or max** are read-only planner,
  advisor, or auditor roles. They may inspect evidence and propose a
  hypothesis, patch, handler, or verifier plan, but they never edit files,
  patch code, or run live/side-effecting work.
- Use **Sol / ultra** only for meaningful independent workstreams or the
  deepest investigation: multi-machine incidents, cross-consumer rollout,
  difficult artifacts/UI/ADB regressions, security, migrations, or substantial
  architecture refactors. It remains read-only and is not a patch/live
  worker; do not use Ultra by default.

### Write/Live Workers

Worker model for all write/live tasks is the session's own model — Hermes =
`deepseek-v4-flash`, Codex = `gpt-5.6-luna` — with the session-as-worker
fallback defined in `Coordinator/Worker Boundary` (single source of truth).
No task-classification gate; `gpt-5.6-luna/high` and `deepseek-v4-flash/high`
are equivalent worker roles.

**Coordinator role:** The main session is the coordinator/report surface: it
classifies the task, routes work to the correct worker, inspects
artifacts/diffs, performs deterministic read-only verification, and reports
the result. The coordinator, using pre-recorded verifier proof and (when
required) Terra/Sol audit advice, decides whether to accept the handoff; a
model self-report never decides `SUCCESS` or `FINAL_BLOCKED`.

For independent review selection, a bounded one-consumer task normally needs
no external audit; when an independent reviewer is required, use Terra / high
for moderately-difficult tasks and Sol / high only for shared-core,
multi-consumer, security/account-safety, lock/verifier/scheduler, materially
ambiguous, or same-target `FINAL_BLOCKED` scope. This routing selects one
reviewer; it does not add an audit after every worker handoff.

Model choice never authorizes live device, account, mailbox, or workbook
actions beyond the user's stated scope. For live/recovery work, apply the
existing recovery state machine and require verifier proof regardless of
model.

### Goal Escalation For Automation Recovery

For a goal that builds, runs, diagnoses, or recovers automation, apply this
model escalation ladder within the same goal and target ledger:

The three model stages below are **not** three live attempts. A model handoff
may happen during offline diagnosis, code/test work, or review. The common
control plane above applies to every live flow; each consumer/flow adapter
declares its configured cap and trigger mapping. A schedule-specific ladder is
adapter configuration, not a separate recovery control plane.

Escalating the model is never, by itself, a recovery strategy. Every handoff
must include what was tried, why it failed, and a materially different next
hypothesis, patch, selector/handler, or verifier plan. The stronger model must
not repeat the same command or patch merely because it is stronger.

1. The coordinator performs detection/classification and evidence routing; after
   the strong plan is accepted, a fresh **session-model worker** (Hermes =
   `deepseek-v4-flash`, Codex = `gpt-5.6-luna`; `gpt-5.6-luna/high` and
   `deepseek-v4-flash/high` are equivalent worker roles — in-process or through
   the eligible gated external CLI transport for Codex) performs implementation,
   focused tests, and every target-scoped live verification assigned by the
   coordinator. It records the entrypoint, signature, artifacts, target state,
   and proposed handler.
2. For compatibility, the TikTok schedule adapter may configure the existing
   seven recovery executions after detection: fresh session-model worker
   (Luna/high or flash/high); Terra/high
   advisor -> fresh session-model worker; Terra/xhigh -> fresh session-model
   worker; Sol/high -> fresh
   session-model worker; then three distinct Sol/max advisor -> fresh
   session-model worker rungs.
   Terra/max and Sol/xhigh remain invalid rungs in that adapter. This mapping
   is an adapter-level cap/routing choice; every other consumer/flow adapter
   declares its own configured cap while using the same control plane.
3. For that TikTok schedule adapter, the same signature allows eight meaningful
   target records: the original detection plus seven materially different
   session-model worker
   live recoveries. Do not create an eighth live retry merely by escalating the
   model; otherwise record `FINAL_BLOCKED` as required by the common recovery
   contract. A meaningful target attempt begins only after the failure is
   classified and its reserved handler performs bounded recovery, artifact
   recapture, target retry, and verifier evaluation. A preflight stop before
   target action does not consume an attempt, but it cannot be relabeled after
   live action to evade the configured cap.
4. Terra/Sol remain advisory-only and never create an additional live attempt.
   Terra supports only high/xhigh and Sol supports only high/max in this
   adapter mapping; repeated advisor rungs require materially different
   evidence question, hypothesis, action, and verifier. Normally the
   session-model worker is
   the patch/live worker. The production-recovery exception is deterministic:
   when the session-model worker returns valid machine-readable
   provider/quota-unavailable
   evidence, persist `provider_mode=deepseek_executor` for the incident and
   skip every Terra/Sol call and worker wait. Run only the exact DeepSeek
   executor ladder (Flash/max; Pro/low, medium, high, max, max, max) through
   the same handler, lease, audit, reservation, target command, recapture,
   verifier, and seven-live-attempt cap. This exception does not change the
   desktop coordinator/worker rule; raw, ambiguous, auth, policy, or invalid
   evidence never activates it.

The escalation owner is not automatically followed by a second auditor. If the
Sol recovery owner already reviewed the final target evidence, relevant diff,
and verifier plan required by the terminal gate, reuse that review in the one
audit slot; otherwise reserve the one required independent review separately.

### Planner Effort Escalation and Fresh-Session Gate

- Terra planner escalation is high -> xhigh; Terra/max is not a valid rung.
  Sol planner escalation is high -> max; Sol/xhigh is not a valid rung in this
  routing. Never raise effort merely to repeat the same strategy.
- Every effort increase must open a new independent Codex session. Do not
  continue, fork, or reuse the prior Sol session as the escalated attempt.
  Give the new session only a concise evidence handoff and require a
  materially different hypothesis, review angle, patch, handler, or verifier;
  repeating the prior session's prompt, command, or patch is forbidden.
- This gate also applies after Claude CLI is blocked by the 85% quota gate and
  the audit advances through OpenCode, cx
  workhorse. A fallback model change or effort increase must
  use a fresh session and a different approach while preserving the prior
  failure signature and artifacts. Keep the actual provider audit label
  unchanged.
- If the active runtime does not support the next effort level or a fresh
  session, record `SUBAGENT_RUNTIME_UNAVAILABLE` with the evidence handoff;
  never simulate escalation by rerunning the old session.

### Mandatory same-target terminal recovery review

- Before the active agent records `FINAL_BLOCKED` for any target, it must
  complete a **Sol / high terminal recovery review** for the **same target**,
  unless the subagent runtime is unavailable. A Terra recovery failure is
  therefore never a terminal decision by itself, and a direct-Sol path is
  subject to the same gate. Production recovery is the narrow exception:
  after a valid Luna provider/quota-unavailable activation, the deterministic
  DeepSeek executor mode must not call Terra/Sol; DeepSeek unavailable before
  reservation or an UNKNOWN crash may reach `FINAL_BLOCKED` from its own
  evidence-backed ledger/verifier gate.
- The Sol handoff must carry the same target identifier, failure signature,
  attempt ledger, checkpoint/report paths, and recapture artifacts. A Sol call
  for a different target, account, video, or incident does not satisfy this
  gate.
- Sol may review evidence, produce a materially different handler/verifier
  plan, or route an app-neutral defect to `automation-core`. Sol review is not
  permission for a blind retry beyond the applicable versioned cap and does not
  reset that limit.
- This is a terminal recovery gate, not a generic second code audit. When the
  same Sol review includes the final evidence, relevant diff, and verifier
  proof, it also satisfies the one independent audit slot; do not call another
  Sol, AG Claude, Claude CLI, OpenCode, or cx auditor for
  the unchanged evidence.
- `FINAL_BLOCKED` is allowed only after `sol_handoff_completed=true` is recorded
  for the target, with Sol's verdict and evidence path. The active Codex
  orchestrator owns this record at
  `D:\CodexRuntime\<project-id>\recovery\handoff-ledger.jsonl`; each target
  entry must include `target_id`, `failure_signature`, `attempt_count`,
  `terra_outcome`, `sol_handoff_completed`, `sol_verdict`, `evidence_paths`,
  and `updated_at`. Live scripts must not fabricate or overwrite this gate.
- The active agent must verify this same-target handoff ledger before reporting
  the target outcome; model self-report, worker exit, and a Sol call for a
  different target are not completion proof. If the runtime cannot spawn Sol,
  record `SUBAGENT_RUNTIME_UNAVAILABLE` with the evidence handoff and stop
  before any further live retry. The external CLI session-model transport is not a
  Sol/Terra/auditor substitute and cannot satisfy this terminal gate.

### Automatic Ultra Gate

At the start of a goal that may need Sol or Ultra, the current agent must make
a compact internal classification before choosing the next model. Do not print
the gate for ordinary bounded Luna tasks; default those tasks to `NO` silently.
Only include the details in the handoff when escalation is actually needed:

```text
ULTRA_GATE: YES | NO
REASONS: <matching signals>
SHARDS: <number and short names>
```

Set `ULTRA_GATE=YES` only when at least one objective signal is true: the
change spans `automation-core` plus two or more consumers; two or more
repositories, machines, targets, or independent execution paths must be
investigated or changed in parallel; a versioned contract migration/rollout
needs core, consumer, and regression workstreams at the same time; a
multi-machine incident has distinct artifact/signature clusters; or a
security/account-safety/scheduler/lock/production review needs separate
implementation and audit shards.

Set `ULTRA_GATE=NO` silently for one execution path, one module, one consumer,
one target, or a bounded artifact classification task, even when the bug is
annoying. Use Sol/high for those cases. A vague statement that a task is
"hard" is not an Ultra signal. If YES, record reasons/shards and route to
Sol/Ultra (or spawn the independent Sol subagents when the active surface
exposes Ultra); if NO, keep the normal Luna/high -> Terra/high -> Sol/high
ladder without adding a verbose gate report.

`create_goal` records the objective; it does not itself switch models. The
selected agent must spawn a configured stronger subagent when the matching
escalation gate is met; it must not merely write that a handoff is needed. The
handoff is a Codex orchestration action (for example, the collaboration
`spawn_agent` tool), not a Python/PowerShell branch inside the automation repo.
The repo's live script is not expected to call models. If the active Codex
surface does not expose the required subagent/model tool, report that runtime
limitation explicitly and preserve the evidence handoff; do not pretend the
repo itself can perform escalation.

### Goal and Provider Quota Separation

- A goal state such as `usageLimited`, `remainingTokens=null`, a per-session
  usage-limit message, or an effort/model cap is not proof that the Codex
  provider account quota is exhausted. Do not report `CODEX_QUOTA_EXHAUSTED`,
  call `update_goal` with `complete`/`blocked`, or stop the user's goal solely
  from one of those signals. Record the exact signal as
  `GOAL_USAGE_LIMIT_REACHED` and preserve the objective, evidence handoff,
  and unfinished work.
- Only a provider-reported Codex quota/limit result from the active runtime
  may classify the Codex account as exhausted. A still-running main Codex
  thread is evidence that the current route is usable; it does not authorize
  relabeling a separate Sol/subagent session limit as global Codex quota.
- If the current goal/session reaches its own usage limit while work remains,
  continue through a fresh independent Codex session with the same task
  boundary and a concise evidence handoff when the runtime supports it. The
  new session must not repeat the prior prompt, command, or patch. If the
  runtime cannot create that session, report `SUBAGENT_RUNTIME_UNAVAILABLE`
  with the handoff; do not claim that Codex quota is exhausted.

### DeepSeek Quota Fallback (9Router)

When the session-model worker (Luna/high or flash/high) returns valid
machine-readable provider/quota-unavailable
evidence during production recovery, the deterministic runtime persists
`provider_mode=deepseek_executor` for that incident/signature. It immediately
skips Terra/Sol and does not wait or probe Luna again. This is a production
recovery exception only; the desktop coordinator/worker policy remains the
session's own model (Hermes = `deepseek-v4-flash`, Codex = `gpt-5.6-luna`) for
implementation/live work outside this runtime.

- Allowed DeepSeek IDs are exact, with provider `9router`:
  `cmc/deepseek/deepseek-v4-flash` and `cmc/deepseek/deepseek-v4-pro`.
- `model_reasoning_effort` is separate and valid only as `low`, `medium`,
  `high`, or `max`; `auto`, `thinking`, `xhigh`, `ultra`, and silent downgrade
  are forbidden.
- The exact seven-slot executor ladder is Flash/max, Pro/low, Pro/medium,
  Pro/high, Pro/max, Pro/max with a different strategy/evidence/fingerprint,
  and Pro/max with the final different strategy/evidence/fingerprint.
- DeepSeek patch commands use `workspace-write` with the exact provider/model/
  effort and no dangerous sandbox bypass. They may not run arbitrary batch/live
  shell. The only live action is the exact reserved target command after the
  handler, lock/lease, audit, reservation, recapture, and verifier gates.
- The fallback preserves the per-target state machine and seven-live cap. A
  DeepSeek outage before reservation fails closed with evidence; a crash after
  reservation is `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH`. Raw, ambiguous,
  authentication, policy, or invalid Luna results never activate this mode.
- Record the fallback decision and model/effort in the recovery ledger
  (label `DEEPSEEK_FALLBACK`); a fallback verdict is never Claude approval
  and never completion proof by itself.


## Independent Audit and Claude

### Audit slot and reviewer routing

- An independent audit is a read-only review of the finalized plan or
  consolidated diff/evidence, not an audit of a worker's identity or self-report.
- Use no external auditor by default for a bounded one-consumer task. If that
  scope still needs an independent review, use Terra / high.
- Use Sol / high for shared-core, multi-consumer policy, security/account
  safety, lock/verifier/scheduler, or materially ambiguous root-cause scope.
- The active v5 audit chain is mutually exclusive for the one audit slot:
  `plan-review` (gpt-5.6-terra via 9Router)/high -> `plan-review-hard` (gpt-5.6-sol via 9Router)/high -> Claude CLI (`claude-sonnet-5`/high for medium
  tasks or `claude-opus-5`/medium for hard tasks, quota-gated) -> OpenCode free (dynamic
  catalog). Stop
  after the first complete usable verdict. A quota, runtime, or access failure
  may advance the chain; it does not add a second opinion on unchanged evidence.
- An independent Terra/high or Sol/high verdict follows the same rule: it fills
  the one slot and is not followed by another active route unless a material
  change or documented second-audit exception opens a new slot.
- Re-audit only after a material patch/evidence change, an unresolved P0/P1
  disagreement, or an explicit new policy boundary. Local test/diff
  verification remains mandatory regardless of the selected reviewer.

### External audit route selection (Active Audit Routing Policy v6 chot 2026-08-09)

- Active route for bounded/broader implementation audits (read-only, mot slot):
  9Router combo `plan-review` (gpt-5.6-terra)/HIGH (dung DUNG MOT route moi task)
  -> 9Router combo `plan-review-hard` (gpt-5.6-sol)/HIGH (case kho)
  -> 9Router combo `opencode-audit` (`oc/nemotron-3-ultra-free` -> `oc/big-pickle` -> `oc/longcat-2.0-free` -> `oc/ling-3.0-tiny-free`; OpenCode quota lon nhat)
  -> `AUDIT_ALL_ROUTES_FAILED`.
- KHONG dung lam auditor: `gpt-5.6-luna` (la worker, thieu trinh), `cmc/*` (khong co quota),
  `opencode-free`/`oc/deepseek-v4-flash-free` (resolve thanh DeepSeek Flash = worker),
  Gemini (cam, policy v6), Command Code (inactive).
- Planner (read-only, 1 call): case thuong combo `plan-review` (`gpt-5.6-terra`)/HIGH, case kho combo `plan-review-hard` (`gpt-5.6-sol`)/HIGH;
  fallback combo `opencode-audit`.
  KHONG dung `gpt-5.6-luna` lam planner (worker); khong DeepSeek lam planner/auditor.
- Auto-recovery khi AG fail giua chung: LAYERS tuong tu, route da fail khong quay lai trong task;
  moi task toi da 1 lan AG; retry cung model toi da 1 lan chi cho timeout/5xx;
  429/quota/auth/model-not-found/empty output -> chuyen model NGAY.
- If the plan audit is unavailable, record the runtime failure and do not invent approval.
- `Terra/high` or `Sol/high` selected as the independent reviewer fills the
  same slot and is not followed by another active route on unchanged evidence.
  Sol/high remains reserved for shared-core,
  multi-consumer, security/account-safety, lock/verifier/scheduler,
  materially ambiguous, or same-target terminal-recovery scope.

- Do not invoke the Claude CLI hard-task rung merely because an audit slot
  exists. It is selected by the recorded medium/hard classification and is
  always quota-gated. A difficult same-target `FINAL_BLOCKED` alone does not
  replace the mandatory Sol review gate.
- When Claude is selected, use the `claude-final-audit` skill with real Claude:
  (`claude-sonnet-5`, effort `high`) for medium tasks or (`claude-opus-5`,
  effort `medium`) for hard tasks, when the CLI is available and the quota hard
  gate below permits it.
- Full Claude audits may take several minutes; allow at least
  `timeout_ms=600000` and wait for process completion.
- Every Claude audit invocation must pass an orchestration/tool timeout of at
  least `600000ms` (10 minutes) and poll the same process until it completes.
  A timeout shorter than this is a caller-side short timeout, not evidence that
  Claude is unavailable; preserve the read-only audit artifact and classify
  the actual process outcome before falling back.
- A short wrapper timeout is not evidence of quota, authentication, or Claude
  failure. Classify the actual failure before deciding on recovery.
- **Claude quota hard gate (5h + weekly):** Before every Claude invocation (including
  plan audits, code audits, re-audits, and retries), the orchestrator must read
  the provider-reported usage in the rolling 5-hour Claude session window AND
  the rolling weekly window. This is a quota percentage, not an estimate from
  tokens, credits, elapsed time, process state, or exit status. The accepted
  preflight source is a configured `claude_5h_quota` adapter based on
  `claude -p '/usage' --no-session-persistence --permission-mode dontAsk
  --output-format json`; it must parse `Current session: <used>% used` and,
  when present, `Current week (all models): <used>% used`; return `used_5h_percent`,
  derived `remaining_5h_percent`, `used_weekly_percent`,
  `remaining_weekly_percent`, `observed_at` (UTC), `window=5h`, and
  `source_id`, and prove the probe was model-free
  (`num_turns=0`, `duration_api_ms=0`, `total_cost_usd=0`). A reading older than
  60 seconds is stale. Because reaching 85% **used** must stop Claude, the
  runnable condition is strictly `used_5h_percent < 85%`; at `>=85%`, Claude
  must not start or be retried. Because reaching 90% of the rolling weekly
  window must stop Claude for the week, the runnable condition additionally
  requires `used_weekly_percent < 90%` when the weekly reading is present; at
  `>=90%`, Claude must not start or be retried for the remainder of the week —
  this is a hard stop, not a wait-for-5h-reset. If the weekly reading is absent
  from `/usage`, the 5-hour gate alone applies (the adapter must record the
  weekly fields as null and note the absence in `reason`).
  If the adapter is missing, the reading is stale/unknown, or the source cannot
  be independently verified (the adapter must validate the provider response
  for the current authenticated account/org context, 5-hour window, and
  timestamp), fail closed and
  do not invoke Claude. The current `claude --version` and `claude auth status`
  checks are not quota sources; until this adapter returns a fresh, verified
  reading, Claude is unavailable under this policy. For this workspace, the
  concrete adapter is `D:\Taadaa\tools\claude-quota-preflight.ps1`; run it with
  the task ledger path immediately before every Claude process. Exit code `0`
  permits Claude, exit code `20` means the 85% used 5-hour boundary was reached
  and blocks Claude, exit code `22` means the 90% used weekly boundary was
  reached and blocks Claude for the rest of the week, and exit code `21` means
  quota status is unavailable and also blocks Claude. The caller must use the
  fresh record from that invocation; any record older than 60 seconds or reused
  from an earlier invocation is stale and blocks Claude. Every nearer consumer
  `AGENTS.md` inherits this gate and may not treat CLI/auth availability alone
  as Claude availability.
- Text inheritance is not the only enforcement layer. Every real Claude audit
  must run through
  `C:\Users\Kibe\.codex\skills\claude-final-audit\scripts\invoke-claude-final-audit.ps1`,
  which owns the fresh preflight and 30-second in-run monitor. Direct audit
  calls to `claude -p` are forbidden. The nine automation-core consumers must
  also keep the local `Claude Quota Hard Gate (Local Enforcement)` stub so an
  already-open task or missed ancestor cannot weaken the gate. Validate all
  copies and the wrapper with `D:\Taadaa\tools\check-claude-quota-policy.ps1`.
- Before creating a Claude process, record the quota decision in
  `D:\CodexRuntime\<project-id>\audit\claude-quota-ledger.jsonl` with at least
  `event`, `decision`, `used_5h_percent`, `remaining_5h_percent`,
  `used_weekly_percent`, `remaining_weekly_percent`, `observed_at`, `source_id`,
  and `reason`. Use
  `CLAUDE_QUOTA_THRESHOLD_REACHED` for `used_5h_percent >= 85%`,
  `CLAUDE_WEEKLY_QUOTA_THRESHOLD_REACHED` for `used_weekly_percent >= 90%`, and
  `CLAUDE_QUOTA_STATUS_UNAVAILABLE` for a missing, stale, or unverifiable
  reading. A preflight block is an explicit decision and must be recorded even
  though no Claude process was started. A mid-run threshold stop must use
  `CLAUDE_QUOTA_THRESHOLD_REACHED_DURING_RUN` with the same ledger fields and
  `phase=in_run`.
- A Claude audit expected to run longer than 60 seconds may start only when the
  caller-provided quota monitor (the preflight adapter alone is not a monitor)
  can poll at least every 30 seconds. If a poll reports
  `used_5h_percent >= 85%`, the orchestrator must stop at the next safe
  cancellation boundary; for `claude -p` this means cancelling the process tree
  promptly, verifying that it and its descendants exited, preserving read-only
  artifacts, and treating incomplete output as having no verdict. If this
  monitor/cancellation path is unavailable, do not start a long-running Claude
  audit.
- A quota-gate result of `>=85%` used in the 5-hour window or `>=90%` used in
  the weekly window also blocks every new Claude audit/retry for the affected
  window. An already-running audit is not an exemption: keep it only while
  polls remain below both limits; once a poll reaches a limit, stop it at the
  safe boundary and do not launch a replacement until the gate permits it.
- A quota-gate stop is treated as Claude CLI unavailable for audit routing. For
  a hard or ordinary code audit, advance to OpenCode, the cx
  workhorse. For an overall-plan audit, use the separate
  Hermes route (`deepseek-v4-flash` read-only plan ->
  `gpt-5.6-luna/max` plan audit), with the additional Sol gate for policy,
  core, live, and multi-repository tasks. A process exit, timeout,
  authentication result, worker state, or Claude self-report is not quota proof,
  and no quota-gated stop may be bypassed by a retry.
- When Claude CLI is blocked by the preflight quota gate before a process starts,
  preserve the quota artifact and advance exactly once through the active route:
  OpenCode free, then the cx workhorse. Do not run cumulative reviews or
  retry Claude CLI merely to obtain a quota error.
- OpenCode must be invoked by `D:\Taadaa\tools\invoke-opencode-audit.ps1`
  using a usable free model selected from the live 9Router catalog. If no free
  catalog entry is available, record the failure and advance to the cx
  workhorse; never cycle blindly.
- Label a completed result with the provider that actually ran:
  `AG_CLAUDE_AUDIT`, `CLAUDE_CLI_AUDIT`, `OPENCODE_AUDIT`, or `CX_AUDIT`. Never describe a fallback result as another provider's
  approval.
- When the `claude-final-audit` skill classifies an already-started Claude
  result as quota/session-limit exhaustion or otherwise produces no usable
   verdict, continue the same slot through OpenCode and cx. Keep the provider's actual
  label; do not relabel a fallback as Claude. A preflight quota-gate block
  follows the same route and must not start Claude merely to obtain a quota
  error.
- Never describe a fallback result as Claude approval. Audit findings are
  inputs, not completion proof. Reproduce relevant findings, inspect the final
  diff, and rerun the relevant tests before merge, push, or delivery.

### Vision/Attachment Audit Fallback

- If an auditor explicitly reports that its model does not support image input,
  classify the result as `VISION_CAPABILITY_UNAVAILABLE`. Text-only audit
  wrappers must not be relabeled to pretend that an image was delivered.
  Otherwise continue to the next active v5 route or local verifier.
- A vision model is useful only when the screenshot/image is actually attached
  through the audit transport and delivery is confirmed. A text-only audit
  wrapper does not make a local screenshot visible merely by changing a model;
  classify the result as `ATTACHMENT_NOT_DELIVERED` when delivery is unknown.
- Retry the read-only audit at most once per failed audit with an explicitly
  confirmed attachment-capable route; do not let a generic wrapper silently
  fall through to a text-only model. Record the actual audit label, model,
  verdict, scope, attachment/read-access limits, and never call it Claude
  approval. If no eligible route exists, record `VISION_MODEL_UNAVAILABLE` and
  continue through the next active v5 route/local verifier without blind
  candidate cycling.
- If the failure is an inaccessible external artifact path, missing attachment,
  or denied shell/filesystem access, classify it as `READ_ACCESS_UNAVAILABLE`
  (or `ATTACHMENT_NOT_DELIVERED`), not automatically as a vision failure.
  Changing models does not grant filesystem/device access; the main agent must
  perform the local artifact/verifier check and record that limitation.

## Repository-Specific Rules

- Keep provider, account, workbook, UI, deployment, and recovery-handler policy
  in the applicable repository's `AGENTS.md` or contract.
- `automation-core` owns shared app-neutral automation enforcement and its
  contract; consumer repositories own their adapters and consumer policy.
- Do not duplicate this whole file into every repository unless portability to
  another workspace or CI environment explicitly requires it.

### Target Serial Provenance

- Every live device target under `D:\Taadaa` must resolve the exact `machine` ->
  ADB serial pair from `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx`, sheet `Accounts`, using the `May` and `Device ID` columns.
- Duplicate source rows are valid only when they resolve to the same serial. A
  missing, conflicting, or caller-supplied serial that does not match the
  source workbook is `MACHINE_SERIAL_MISMATCH` and must fail before lock
  acquisition or any device/account action.
- Raw `adb devices` output, hardcoded serial constants, stale artifacts, and
  proxy mapping workbooks are not valid target-serial sources. Proxy workbooks
  may provide proxy values only.

### Shared Live Recovery Implementation Rule

This rule applies to every live automation repository under `D:\Taadaa`:

- The recovery rule is global/common across all live automation flows. A
  schedule is only a trigger/adapter that submits a target and failure
  signature to the shared per-target control plane; manual, CLI, watchdog, and
  event triggers use the same state machine, registry, artifact/verifier,
  lease/heartbeat, fail-closed gates, and configured cap.
- Provider, account, workbook, and business-flow policy remains in the
  consumer adapter. The common plane does not infer provider behavior from a
  schedule or from a worker/process status.

#### Gmail/Google state-transition evidence

- Không được mặc định kết luận Gmail/Google tự hết phiên vì để lâu, cũng không
  được mặc định kết luận scheduler/consumer takeover. Khi màn hình đổi (kể cả
  từ CAPTCHA sang logged-out/session-ended), thời gian chờ và màn hình mới chỉ
  là quan sát; nguyên nhân vẫn là chưa xác định nếu chưa có bằng chứng riêng.
- Ghi lại timestamp recapture, foreground/package, lock owner/lock id, bằng
  chứng runner/process liên quan và đường dẫn artifact. Chỉ phân loại
  takeover khi có evidence khớp từ lock/process; chỉ phân loại session expiry
  khi có tín hiệu Google/session rõ ràng, không chỉ vì màn hình đổi.
- Proof CAPTCHA đã chụp trước đó vẫn có giá trị cho state trước; không thay
  classification của proof đó chỉ vì recapture sau này hiện màn hình khác.
- Keep the target lock across recapture and the bounded cleanup/workbook
  update. If a lock had already been released, reacquire it through the
  guarded recovery path before any further device or data action.

- Recovery phải xử lý từng target, từng state và phải biết failure signature
  trước mỗi action.
- Mọi hành động làm thay đổi UI/device state (tap, back, reboot, mở/đóng
  surface, dismiss popup, retry) bắt buộc đi qua handler trong source/state
  machine hoặc primitive có contract của `automation-core`. Không dùng ADB/UI
  thủ công, tọa độ thủ công, hay thao tác ngoài script để làm target “qua” rồi
  báo success.
- Screenshot/UI dump hoặc kiểm tra read-only chỉ dùng để thu evidence và phân
  loại; không được biến chẩn đoán thành recovery thủ công.
- Chưa có handler thì kết quả là `NO_HANDLER_IMPLEMENTED`: dừng target, lưu
  evidence, bổ sung handler + regression test + recapture/verifier rồi mới retry.
- Handler phải bounded và fail-closed; chỉ `VERIFIED_SUCCESS` mới cho phép
  cleanup, workbook/data update hoặc release theo success. Worker exit không
  phải bằng chứng hoàn thành.
- Force-stop, relaunch, HOME hoặc soft reboot vẫn có thể là action của một
  recovery handler đã được phân loại, reserve và giới hạn rõ ràng. Nhưng khi
  handler đã hết lượt và target chuyển `FINAL_BLOCKED`/`HARD_STOP`, chỉ được
  recapture evidence và ghi handoff; tuyệt đối không chạy cleanup UI/device
  sau đó (không HOME, force-stop, relaunch, reboot hay tự đóng surface). Muốn
  recovery tiếp thì phải mở một recovery command/attempt mới có ủy quyền rõ.
- `automation-core` cung cấp enforcement/primitive app-neutral; repository
  consumer chịu trách nhiệm handler, selector và policy riêng của provider.

### Shared Parallel Runner Policy

- Mặc định mọi live runner trong các repository dưới `D:\Taadaa` phải dispatch
  toàn bộ target đã chọn đồng thời theo `max worker` của runner; áp dụng như
  nhau cho lượt vận hành bình thường và lượt recovery. Không được tự chuyển
  sang vòng lặp từng máy hoặc ép `MaxParallel=1` nếu người dùng không yêu cầu.
- Recovery song song không có nghĩa là bỏ qua state machine: mỗi target vẫn
  giữ device lock riêng, handler riêng, retry bound riêng và verifier riêng;
  lỗi của target này không được làm worker của target khác báo success.
- `MachineStartStaggerMs` chỉ được dùng khi policy/runner đã cấu hình để bảo
  vệ transport; stagger không được biến batch đã chọn thành recovery tuần tự.
  `max worker` là giới hạn đồng thời thực tế và phải được ghi trong report.
- Từ nay mọi live multi-machine runner bắt buộc random thứ tự máy ở mỗi run
  và dùng stagger random bounded giữa các lần start máy. Dùng primitive
  `automation_core.scheduler.machine_launch` hoặc adapter có cùng contract;
  ghi seed/order/delay vào evidence redacted. Áp dụng sau assignment, lock và
  preflight; không dùng rule này để reorder account hoặc thay UI settle/retry.
- Ngoại lệ: các repository phục vụ add-mail/register-gmail được miễn rule
  đồng thời này và tuân theo policy cục bộ của chúng. Ngoại lệ không áp dụng
  cho TikTok video, TikTok luot-nuoi-acc hoặc các repository live automation
  khác.
- Scheduler/worker exit vẫn không phải completion proof; từng target chỉ được
  kết luận sau `VERIFIED_SUCCESS` hoặc `FINAL_BLOCKED` theo recovery contract.

### Live Run Scope And Device-Lock Policy

Before dispatching a live multi-machine command, classify the user's scope
explicitly. The words below are operational policy, not merely labels in a
report:

- `FULL_SCOPE_TAKEOVER`: when the user says “chạy full máy”, “chạy all máy”,
  or equivalent, every configured machine in the requested range remains in
  the target accounting scope. Scope controls accounting, not retry
  eligibility. A previous `HANDOFF`, stale lock, or old `FINAL_BLOCKED` record
  is not an automatic exclusion from the report, but it does not authorize a
  new live attempt by itself. A target may be reclaimed or retried only when
  the versioned recovery contract independently permits a new signature,
  evidence-backed handler, target reservation, recapture, verifier, and any
  required same-target handoff gate.
- `EXCLUDE_LOCKED`: when the user explicitly says “all máy trừ các máy lock”
  or equivalent, the runner must inspect the current shared device-lock and
  handoff state before dispatch, exclude those targets, and leave their locks
  untouched. This mode's target result is `SKIPPED_LOCKED` or
  `EXCLUDED_LOCKED`, consumes no attempt, is never `FINAL_BLOCKED`, and is
  never success. Explicit lock exclusion takes precedence if a command
  contains both full-scope and lock-exclusion wording.
- In both modes, never overwrite or take over a lease with `owner_active=true`
  or an unverifiable owner lease. “Process PID still exists” is not by itself
  proof that the lease owner is active: an explicitly inactive `HANDOFF` or
  `blocked` lease with `owner_active=false` and a voluntary-yield marker may
  be reclaimed only through the guarded takeover path, after same-host
  liveness, lease identity, target reservation, bounded handler, recapture,
  and verifier checks. A lease left by another host is not locally reclaimable
  unless the shared-lock contract explicitly provides a cross-host recovery
  authority; otherwise report it as blocked. Never delete a lock file by hand.
- Scope mode does not change the versioned lock-retention lifecycle. A verified
  success may release through the normal owner path; a non-success target
  remains retained as `HANDOFF`/`blocked` when required by the core or consumer
  contract. The runner must not force-release a failed target merely because
  the full-scope command includes it.
- The selected scope mode, target list, lock decision, owner PID/project, and
  takeover or exclusion reason must be persisted in a redacted batch-level
  audit artifact, without turning a lock skip into a target business/result
  state. A preflight/lock skip with exit code 0 must never be mapped by a
  wrapper to `Verified=True`. A scheduler or worker process claiming a device
  is never completion proof and never overrides this policy.

## Scheduler Maintenance Authority

- The user authorizes Codex to stop any local scheduler, watcher, or batch
  runner that is using a runtime which must be repaired. Stop only the
  identified process tree, verify it has exited, complete offline validation,
  then restart the same configured service and report its verified state.
- This authority does not authorize live account, ADB, mailbox, workbook, or
  business actions beyond what the restarted scheduler normally performs.

### Narrow User-Authorized Worker Operation: Local Runtime Maintenance

- This is a bounded direct-worker operation, not a coordinator exception to
  the generic `SUBAGENT_RUNTIME_UNAVAILABLE`/no-direct-fallback rule. Explicit
  user authorization does not turn the coordinator into a live executor. Only
  the bound fresh, non-resumed, non-forked session-model worker
  (`deepseek-v4-flash`/`high` for Hermes, `gpt-5.6-luna`/`high` for Codex)
  direct worker may Stop, Install, and Start targets within the exact reserved
  scope; the coordinator may only reserve, inspect, and verify. When the
  user explicitly authorizes local runtime maintenance and identifies the
  exact scheduled tasks, process roots/descendants, built local wheel, and
  virtual environments, the coordinator must dispatch a fresh, pinned
  session-model worker through in-process Sub Agent/MCP or, only after the external
  CLI eligibility and gated-process contract are proven, that same role via
  the external CLI transport. Provider/model quota, authentication, policy
  denial, an unclassified 429, raw noninteractive exec, or an unproven gate
  is ineligible and remains fail-closed. That worker may perform only this
  bounded maintenance sequence between automation runs: stop the named
  scheduled tasks; stop only the confirmed descendants of those exact roots
  in leaf-to-root order; install the identified local wheel offline into the
  identified runtimes; verify the installed version, importability, module
  path, and `pip check`; and restart only the same configured scheduled task or
  service after the fail-closed startup gate has been proven.
- Before any side effect, the coordinator must create and maintain
  coordinator-owned pre-lease/checkpoint records and a pre-manifest containing
  the worker/session identity, exclusive scope, exact tasks, roots/descendants,
  runtimes, wheel, phase, heartbeat, and last progress. After each bounded
  Stop/Install/Start phase and at handoff, it must append the matching
  post-lease/checkpoint records and post-manifest. It must checkpoint preflight,
  patch, offline install/verification, and handoff, including explicitly
  skipped phases and reasons. Process exit, task state, or worker self-report
  is not completion proof.
- Process maintenance is limited to the user-named local scheduler, watcher,
  or batch-runner trees. A parent PID shared with other work, an
  owner-unresolved process, a PID outside the confirmed descendant tree, or a
  descendant whose parent-chain no longer proves ownership is fail-closed;
  never stop the shared parent or use a broad command/name kill. If any
  confirmed descendant remains after the bounded stop, do not install or
  restart.
- Wheel maintenance must use the exact identified Python interpreter and a
  built local wheel with `--no-index --no-deps --force-reinstall`; no editable
  install, network/index access, automatic rollback, or dependency upgrade is
  allowed. Verification must use `python -I`, check the exact expected
  distribution version, import the required modules, prove their paths are
  below that runtime's `site-packages`, and run `pip check`. Any failure keeps
  all named tasks stopped.
- Restart is allowed only when a pre-worker maintenance/quiescent or other
  fail-closed exclusion mechanism is artifact-proven to exclude every
  user-protected target before any worker/event/callback can wake, unlock,
  rotate locks, assign a proxy, dispatch, or run due work. A device/workbook
  lock is not an exclusion mechanism. Without that proof, keep every named
  task stopped and record `STARTUP_NOT_QUIESCENT`; do not call
  `Start-ScheduledTask`, invoke the scheduler/watcher directly, or retry. If
  startup produces an event/action or changes a target artifact, stop only the
  newly created confirmed tree and record
  `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH`.
- This worker operation does not authorize source-code, task-definition, consumer
  configuration, lock-file, policy, workbook, device, account, mailbox,
  ADB, proxy-assignment, business-flow, live-dispatch, recovery, or retry
  changes; does not use a lock as an exclusion; does not expand an attempt
  cap, lease, handler, or verifier gate; and does not become a second recovery
  control plane. It is limited to the exact maintenance actions above and
  requires redacted, inspectable evidence for every decision and result.

## Shared Device-Lock Ownership

- A device lock is a lease owned by the exact `host` + `pid` + `lock_id`; only
  that lease may release the lock or change its status.
- A scheduler, cleanup script, or another consumer must never delete, overwrite,
  or take over a prior script's lock, even when its PID is dead or its status is
  `handoff`. Normal runs leave failed/manual-needed locks retained.
- Same-project recovery must declare evidence-backed `SAME_PROJECT_RECOVERY`.
  Cross-consumer reclaim is allowed only through the `automation-core` guarded
  `FULL_SCOPE_TAKEOVER` path with explicit user full-machine authorization, a
  reason, and a redacted scope audit artifact.
- Active or unverifiable owners remain blocked. Direct lock-file mutation is
  not recovery. Full-scope reclaim changes lock authority only; it does not
  reset the versioned attempt cap or authorize a new retry without handler,
  recapture, and verifier proof.


## Merge / Cleanup Rule (bắt buộc, 2026-08-08)

Khi thực hiện merge nhánh về main hoặc dọn nhánh/tree quan trọng:
1. Lên PLAN bằng subagent TRƯỚC khi merge (không merge mù).
2. Worker thực thi merge/resolve.
3. Chạy AUDIT lại sau khi worker xong — lặp tới khi audit APPROVED mới xoá nhánh/tree.
4. Xoá nhánh chỉ sau bằng chứng absorbed/superseded (merge-tree/reflog/fsck).
## Giữ màn thật — Rule recovery BẮT BUỘC (user 2026-08-09)

Mọi lỗi UI/recovery: check màn thật (screencap + UI dump live của ĐÚNG máy/serial tại thời điểm hiện tại) TRƯỚC khi sửa/handle. KHÔNG tin artifact cũ (log cũ, XML dump cũ, screenshot/report session trước). Làm tới đâu verify tới đó: sau MỖI bước sửa → recapture + verify trên màn thật → mới sang bước tiếp.

<!-- WORKER-CHECKPOINT-TERMINATION-POLICY:START -->
## Worker checkpoint và gate dừng process (bắt buộc)

- Worker/background run phải ghi checkpoint và report riêng theo từng vòng: scope, thời điểm, phase, diff/test thật và điều kiện chờ kế tiếp; không chỉ ghi report ở cuối.
- Không suy luận code lỗi từ stdout đứng yên hoặc `exit code -15`. Chỉ được terminate khi có lỗi fatal/quota/transport machine-readable, hoặc sau ít nhất 3 quan sát cách nhau tối thiểu 30 giây (tổng >=90 giây) cùng chứng minh output/checkpoint/file mtime/process tree không tiến triển, không còn child code/test/tool hoạt động.
- Trước khi terminate phải lưu đầu/cuối log, process tree, mtime, `git status` và `git diff`; nếu worker có thể đã ghi code thì chạy hậu kiểm diff/test độc lập trước kết luận.
- Kill/exit bất thường phải phân loại `WORKER_TERMINATED_EXTERNALLY` hoặc `WORKER_EXITED_WITHOUT_REPORT`; không rollback mù, không tin report cũ, không chạy worker thay thế chồng. Reconcile exact scope và verifier độc lập trước replacement/commit.
- Quy tắc này bổ sung `agent-review-loops`; không cho phép bỏ qua gate riêng của repository hoặc mở rộng side effect/live scope.
<!-- WORKER-CHECKPOINT-TERMINATION-POLICY:END -->

## RULE 3 BƯỚC FIX LỖI UI (2026-08-10, workspace-wide + core)

- MỌI lỗi UI/vận hành (không phải Post/Delete/pay/OTP/switch) chạy đủ 3 bước trước khi kết luận: B1 ATX-kill → B2 force-stop+relaunch (tối đa 1) → B3 reboot máy (tối đa 1).
- Budget theo máy trong turn: 1 relaunch + 1 reboot/máy; các lần lỗi sau chỉ ATX-kill + coordinate fallback có evidence → fail thì MANUAL_REVIEW.
- Lỗi cùng chỗ sau đủ budget = thất bại; lỗi khác chỗ được chạy lại chuỗi nhưng vẫn trong budget tổng của máy.
- Handler đặc thù fail vì UI/dump phải route vào ladder, không dừng sớm.

## Canonical Script Reuse Rule (bắt buộc, 2026-08-12)

- Khi cùng một workflow/operation chỉ thay input data (ví dụ Tik1/Tik2/TikN, account row 1/2/N, machine list hoặc config path), PHẢI dùng lại canonical script/entrypoint đã chạy chuẩn.
- Chỉ thay tham số hoặc file dữ liệu qua CLI/config; KHÔNG tạo launcher/runner/script tạm mới và KHÔNG ghép shell loop/xargs để thay thế flow canonical.
- Nếu canonical script chưa nhận data variant cần thiết hoặc còn hardcode path cũ: sửa/build chính script đó theo hướng parameterized, giữ nguyên safety gate hiện có; ghi baseline rollback trước edit, test/preflight variant cũ + mới, audit/verify rồi mới chạy live.
- Chỉ tạo script mới khi workflow thực sự khác và user đã chốt rõ; phải ghi lý do vì sao entrypoint hiện tại không thể tái sử dụng.
- Trước launch phải ghi evidence gồm canonical script path và data path/row đã chọn; việc đổi data không được bypass lock, account/target verifier, confirmation, recovery hoặc report contract.

## AUDIT / PLAN / REVIEW ROUTING MANDATE (chốt 2026-08-18, ALL repo)
- TUYỆT ĐỐI CẤM dùng delegate_task hoặc Flash/Worker để làm PLANNER / AUDITOR / REVIEWER.
- CẢ 3 VIỆC (PLAN, CODE REVIEW, AUDIT) ÁP DỤNG CHUNG 1 KHUNG CHUẨN KỊCH TRẦN REASONING:
  1. Cấp Thường / Vừa (UI, popup, video gate, feature 1 repo, helper):
     - 9Router HTTP API (http://127.0.0.1:20128/v1/chat/completions) với combo 'plan-review' (gpt-5.6-terra -> ag/claude-opus-4-6-thinking -> cmc/deepseek/deepseek-v4-pro) kèm reasoning kịch trần ("reasoning_effort": "max" / "high").
  2. Cấp Khó / Core / Nhạy cảm (Architecture, Scheduler, Manifest validation, Hashing, State machine, Lock, Recovery, Multi-repo):
     - Ưu tiên 1: 9Router HTTP combo 'plan-review-hard' (gpt-5.6-sol) kèm reasoning kịch trần ("reasoning_effort": "ultra" / "max").
     - Fallback (khi Sol lỗi/hết quota/429/404): Gọi Claude CLI print mode trực tiếp với model Opus 5 và reasoning medium ('claude -p "<prompt>" --model opus --effort medium --allowedTools "Read,Bash(git *)"'). CẤM gọi `--effort max` vì cạn kiệt session limit 5h.
- Request body HTTP bắt buộc: tools: [], tool_choice: 'none', stream: false, Authorization: Bearer $NINEROUTER_API_KEY.
## 13. PREFLIGHT SCHEDULE CHECK (Bắt buộc trước mọi batch chạy tay/live — user chốt 2026-08-18)
Trước khi chạy bất kỳ batch tác vụ nào trên farm (Reg TikTok, Hotmail login, Add mail khôi phục, Register Gmail, Upload video, Reconcile...):
1. **TỰ ĐỘNG KIỂM TRA LỊCH CRON NUÔI ACC:** Agent BẮT BUỘC tự động kiểm tra manifest nuôi acc (`D:\Taadaa\runtime\kibe\cron-state\manifests\<ngày>\active_manifest.json` qua skill `farm-schedule-preflight-check`) TRƯỚC KHI KHỞI CHẠY.
2. **KHOẢNG ĐỆM AN TOÀN ≥ 1 TIẾNG:** Chỉ được chọn và chạy trên các máy hoàn toàn rảnh trong suốt thời gian chạy batch và **cách ca nuôi acc kế tiếp tối thiểu 60 phút**.
3. **CẤM CHẠY TRÙNG MÁY:** Tuyệt đối không khởi chạy batch trên các máy đang trong ca nuôi hoặc sắp vào ca < 60 phút.
4. **USER CHỈ CẦN BẢO "CHẠY SCRIPT XXX" → AGENT TỰ CHECK LỊCH RỒI CHẠY:** User không cần phải nhắc "kiểm tra lịch", agent tự động check máy rảnh -> lọc danh sách máy an toàn -> chạy. Khi gặp lỗi máy nào -> dừng máy đó, chụp ảnh gửi user, chỉ lock khi user yêu cầu để debug sau.

## 14. QUY TẮC CHỐT PHIÊN TỰ ĐỘNG BẮT BUỘC (User chốt 19/08/2026 — Áp dụng ALL repo)

Khi user hỏi "chốt phiên được chưa", "xong chưa", "đã xong chưa" hoặc yêu cầu đóng phiên, Agent **TUYỆT ĐỐI KHÔNG ĐƯỢC TRẢ LỜI "XONG/CHỐT ĐƯỢC" BẰNG MIỆNG** khi chưa tự động hoàn tất đầy đủ chuỗi quy trình dưới đây:

0. **BƯỚC 0 (GATE 0) — BẮT BUỘC LIVE CANARY TEST TRÊN MÁY LỖI (KHI FIX LỖI FARM/DEVICE):**
   - Khi phiên làm việc có sửa code tính năng/lỗi liên quan đến thiết bị/farm hoặc logic runtime: **BẮT BUỘC CHẠY TEST LIVE THỰC TẾ (CANARY TEST) TRÊN TARGET BỊ LỖI TRƯỚC TIÊN.**
   - Lệnh chạy canary: `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts
un-feed-session.ps1" -Machines <id> -Row <row> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
   - Phải kiểm tra log.jsonl / summary.txt đạt `final_status: success`, `stop_reason: ""` thực tế mới được chuyển sang Bước tiếp theo. CẤM nhảy cóc nếu chưa chạy Live Canary.

0.5. **BƯỚC 0.5 (GATE 0.5) — BẮT BUỘC CẬP NHẬT CASE FIX & ANTI-PATTERN CATALOG (KHI SỬA FARM AUTOMATION):**
   - **Tài liệu quy chuẩn:** `docs/farm-automation-cases.md`.
   - **Phạm vi áp dụng:** MỌI task có can thiệp/sửa đổi code hoặc logic liên quan đến farm (UI, Popup, Keyboard, Switcher, Cron, Sync, Cohort, Device Lock, ADB, Follow, Upload, Reg, Mail...).
   - **Nội dung bắt buộc:** Phải ghi rõ (1) Vị trí áp dụng, (2) Nguyên nhân gây lỗi / Anti-Pattern, (3) Giải pháp chuẩn / Case Fix thực tế. Khóa chặt bằng focused test trong test suite.
   - **Điều kiện chặn:** Nếu phiên có sửa logic farm mà CHƯA có file diff cập nhật `docs/farm-automation-cases.md` → **CẤM Model Review, CẤM Commit và CẤM Push.**

1. **BƯỚC 1 — GỌI REVIEW MODEL ĐỘC LẬP (9Router HTTP API):**
   - Lấy diff commit/working tree gửi sang model `plan-review` qua 9Router (`http://127.0.0.1:20128/v1/chat/completions`).
   - Quét toàn bộ Security risks, Logic errors, Edge cases.
   - Nếu reviewer phát hiện lỗi logic / bug -> Phải fix và chạy lại test 100% PASS trước khi đi tiếp.

2. **BƯỚC 2 — COMMIT LOCAL ĐÚNG SCOPE VÀ DỌN TREE:**
   - Commit local exact-scope phần code fix + test liên quan.
   - Tự động kiểm tra `git worktree list` và `git branch -a`.
   - Nếu có các nhánh worktree/branch con -> Tự động merge về nhánh chính (`main`/`master`) và xóa gọn các worktree/branch tạm sau khi merge.

3. **BƯỚC 3 — PULL-BEFORE-PUSH VÀ PUSH LÊN REMOTE:**
   - Chạy `git pull --rebase origin <main/master>`.
   - Đảm bảo local đồng bộ sạch sẽ với remote.
   - Chạy `git push origin <main/master>`.

👉 **Báo cáo hoàn tất cuối cùng PHẢI có đủ 5 bằng chứng:**
- (a) Bằng chứng Live Canary Test trên máy lỗi thật (`final_status: success`).
- (b) Verdict của Model Review độc lập (`APPROVED`).
- (c) Kết quả kiểm thử test suite (N/N tests pass 100%).
- (d) Trạng thái cây nhánh/worktree đã merge sạch.
- (e) Commit SHA và log push thành công lên remote `origin`.

## CLOSE-SESSION HARD TRIGGER
Các câu “chốt phiên”, “chốt phiên đi”, “đóng phiên”, “kết thúc phiên”, “xong phiên chưa” là **lệnh thực thi closeout**, không phải yêu cầu gửi summary. Bắt buộc load `session-close-protocol` và chạy: review độc lập `APPROVED` → kiểm tra branch/worktree/conflict → dọn đúng file tạm do session tạo → commit đúng scope → fetch/pull --rebase → push + xác minh remote SHA. Thiếu bất kỳ gate nào chỉ được báo `BLOCKED_AT_<STEP>`; cấm nói “đã chốt/xong” bằng miệng.

## 🛑 QUY TẮC AN TOÀN BẬT / TẮT CRON & REG COOLDOWN (User chốt 2026-08-26)
- **CẤM PAUSE CRON KHI CHẠY TAY / RECOVERY:** Mọi cron (nuôi acc, feed, reg đêm) đã có cơ chế tự lọc `device_lock` để skip các máy đang bận và chạy tiếp các máy rảnh còn lại. Tuyệt đối KHÔNG pause cron vì sẽ làm chết các watchdog giám sát an toàn và script tự động giải phóng lock quá hạn (TTL 2h).
- **MỖI MÁY REG TỐI ĐA 1 LẦN/NGÀY:** Máy đã reg `SUCCESS` hôm nay tự động nhận cooldown tới ngày hôm sau, detector tự động skip không bao giờ lập batch lại. Lỗi/PENDING không cooldown.
- **RECOVERY ĐÚNG DANH SÁCH LỖI:** Tuyệt đối không tự ý mở rộng phạm vi chạy lại toàn bộ batch pending khi được yêu cầu recovery.

## CANARY_CLASSIFICATION_RULE_2026_08_27

This rule overrides older generic wording that makes live canary mandatory for every code or farm fix.

1. Classify the session from the opening user request and evidence, not from the repository name alone.
2. `LIVE_CANARY_REQUIRED` applies only when at least one condition is true:
   - the task explicitly names a machine, row, serial, or device target;
   - the user explicitly requests real-device validation; or
   - the opening session includes user-provided incident evidence (screenshot, alert, or log) that identifies a machine/target and a concrete runtime failure, and the user is asking to fix or debug that incident. Example: `[MÁY 4] DỪNG PHIÊN` + account + `profile verification`/`camera-recovery-failed` identifies machine 4 as the incident target.
3. When incident evidence qualifies, resolve machine → row → serial through the canonical mapping before running anything live. If mapping cannot be proven, report `TARGET_RESOLUTION_UNPROVEN`; never guess another machine, row, or serial.
4. `CANARY_NOT_APPLICABLE` applies to code-only, refactor, general-flow, unit-test, mock-test, or static-analysis work when the current task has no explicit live target, no real-device request, and no qualifying opening-session incident evidence. Proceed with focused semantic verification instead of a device canary.
5. A generic screenshot or log containing TikTok, farm, or device UI without an identified incident target and concrete runtime failure is not enough to trigger a canary.
6. Never infer a live target from a repository name, config filename, workbook, historical artifact, nearby machine file, or an old canary result. If a canary is required, run only the exact resolved target; do not expand to a batch or another machine without explicit authorization.


## 🛑 STRICT INCIDENT EVIDENCE LIVE CANARY RULE (User chốt 28/08/2026 — All Repos)
Khi user gửi ảnh/screenshot màn hình lỗi, báo máy/UI bị kẹt, hoặc gửi incident alert:
1. BẮT BUỘC nhận diện máy/serial hiện trường (hoặc tra cứu từ workbook Tik1/Tik2/taikhoan_run_safe).
2. Khi fix xong (dù fix ở consumer repo hay automation-core): BẮT BUỘC CHẠY LIVE CANARY trên đúng máy/hiện trường đó (hoặc verify trực tiếp qua ATX / screencap / dump UI).
3. TUYỆT ĐỐI KHÔNG ĐƯỢC tự ý gán `CANARY_NOT_APPLICABLE` và chốt phiên khi đầu phiên có ảnh hiện trường lỗi thực tế mà chưa kiểm chứng đóng popup / clear lỗi trên máy thật.
4. NGHIỆM THU BẰNG CHỨNG BẮT BUỘC (EVIDENCE & MEDIA GATE): Sau khi Canary hoặc chạy task hoàn tất, BẮT BUỘC chụp ảnh screencap màn hình máy thật và đính kèm thẻ `MEDIA:<path_anh>` vào báo cáo kết quả gửi User. Thiếu thẻ `MEDIA:` = VI PHẠM GATE NGHIỆM THU, CHƯA ĐƯỢC PHÉP CHỐT PHIÊN.


## 🛑 TOÀN DIỆN VẬN HÀNH: ĐỊNH NGHĨA BẰNG CHỨNG READ-BACK & AN TOÀN THIẾT BỊ (ALL REPOS & TASKS)
Mục này áp dụng cho MỌI task tác động lên thiết bị, mạng, cấu hình hoặc DB (không chỉ riêng Incident Farm):
1. ĐỊNH NGHĨA READ-BACK CHUẨN: Read-back BẮT BUỘC là lệnh ĐỌC độc lập (tách rời khỏi lệnh ghi), chạy trên chính thiết bị đích sau khi thay đổi, trích xuất raw stdout so sánh rõ giá trị [KỲ VỌNG] ↔ [THỰC TẾ]. CẤM dùng echo của lệnh ghi, CẤM đọc file config local thay cho thiết bị, CẤM tự tóm tắt bừa.
2. SUBAGENT SELF-REPORT = 0 BẰNG CHỨNG: Lời worker/subagent tự báo "done/success/đã hoàn tất" KHÔNG PHẢI là bằng chứng. Coordinator BẮT BUỘC phải tự thực thi lệnh đọc lại hoặc đọc artifact có file path + timestamp mới tạo.
3. BẰNG CHỨNG THEO THUỘC TÍNH: Bằng chứng phải quan sát trực tiếp đúng thuộc tính đang khẳng định (UI -> screencap/OCR; Network/Service/Config -> Read-back stdout từ máy đích; DB -> SELECT read-back).
4. KIỂM TRA LƯU BỀN (PERSISTENT CONFIG): Với thiết bị mạng / router, trước khi reboot hoặc can thiệp nguồn/cáp, BẮT BUỘC read-back kho lưu bền (OpenWrt: `uci changes` rỗng VÀ đọc file cấu hình trực tiếp `/etc/config/*`; Cisco/Switch: `show startup-config`) chứng minh cấu hình còn nguyên sau khởi động lại.
5. CHỈ ĐẠO THAO TÁC VẬT LÝ & NGOẠI LỆ CỨU HỘ:
   - Bình thường: Chỉ được đề xuất khi trạng thái đã đạt `VERIFIED_SUCCESS` kèm bằng chứng đối soát.
   - Ngoại lệ Cứu hộ (`RESCUE_NEEDED`): Khi thiết bị mất kết nối hoàn toàn không thể read-back được, ĐƯỢC PHÉP đề xuất thao tác vật lý nhưng BẮT BUỘC khai báo rõ nhãn `STATE: UNVERIFIED / RESCUE_NEEDED`, nêu rõ nguy cơ rủi ro (mất config chưa lưu, chập mạng) và hướng dẫn rollback. TUYỆT ĐỐI CẤM trình bày như bước tiếp theo của một việc "đã xong".


## 🎯 QUY CHUẨN LIVE CANARY THEO TỪNG REPO / SCRIPT (User chốt 28/08/2026)
Live Canary BẮT BUỘC phải kích hoạt bằng **Runner chính thức của repo**, TUYỆT ĐỐI CẤM dùng ad-hoc script/tap tay thay thế:
1. **Với `tiktok-luot nuoi acc` (Feed):** Chạy runner với `--max-swipes 2` (hoặc `--recovery-test-swipes 2`) + `--cleanup-on-stop` → Vượt qua popup → Thực hiện đủ 2 swipes → Tự động dọn dẹp về Home → Giải phóng lock.
2. **Với các script nghiệp vụ khác (`Tiktok_Reg`, `tiktok-follow`, `Tiktok-video`, `Hotmail`, `tiktok-add-bao-mat-f2a`, `register gmail`...):** Chạy đúng runner của repo trên máy target → Vượt qua đúng điểm nghẽn/lỗi → Chạy nốt hoàn thành trọn vẹn luồng công việc của script (Task Completion) → Tự động cleanup và giải phóng lock.
3. Chỉ khi runner chạy hoàn tất từ A-Z đạt `status: success` mới được coi là Pass Gate 0 và chuyển sang Model Review / Chốt phiên.

<!-- HERMES-DIRTY-SCOPE-RULE-20260831:START -->
## Dirty-tree scope rule (mandatory)

A dirty worktree is **not** a repository-wide blocker. The current task contract's exact allowlist is authoritative.

- Before any action, split paths into `IN_SCOPE` and `OUT_OF_SCOPE` using the current allowlist. Unrelated staged/unstaged files, unrelated test/build processes, and unrelated failures are `OUT_OF_SCOPE`: ignore them, do not inspect, revert, reset, unstage, stage, wait on, or report them as blockers.
- A staged or unstaged file inside the allowlist is not automatically a conflict. Staged state, an old mtime, or a non-empty `git status` does not prove another writer owns the requested hunk.
- Continue when dirty hunks are distinct and the requested hunk is unowned. Declare `SCOPE_CONFLICT` only when the same allowlisted file/overlapping region changes during the current ownership window, an active writer owns the requested region, or ownership cannot be separated safely. Record path, region, before/after hash or content, and timing evidence.
- `SCOPE_DRIFT` means this agent/worker changed outside its own allowlist; pre-existing unrelated dirty paths are not scope drift. Do not convert foreign dirt into a blocker.
- Verification and reporting must remain path-scoped. Report `unrelated dirty preserved`, `overlapping dirty/conflict`, and `agent-caused scope drift` as separate states.

<!-- HERMES-DIRTY-SCOPE-RULE-20260831:END -->


## Quy Tắc Định Tuyến Log Theo Máy & Chống Timeout Khi Điều Tra Lỗi (Bắt buộc)

- **Định tuyến log O(1) từ Alert Banner [MAY N]:**
  Khi nhận ảnh/screenshot hoặc thông báo có thanh đỏ `[MAY <N>]` (hoặc nêu đích danh Máy N):
  1. Tra ngay Serial của máy từ `D:\Taadaa\machine-config\kibe.yaml` theo số máy `<N>`.
  2. Truy cập THẲNG vào thư mục log/artifact riêng của máy đó:
     - `D:\Taadaa\runtime\kibe\live\<ngày>\*\machines\machine_<N>\`
     - `D:\Taadaa\runtime\kibe\artifacts\alert_machine_<N>.png`
     - Lấy XML/screenshot hiện trường trực tiếp: `adb -s <serial> ...`
  3. **TUYỆT ĐỐI CẤM** chạy lệnh tìm kiếm quét mù đệ quy (`grep -rn`, `find`) trên toàn bộ thư mục `.ai-runs/` hoặc `D:\Taadaa\runtime\` gây tắc nghẽn I/O và treo timeout 900s.

- **Quy Tắc Timeout & Focused Test:**
  - Khi test code/fix bug, **CHỈ chạy focused test** theo đúng file/class/chức năng vừa sửa (thời gian chạy < 30s).
  - **CẤM chạy full test suite** toàn repo (hàng nghìn test) trong các lượt debug hoặc chốt phiên gây nghẽn tiến trình.
  - Các lệnh terminal dài phải đặt timeout hợp lý (30-60s) để fail-fast, không để lệnh treo quá 120s.

## Quy Tắc GPMLogin (API v3 Port 19995) & Automation Trình Duyệt

- **Cấu hình Proxy & Bảo vệ rò rỉ IP:**
  1. Gán `raw_proxy` trực tiếp vào profile trước khi start. Proxy lỗi/auth 407 = GPM KHÔNG start profile để chống leak IP thật.
  2. CẤM MikroTik farm S7 (M9:5111, M41:5103, M42:5104, M60:5126, M70:5138, M71:10006). Mỗi máy dùng đúng port proxy S7 riêng biệt.
  3. Kiểm tra CDP live và xác thực session trước khi thực hiện thao tác nhạy cảm.
- **Quy tắc thực thi Script & Tránh Treo:**
  1. Script Python dài BẮT BUỘC dùng `write_file` ra đĩa rồi chạy, TUYỆT ĐỐI CẤM bash heredoc (`python << 'PYEOF'`) vì dễ lỗi syntax/escape và treo subshell.
  2. Không điều khiển browser bằng LLM từng turn đơn lẻ (dễ crash/timeout do network drop); BẮT BUỘC viết script Python tự động độc lập chạy trong subagent hoặc background runner.
  3. Giới hạn đồng thời: tối đa 3-4 profiles song song, stagger 10-15s giữa các profile để tránh nghẽn CDP và quá tải tài nguyên hệ thống.
  4. Google UI tiếng Việt: dùng href pattern language-agnostic (`a[href*="signinoptions/twosv"]`, `a[href*="two-step-verification/authenticator"]`). Vượt qua challenge mật khẩu bằng cách đọc password từ file Excel tương ứng.
  5. Luôn bọc trong `try ... finally` để dừng profile qua GPM API và kill tiến trình chrome mồ côi sau mỗi lượt.

<!-- ANTI-OVERENGINEERING-BUDGET-GATE:START -->
## 🛑 QUY TẮC BẮT BUỘC: CHỐNG OVER-ENGINEERING & PHÂN TẦNG NGÂN SÁCH TASK (ALL WORKERS)
Áp dụng cho toàn bộ sessions (Coordinator & Worker) trên các repo Taadaa Phone Farm:

1. **PHÂN TẦNG NGÂN SÁCH THEO ĐỘ PHỨC TẠP TASK (DYNAMIC BUDGET):**
   - **Tier 1 (Hotfix / Lỗi cục bộ - sửa 1 hàm, format text, regex, cú pháp, selector UI, timeout):** Tối đa **15–20 tool calls**, xong trong **10–15 phút**. CẤM viết test mới, chỉ py_compile hoặc 1 assert tối thiểu.
   - **Tier 2 (Flow Bug - kẹt bước flow, popup mới, lệch luồng điều hướng, retry loop):** Tối đa **25–40 tool calls**, xong trong **20–30 phút**. Sửa đúng flow, chạy test runner của flow.
   - **Tier 3 (Major / Refactor lớn - sửa kiến trúc core, đa repo, đổi DB/workbook/socket ATX):** BẮT BUỘC chia thành các **Phase Milestone độc lập** (mỗi phase < 30 tool calls). CẤM chạy 1 lèo 100+ turns trong bóng tối.

2. **QUY TẮC CHECKPOINT (CHỐNG CHẠY MÙ TRONG BÓNG TỐI):**
   - Khi chạm mốc **25-30 tool calls** mà chưa xong, Worker BẮT BUỘC tạm dừng xuất báo cáo Checkpoint: (a) Đã tìm thấy gì? (b) Đã sửa được gì? (c) Khúc mắc còn lại là gì? -> Chờ định hướng, CẤM tự ý chạy tiếp hàng trăm turns.

3. **CẤM TEST INFLATION & SIMULATION THỪA MỨA (ÁP DỤNG CHO MỌI TIER):**
   - **CẤM TỰ VIẾT TEST SUITE ĐỒ SỘ:** Không tự ý đẻ file test mới hay viết hàng loạt test cases khi chưa được yêu cầu.
   - **CẤM CHẠY SIMULATION / MONTE CARLO:** CẤM viết script chạy lặp hàng ngàn lần (vd sinh 10.000 username đo entropy).
   - **CẤM TẠO PROBE SCRIPT TẠM TRONG %TEMP%:** Kiểm chứng chỉ dùng python -c "..." hoặc test file hiện có.
   - **CẤM CHẠY LẠI FULL TEST SUITE NHIỀU LẦN:** Sửa module nào chỉ test module đó hoặc py_compile.

4. **RÀNG BUỘC KHI COORDINATOR DISPATCH WORKER:**
   - Coordinator khi gọi delegate_task BẮT BUỘC gắn nhãn Tier và budget tương ứng (Tier 1: max 15-20 calls; Tier 2: max 25-40 calls; Tier 3: chia phase).
<!-- ANTI-OVERENGINEERING-BUDGET-GATE:END -->

## Quy tắc Quản lý & Vận hành Tools dùng chung (Single Source of Truth)
1. **Runtime (Chạy thực tế):** Toàn bộ tool vận hành chung (`buy_hotmail.py`, `inspect_machine.py`, `install_farm_apks.py`...) BẮT BUỘC đặt tại `D:\Taadaa\tools\` (đồng bộ tự động qua OneDrive giữa Kibe và Admin). Mọi quy trình farm gọi trực tiếp qua `python D:/Taadaa/tools/<tool_name>.py` hoặc import từ `D:\Taadaa\tools\`.
2. **Quản lý mã nguồn (Git):** Mã nguồn các tools dùng chung được quản lý tập trung DUY NHẤT tại repo `AI-Tools` (`D:\Taadaa\AI-Tools\tools\`). CẤM sao chép / nhân bản sang thư mục `tools/` của các repo khác (`Hotmail`, `Tiktok_Reg`...).
3. **Phân quyền Master/Client:** Kibe là Master sửa/ghi file tool tại `D:\Taadaa\tools\`, máy Admin chỉ thực thi (Read-Only) để chống xung đột file sync (conflicted copy) trên OneDrive.

## 🔒 ANTI-OVER-ENGINEERING — HARD ENFORCEMENT (locked 2026-09-07 by Claude Opus High)
Sự cố tham chiếu: proxy08 502 → Coordinator bỏ task 2FA của user 3h20p để tự build mobiproxy_auto_healer.py (398 dòng) + watchdog + cronjob. FAIL.

1. **PRIMARY TASK PRIMACY (Khóa chết mục tiêu chính):** Lệnh user = PRIMARY_GOAL bất khả xâm phạm. Phát hiện dọc đường = INCIDENTAL, cấm thăng cấp thành task, cấm rẽ nhánh.
2. **ZERO SECONDARY TOOL-BUILDING (Cấm tự dựng đồ):** Không có lệnh tường minh = cấm tạo tool/daemon/CLI flag/cronjob/sửa hạ tầng. Muốn build phải hỏi & chờ duyệt.
3. **O(1) UNBLOCK ONLY (<60s):** Hạ tầng nghẽn chỉ fix O(1). 1 lần không thông = DỪNG, báo 1 dòng, chờ lệnh. Cấm mở rộng scope để "fix triệt để".
4. **USER-CENTRIC WALL-CLOCK (Đồng hồ tính từ user):** Latency tính từ timestamp tin nhắn user, không phải subprocess runtime. CẤM ngụy biện "process chỉ chạy 7 phút".
5. **DIRECT MINIMAL ACTION (Xử lý trực diện):** Việc trước mặt làm đường ngắn nhất, thao tác tối thiểu. Không phân tích thừa, không vẽ flow.



# INVARIANT POLICY: ZERO HARDCODED TIME & EVENT-DRIVEN WATCHDOG (TU VAN CLAUDE CLI)
- RULE #0 (ZERO HARDCODED TIME): Coordinator TUYET DOI CAM tu dat bat ky khung gio co dinh nao (13h, 21h, 23h30...) cho tac vu can thiep thiet bi farm (logout nick ky sinh, sua tai khoan, adb). Bat ky hanh vi hen gio co dinh hay doan mo khung gio ranh deu bi CAM TUYET DOI.
- RULE #1 (NO TOUCH WITHOUT PER-DEVICE LOCK): Moi tac vu can thiep thiet bi BAT BUOC phai check per-device lock (machine_N.lock.json). Neu may dang bi lock boi ca chinh -> CAM DUNG VAO THIET BI.
- RULE #2 (SOURCE OF TRUTH LA DEVICE STATE): Coordinator CHI DUOC PHEP phan ung theo State thuc te (live lock files, end_time run_manifest, 0 lock). TUYET DOI KHONG SUY LUAN, UOC DOAN THOI GIAN HOAN THANH.
- RULE #3 (SESSION EXCLUSIVITY): Cac ca chay chinh (FEED_SESSION, 2FA_SESSION, REG_GMAIL, REBOOT) la BAT KHA XAM PHAM. CAM chen ngang khi may dang dinh ca chinh.
- RULE #4 (EVENT-DRIVEN WATCHDOG ONLY): Khi user yeu cau 'canh may ranh thi lam', BAT BUOC tao Watchdog polling dinh ky (1-2 phut) check lock rieng cua may do. May vua ranh (giai phong lock) la VAO VIEC NGAY TUC THI, lam xong dung ngay va bao cao.

## Kỷ luật chống Polling tiến trình nền (Event-driven Wakeup & Zero Context Bloat)
- CẤM TUYỆT ĐỐI POLLING TIẾN TRÌNH NỀN: Cấm tự viết vòng lặp `sleep`, `ps`, `pgrep`, `top` hoặc liên tục gọi lệnh check trạng thái chờ tiến trình nền. Mỗi turn polling gây lãng phí lớn token context và phình context session.
- MỌI TÁC VỤ CHẠY LÂU (>30s như batch render, upload, batch reg, test suite, DB sync): BẮT BUỘC dùng `terminal(background=True, notify_on_complete=True, timeout=...)` hoặc dispatch qua `delegate_task`.
- KHI ĐÃ BACKGROUND/DISPATCH: Kết thúc lượt trả lời ngay hoặc thực hiện việc độc lập khác để harness tự động đánh thức (wake-up) khi có output hoàn thành.
- PHÒNG NGỪA SILENT CRASH (GATE 6 — EVIDENCE-FIRST SPEECH GATE):
  + Cổng phát ngôn State Machine: `DISPATCHED → RUNNING → UNVERIFIED → VERIFIED_SUCCESS | FAILED` (đây là gate kiểm soát phát ngôn, không thay thế recovery state machine).
  + Khi nhận wake-up hoặc tool return: CẤM TUYỆT ĐỐI suy diễn thành công chỉ qua exit code hoặc status='dispatched'.
  + BẮT BUỘC ĐỐI SOÁT BẰNG CHỨNG THỰC TẾ THEO ĐÚNG MỤC "TOÀN DIỆN VẬN HÀNH: ĐỊNH NGHĨA BẰNG CHỨNG READ-BACK" Ở TRÊN:
    * Thiết bị có màn hình (S7/UI/Browser): Bắt buộc có screencap/OCR ảnh thật `MEDIA:<path_anh>`.
    * Thiết bị không màn hình (Router/Server/Network/Terminal/DB): Bắt buộc có Log Đọc Lại (Read-back stdout độc lập từ chính thiết bị đích).
    * Subagent/Worker báo "done" = 0 bằng chứng, Coordinator bắt buộc tự chạy lệnh đọc lại hoặc kiểm tra artifact.
  + MỌI PHÁT NGÔN BÁO CÁO KHI CHƯA ĐẠT VERIFIED_SUCCESS:
    * BẮT BUỘC giữ nguyên trạng thái `UNVERIFIED` hoặc `RUNNING`.
    * CẤM TUYỆT ĐỐI mọi câu từ khẳng định hoặc ngụ ý đã hoàn thành ("đã nạp", "đã xong", "đã fix", "ok rồi", "xong phần config").
    * Thao tác vật lý: Tuân thủ nghiêm ngặt mục 5 ở trên (chỉ khi `VERIFIED_SUCCESS` hoặc ngoại lệ cứu hộ `UNVERIFIED / RESCUE_NEEDED` kèm cảnh báo rủi ro). CẤM CHỈ ĐẠO User thực hiện thao tác vật lý như bước kế tiếp của một việc "đã xong" khi chưa đối soát.


## 🔒 FARM-ASSET-001 — BẢO VỆ TÀI SẢN NICK TIKTOK & CẤM TỰ Ý LOGOUT (CRITICAL)
1. **Tài sản:** Mọi nick TikTok đang đăng nhập trên máy farm là TÀI SẢN DOANH NGHIỆP CỦA USER.
   Agent CẤM TUYỆT ĐỐI tự gán nhãn "nick lạ / nick rác / nick test" để làm căn cứ xử lý.
2. **Logout duy nhất được phép:** Nick KÝ SINH — username có đúng 1 dòng trong Excel và `owner_stt != current_stt`, username đã được OCR readback xác nhận (User đã phê duyệt dọn dẹp).
3. **CẤM LOGOUT trong mọi trường hợp khác:**
   - Nick chính chủ (`owner_stt == current_stt`);
   - Nick KHÔNG CÓ trong Excel -> BẮT BUỘC coi là DATA DESYNC (Lệch dữ liệu / Sót ghi nhận);
   - Nick trùng nhiều dòng / owner_stt rỗng / Excel lỗi;
   - Chưa OCR hoặc OCR không chắc chắn.
   - CẤM luôn các hành vi tương đương: `pm clear` TikTok, gỡ app, xóa cache phiên.
4. **Gặp nick không có trong Excel:** Đóng băng máy (dừng automation) -> Chụp ảnh & OCR -> Ghi `unrecorded_assets_incident.jsonl` -> Truy vết backup Excel và log Reg/nuôi -> BÁO CÁO USER & CHỜ CHỈ ĐẠO. Tuyệt đối không có timeout nào cho phép tự xử lý.
5. **Code Guard:** Mọi logout BẮT BUỘC phải đi qua `logout_guard.py` và `do_logout_account.py`. Cấm viết đường logout khác. Cấm bắt `LogoutForbidden` rồi bỏ qua.

<!-- CREDENTIAL-ISOLATION-POLICY:START -->
## KỶ LUẬT ĐỘC LẬP CREDENTIAL (CẤM ĐÈ PASS CHATGPT/TIKTOK BẰNG PASS MAIL)
- **Độc lập dịch vụ:** Hotmail/Gmail, ChatGPT, và TikTok là 3 hệ thống/dịch vụ hoàn toàn riêng biệt.
  * Cột 4 (`PASS`): Mật khẩu tài khoản TikTok.
  * Cột 7 (`PASS MAIL`): Mật khẩu hòm thư Hotmail/Gmail.
  * Cột 12 (`PASS CHATGPT`): Mật khẩu tài khoản ChatGPT.
- **CẤM TỰ TIỆN SUY DIỄN / ĐỒNG BỘ CHÉO:** Dù trong quá khứ các cột có cùng mang một giá trị thì khi tìm lại, khôi phục hoặc đổi `PASS MAIL`, TUYỆT ĐỐI CẤM tự ý ghi đè hay đồng bộ sang Cột 12 `PASS CHATGPT` hoặc Cột 4 `PASS` TikTok.
- **Quy tắc thao tác an toàn:** Mọi tác vụ xử lý mail (đổi pass, tìm pass đơn hàng BoxTaiKhoan, forgot password) CHỈ ĐƯỢC PHÉP ghi vào Cột 7 (`PASS MAIL`). CẤM chạm vào Cột 12 `PASS CHATGPT` trừ khi có lệnh đích danh từ User yêu cầu đổi/cập nhật mật khẩu ChatGPT.
- *Quy tắc này phục vụ an toàn dữ liệu credential, KHÔNG dùng để từ chối hoặc trì hoãn việc sửa lỗi khi được yêu cầu.*
<!-- CREDENTIAL-ISOLATION-POLICY:END -->
