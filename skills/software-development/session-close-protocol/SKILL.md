---
name: session-close-protocol
description: "Use when the user says 'chốt phiên', 'đóng phiên', 'kết thúc phiên', or 'xong phiên'. Run the final review/commit/rebase/push workflow only then; never trigger it from a progress question."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [session-close, review, git, handoff, taadaa]
    related_skills: [taadaa-farm-ops-rules, verification-evidence, concurrent-workspace-safety]
---

# Session-close protocol

References:
- `references/plan-review-diff-scoped-payload-safety.md` — Quy tắc diff-scoped payload và socket timeout an toàn khi gọi Gate 1 Plan-Review qua 9Router tránh nghẽn context và timeout.
- `references/incident-evidence-live-canary-protocol.md` — Quy trình bắt buộc chạy Live Canary đầy đủ (runner swipe + cleanup home + unlock) khi có incident evidence / ảnh lỗi hiện trường.
- `references/multi-repo-rebase-and-chained-token-closeout.md` — Quy trình commit trước pull/rebase đa repo kèm cơ chế token authorization cho chuỗi popup liên hoàn.
- `references/reviewer-finding-triage.md` — Phân loại finding REJECT (reproduce, baseline-check, f-string continuation pitfall, stale git lock) trước khi sửa; cấm push khi còn REJECTED.

## GATE 0: LIVE CANARY CHỈ KHI CÓ TARGET LIVE HOẶC INCIDENT EVIDENCE
Khi phiên có sửa code tính năng/farm hoặc logic runtime:
- **BẮT BUỘC chạy Live Canary bằng RUNNER CHÍNH THỨC của repo** (TUYỆT ĐỐI CẤM dùng ad-hoc tap/script lẻ thay thế):
  1. **Với `tiktok-luot nuoi acc` (Feed):** Chạy runner với `--max-swipes 2` (hoặc `--recovery-test-swipes 2`) + `--cleanup-on-stop` → Tự động đóng popup → Swipe đủ 2 video → Tự động dọn dẹp về Home và nhả lock.
  2. **Với các script nghiệp vụ khác (`Tiktok_Reg`, `tiktok-follow`, `Tiktok-video`, `Hotmail`, `tiktok-add-bao-mat-f2a`, `register gmail`...):** Chạy runner chính thức trên máy target → Vượt qua đúng điểm nghẽn/lỗi đã fix → Chạy tiếp đến khi hoàn thành trọn vẹn nhiệm vụ của script (Task Completion) → Tự động dọn dẹp và nhả lock.
- Với **code-only thuần túy** (không có target máy, không có ảnh/log hiện trường từ user), mới ghi `CANARY_NOT_APPLICABLE`.
- **Target-resolution gate chỉ áp dụng khi target đến từ task hoặc incident evidence:** resolve `<row>` bằng hàm mapping canonical và nguồn workbook/device-map thực tế. Nếu resolver lỗi khi target đã được xác định, báo `TARGET_RESOLUTION_UNPROVEN`.
- **Preflight bằng đúng interpreter trước live canary:** trước khi gọi PowerShell/runner có thể chạm thiết bị, chạy một import/entrypoint smoke bằng chính executable mà launcher sẽ truyền cho runner, kèm kiểm tra dependency bắt buộc tối thiểu. Nếu lỗi import/setup xảy ra trước target action (ví dụ thiếu native dependency của PIL), phân loại là `BLOCKED_AT_GATE_0_PREFLIGHT`, ghi rõ `no device action occurred`, và không tiếp tục review/commit/push. Không nhầm lỗi môi trường với lỗi UI/popup; khi setup được sửa ở phiên khác, phải chạy lại preflight rồi mới canary.
- **Phân loại canary failure theo stage:** tách `target resolution`, `runner/import preflight`, `device preflight`, và `runtime/UI`. Wrapper exit 1 không đủ để kết luận popup hoặc thiết bị lỗi; phải đọc traceback và artifact stage thực tế.
- Khi canary được chạy, chỉ kết quả `status: success`, `final_status: success`, `stop_reason: ""` mới mở các gate review/commit/push. Nếu canary fail/blocked, dừng release actions và báo đúng blocker.

## Purpose

## All-repository policy propagation lesson

When a user asks to update a rule across all repositories, do not limit the inventory to `AGENTS.md` and `PROJECT_RULES.md`. Enumerate every active top-level Git checkout under the workspace, then inspect tracked `AGENTS.md`, `CLAUDE.md`, `PROJECT_RULES.md`, nested app context files, and explicitly discovered workspace policy files. Distinguish policy adapters from non-policy templates (for example a design-system `templates/claude.md`) before editing. Capture byte/hash/EOL baselines, append one markered canonical block without normalization churn, preserve unrelated dirty work, and verify marker uniqueness plus idempotence across the complete allowlist. During closeout, commit each repo's exact policy candidate separately, resolve the configured upstream per repo instead of assuming `origin/<current-branch>`, and verify the policy commit by exact subject/path scope plus ancestry on both local and remote refs; a later concurrent commit may legitimately move `HEAD` beyond the policy commit. If normal `git commit` is blocked by a stale temporary index lock, do not remove locks blindly: prove no active writer owns that temporary index, use a fresh isolated index, and preserve the real worktree/index state. Use `references/all-repo-rule-propagation.md` for the inventory, baseline, append, and verification procedure.

## Closeout lessons from farm alert and swipe-cap work

### Target resolution and blocker separation

- Resolve the target from the repository's canonical resolver and authoritative runtime/source artifacts before classifying a canary blocker. A missing guessed config filename, truncated search result, stale report, or wrong state-root lookup is not evidence that a row is absent.
- Keep these states separate: candidate row exists; incident-specific row is identified; target machine is in the frozen cohort; device lock is active; canary preflight is configured. They are independent gates and must not be collapsed into one blocker.
- When the user reports that an operation such as Reg has stopped, re-read live lock metadata and owner state before treating that operation as the current blocker. An expired/stale lock still requires the owner/controller release path; do not delete it manually or assume stopping the operation updates lock metadata.
- Validate a frozen cohort against the assignment manifest whose `assignment_id` and `manifest_digest` match the cohort. Do not validate against a convenient global/AppData manifest. If the target machine is not in the frozen cohort, report `BLOCKED_AT_GATE_0_COHORT_TARGET`; do not mutate the frozen artifact, invent a cohort, or bypass with a local-run flag.
- If a canary stops before target selection, report the exact preflight stage and explicitly state that no device action occurred. Do not describe it as a UI, ADB, lock, row, or code failure without evidence.
- After a mistaken diagnosis, keep the correction short and direct: acknowledge the incorrect claim, state the corrected evidence, and give only the current blocker and next safe action.

- Run Gate 0 only when the current task has an explicit live machine/row/serial/device target, the user explicitly requests real-device validation, or user-provided incident evidence (opening-session screenshot/alert/log) identifies a machine/target plus a concrete runtime failure being debugged. For code-only/general flow work without such target or incident evidence, record `CANARY_NOT_APPLICABLE`; the exact diff still requires focused tests and an independent parseable review.
- **User correction — no target is not a canary blocker:** If the user says there is no machine/target, do not invent one from repo names, workbooks, cron state, stale locks, or historical artifacts. Mark `CANARY_NOT_APPLICABLE` and continue to model review → focused verification → exact-scope commit → rebase → push. Do not stop closeout at Gate 0 merely because the code touches farm/runtime paths.
- If the review route cannot authenticate or returns no parseable verdict, classify the closeout as `BLOCKED_AT_REVIEW`; never commit/push and never soften the result into “chốt xong”. Preserve the exact route blocker without printing credentials.
- When a concurrent writer changes a scoped file after a prior commit, re-read the full file, freeze the new exact diff, and invalidate old review/test evidence. Re-check the invariant after each rebase/merge; this prevents a later timeout commit from reverting `FEED_SESSION_MAX_SWIPES` from 15 to 16.
- A full-suite timeout is also not a pass; report the command and the bounded evidence.
- If Gate 0 fails for a machine-specific blocker (for example, that machine's VPN/proxy), do not misclassify it as a candidate-code failure. Preserve the failed target artifact, and when the user explicitly authorizes choosing another machine, resolve a fresh machine+row target from runtime evidence, preflight the replacement, and rerun the same canary contract there. Keep the original target's blocker separate from the replacement target's pass/fail.
- A transient device lock must be rechecked live before reporting it as the current blocker; an old canary artifact is historical evidence, not present state. Never unlock, kill, reboot, or force-takeover merely to manufacture a Gate 0 pass.
- **Live-cron lock is not a canary pass and not a kill target:** if the target machine is held by a live cron (`multi-machine-feed-session --machines ...` with a running pid, e.g. pid 201676 holding 74 machines), do NOT use `--full-scope-takeover`, kill the pid, or delete the lock to force a canary. Classify `BLOCKED_AT_GATE_0_LOCKED_BY_LIVE_CRON`, preserve the cron/lock untouched, use focused tests as substitute evidence, and report it in Blocker. Verify lock owner live via `tasklist` / process CommandLine before concluding.
- Keep the final user report short and structured: `Mục đích → Kết quả → Blocker → Remote`. Put the direct status in the first sentence.


“Closeout” is an internal label for the final release pass:
**Gate 0: live canary only when the current task has an explicit live machine/row/serial/device target, the user explicitly requests real-device validation, or user-provided incident evidence identifies a machine/target plus a concrete runtime failure being debugged → Gate 0.5 (Automation Tasks Only): cập nhật Case Fix thực tế & Anti-Pattern tương ứng vào `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`) → Gate 1: review the final candidate → Gate 2: commit the exact scope → Gate 3: git pull --rebase → Gate 4: push → verify the remote SHA**.
For code-only/general flow changes without such target or incident evidence, record `CANARY_NOT_APPLICABLE` and go directly to farm automation catalog update (if automation-related) → review → test → commit → rebase → push. Never infer a target from repository name, config, workbook, historical artifacts, or nearby machine files. The user does not need to know or repeat the word `closeout`. Use plain Vietnamese when explaining it.

## Trigger and non-trigger

This workflow is activated only when the user uses one of these four equivalent commands as an action:

- `chốt phiên`
- `đóng phiên`
- `kết thúc phiên`
- `xong phiên`

Do **not** activate it for `xong chưa?`, `đã xong chưa?`, a general progress update, or a summary request. Those receive status only and must not commit, rebase, push, merge, delete branches, or change the remote.

A task instruction such as “sửa”, “test”, or “làm xong” also does not silently authorize this final release pass. Wait for one of the four explicit session-close commands before performing the commit/rebase/push sequence.

**Original-deliverable scope reset:** when `chốt phiên` is received, reconstruct the deliverable from the user's original request and the session's confirmed change ledger before reading old handoffs or dirty candidates. Closeout releases that deliverable only; it does not revive a prior-session blocker, stale remediation branch, or unrelated candidate merely because its files are present in the worktree. Quarantine unrelated candidates, preserve them unchanged, and report them separately.

**No remediation expansion during closeout:** a review finding may reopen implementation only when the user explicitly asks to fix that rejected candidate and the candidate belongs to the current closeout scope. If the original deliverable is already committed and remote-verified, stop; do not dispatch workers, run new audits, or chase newly discovered findings. If the original deliverable cannot be identified without guessing, stop at `BLOCKED_AT_SCOPE_RECONCILIATION` rather than widening the task.

**User-correction: closeout means the original small deliverable, not the loudest dirty candidate.** When the user says `chốt phiên`, reconstruct the original change ledger first and freeze it as the only candidate. Do not revive an older remediation branch because its files are dirty, a worker handoff arrived, or a reviewer found problems in it. If the user later explicitly says to fix until review passes, keep the same original allowlist and exact candidate; do not expand from a small upload/feed change into unrelated sync, lock, recovery, TOCTOU, or broad hardening work. Before any new review round, state the exact files being reviewed and verify that no historical candidate is included.

**One-writer closeout fence:** never dispatch multiple workers against a shared worktree or keep polling while a worker owns the candidate. Use one coordinator-owned writer or an isolated worktree per worker; after handoff, re-read and reconcile before any further edit. A concurrent commit or scoped rewrite invalidates all prior tests/reviews and is a reconciliation stop, not a reason to keep patching around it. See `references/closeout-scope-recovery.md` for the recovery checklist.

**Original-deliverable scope reset:** when `chốt phiên` is received, reconstruct the deliverable from the user's original request and the session's confirmed change ledger before reading old handoffs or dirty candidates. Closeout releases that deliverable only; it does not revive a prior-session blocker, stale remediation branch, or unrelated candidate merely because its files are present in the worktree. Quarantine unrelated candidates, preserve them unchanged, and report them separately.

**No remediation expansion during closeout:** a review finding may reopen implementation only when the user explicitly asks to fix that rejected candidate and the candidate belongs to the current closeout scope. If the original deliverable is already committed and remote-verified, stop; do not dispatch workers, run new audits, or chase newly discovered findings. If the original deliverable cannot be identified without guessing, stop at `BLOCKED_AT_SCOPE_RECONCILIATION` rather than widening the task.

**User-correction: closeout means the original small deliverable, not the loudest dirty candidate.** When the user says `chốt phiên`, reconstruct the original change ledger first and freeze it as the only candidate. Do not revive an older remediation branch because its files are dirty, a worker handoff arrived, or a reviewer found problems in it. If the user later explicitly says to fix until review passes, keep the same original allowlist and exact candidate; do not expand from a small upload/feed change into unrelated sync, lock, recovery, TOCTOU, or broad hardening work. Before any new review round, state the exact files being reviewed and verify that no historical candidate is included.

**One-writer closeout fence:** never dispatch multiple workers against a shared worktree or keep polling while a worker owns the candidate. Use one coordinator-owned writer or an isolated worktree per worker; after handoff, re-read and reconcile before any further edit. A concurrent commit or scoped rewrite invalidates all prior tests/reviews and is a reconciliation stop, not a reason to keep patching around it. See `references/closeout-scope-recovery.md` for the recovery checklist.

If the user asks what the rule means, explain it without running the workflow.

When policy choices are unclear, ask **one decision question at a time** in plain language. Do not dump a list of unrelated policy questions or introduce internal jargon without explaining it.

## Closeout lessons from the failed mixed-candidate attempt

**Candidate extraction precedes all release gates:** In a dirty/shared checkout, freeze the original deliverable before review or final testing. Verify that the isolated worktree/clone path exists and is the path actually being used; never silently fall back to the shared checkout when a path is missing. Materialize the candidate from the actual current upstream/base plus only the confirmed deliverable hunks. A staged file with the right filename is not proof of the right candidate: exclude older fixes, unrelated docs/config, sibling-worker tests, and mixed same-file hunks. Run tests and review only against the materialized exact tree, recording its SHA/tree identity.

**Closeout failure is terminal for this turn:** If the first mandatory focused test or review gate fails, stop immediately at `BLOCKED_AT_<GATE>`. Do not call later gates, patch the candidate, restage, re-review, commit, rebase, push, or claim “đã chốt” in the same closeout turn. Preserve the failed candidate for a later explicit continuation. Keep the user-facing report short and direct: first line = gate status; then only `Mục đích → Kết quả → Blocker → Remote`, without progress narration or a long internal transcript.

**Remote/base reconciliation:** Before reviewing or committing, compare local `HEAD`, the actual upstream SHA, and the candidate base. If upstream is ahead, rebuild the candidate on that upstream and invalidate earlier tests/review. Do not absorb every dirty/staged path just because it overlaps the same files; compare exact hunks and preserve unrelated work untouched.

## User-decided policy

- **User communication style:** The user wants simple, minimal reports focused on task purpose and result (`Mục đích → Kết quả → Blocker → Remote`).

A dirty worktree is evidence to classify, not an automatic stop. If unrelated staged/unstaged paths or non-overlapping hunks exist, preserve them and continue the requested closeout by reconstructing the exact candidate in a clean temporary worktree or isolated index. Stop only when a same-file overlap, active writer, branch-tip change, or other condition makes the requested bytes unprovable. Do not turn unrelated dirt, a sibling candidate, or a concurrent edit in another region into `BLOCKED`; do not reset, clean, stash, or overwrite it.

### User correction: explicit canary waiver

When the user explicitly says to skip/bỏ qua canary, record `CANARY_WAIVED_BY_USER`, perform no live device action, and continue the remaining non-live gates: exact-scope candidate verification, independent review, commit, rebase, push, and remote-SHA verification. Do not silently reintroduce the canary later or classify the waiver as target-resolution failure. Report the waiver clearly.

- **User communication style:** The user wants simple, minimal reports focused on task purpose and result (`Mục đích → Kết quả → Blocker → Remote`). Do NOT flood the user with internal workflow details, tool outputs, or technical option lists. When guiding an interactive Windows operation, give exactly one concrete next action or one copy-paste command at a time, then wait for the observed result; never tell the user to run a command without actually providing it. If the user says a command is still at a continuation prompt (`>>`), first provide the cancel/recovery action, then provide a complete single-line replacement command in the next step. The assistant autonomously decides technical choices (routing, testing, staging, isolated patching) based on project rules and executes safely.
- **Remote-host evidence boundary:** Do not claim that a remote PC, service, or Hermes instance was configured merely because the current machine can inspect a local checkout or reach a LAN port. Separate local evidence from user-executed remote actions. For remote setup, verify each stage with an explicit output from the target host: config path/value presence without printing secrets, authenticated endpoint response, then one real end-to-end model/tool call. Treat placeholders or dummy API keys as non-working until the target service's auth database explicitly accepts them; never assume LAN reachability bypasses authentication.
- When the user says `chốt phiên`, treat it as full closeout, not merely cleanup: freeze exact scope, reconcile live/runtime state, review and verify the final candidate, then commit/rebase/push only if the gates pass; otherwise report the exact blocked gate. Never claim closeout from a worktree deletion or summary alone.
- **Hard trigger interpretation:** `chốt phiên đi` is the same executable closeout trigger as `chốt phiên`; it is not a request to stop work, give a progress summary, or continue an older investigation. On receipt, immediately enter the closeout state machine and do not start, resume, or delegate unrelated remediation.
- **Closeout ownership fence:** before any closeout action, reconcile and shut down active workers/processes created for the current task, then freeze the exact candidate. A worker completion message is not permission to resume its old task after the user has triggered closeout. If a newly discovered process belongs to an unrelated cron/project, preserve it and report it rather than taking ownership.
- **Gate-failure exit:** if any mandatory gate fails (especially Gate 0), cancel downstream closeout steps for that candidate—no review, commit, rebase, push, cleanup, or “đã chốt” claim. Finish with `BLOCKED_AT_<STEP>` and the concrete evidence. Do not keep polling, patching, rerunning, or opening a new investigation after the blocked closeout report unless the user explicitly issues a new task.
- **User-facing closeout response:** report only `Mục đích → Kết quả → Blocker → Remote`; state the gate result in the first sentence. Do not narrate internal plans or repeatedly ask the user to confirm a command when the trigger is already explicit.
- For farm alert/recovery work, distinguish source code from the interpreter's installed/editable runtime package. Verify the module path and loaded flag with the same interpreter used by the live runner; if runtime was patched directly, preserve an external backup and report that it is not a Git commit until integrated.
- Dirty files **outside the exact task scope are not blockers** by default. Preserve them untouched; stage and commit only the explicit allowlist. This rule is semantic, not model-specific: a worker or reviewer must not convert an unrelated `git status` entry into `BLOCKED` merely because it exists. If the user explicitly authorizes committing additional non-conflicting dirty paths, treat that as a deliberate scope expansion—not permission for `git add .`: audit every added path first for secrets/credentials, local state/log/cache/runtime artifacts, generated data, large binaries/models, active writers, and missing/broken fixtures or manifests. Include only audited, parseable, non-sensitive paths; document excluded paths and the reason. Re-check the expanded allowlist immediately before staging because concurrent writers can add a dirty dependency file or untracked artifact after the first snapshot.
- **Explicit main-branch authorization overrides the default shared-checkout preference:** when the user directly orders “sửa trên main”, “merge vào main”, or equivalent, `main` is the authorized target. Do not keep refusing or deflecting to a worktree merely because the checkout is shared. Snapshot `HEAD`, staged/unstaged paths, and active worktrees first; preserve unrelated dirty paths, stage only the approved allowlist, and stop only for a real same-file/staged ownership conflict. Report the exact main commit/merge result and preserved outside-scope paths.
- Direct-main authorization does not permit broad staging or cleanup. Never use `git add -A`, `git reset`, `git clean`, or stash unrelated work to make `main` clean; use exact path/hunk staging and verify the resulting commit with `git show --name-status`.
- **Model Stability & No-Silent-Downgrade Invariant:** Model active trong phiên do user/config chỉ định (ví dụ `ag/gemini-3.7-flash-high`) là bất biến. CẤM tự ý chuyển sang model khác (như `gpt-5.6-luna` hay fallback ngầm) khi gặp lỗi prompt/timeout/compaction trừ khi có lệnh rõ ràng từ user. Nếu tool call fail do format/timeout, phải retry hoặc xử lý lỗi kỹ thuật trên chính model hiện tại, không silent failover.
- **Releasing Device Locks vs Cohort Preflight Separation:** Khi user yêu cầu "nhả lock" hoặc "release all lock", thực thi mở khóa đích danh/hàng loạt qua backup timestamp ngay lập tức mà không kéo các kiểm tra phức tạp như frozen cohort, manifest digest hay scheduler state vào làm blocker giả. Lock release là tác vụ vận hành thiết bị độc lập.
- For Hermes configuration-only fixes, treat the active config as the exact allowlist and do not invent a repository closeout: use `hermes config set <key> <value>` rather than hand-editing `config.yaml`, then parse/validate the config and verify the persisted key. A global `agent.system_prompt` can be superseded by a platform/channel `system_prompt` override, so inspect the effective override before claiming the rule applies everywhere; existing conversations may retain cached prompts and require a new session.
- When an in-scope file also contains unrelated dirty hunks, do not rely on an interactive partial stage alone. Build the staged candidate from `HEAD` (or use a precise patch/index operation), apply only the approved hunks, and verify `git diff --cached --name-status` plus the staged diff before testing. If unrelated hunks were accidentally staged, reset only the affected paths in the index and rebuild the exact staged blobs; never reset, stash, or clean the worktree.
- Bind every final test and review to the exact staged candidate, not merely the working-tree view: materialize/check the staged tree (for example with `git write-tree` + `git archive` into a temporary directory), run the focused tests and compile checks there, then obtain a fresh parseable reviewer verdict after any index rebuild. A prior approval is stale if the staged bytes or scope change.
- If a reviewer is dispatched asynchronously, report `REVIEW_PENDING` rather than `BLOCKED` while it is still running. Once it returns, independently verify its verdict is parseable and matches the final staged scope before committing.
- Review routing:
  - ordinary or single-repository work: `plan-review`;
  - core, multi-repository, state-machine, lock, recovery, or similarly sensitive work: `plan-review-hard`;
  - **The named plan-review model must be called through 9Router, not replaced by the session model or an implementation worker.** For hard review, send `model: plan-review-hard` to the configured 9Router endpoint and capture the parseable verdict bound to the exact staged candidate. Do not use Luna/Flash or the current implementation model as an auditor.
  - A worker/subagent audit is not the model review gate. Its `APPROVED`/`REJECT` is diagnostic input only; it never satisfies `plan-review`.
  - Before accepting a verdict, verify three separate facts: (1) the request used the named `plan-review`/`plan-review-hard` model, (2) 9Router returned a parseable verdict for the exact staged hash/tree, and (3) the response was actually served by the requested review route and did not silently downgrade or remap to an unsupported implementation model. If the named route is unavailable, malformed, rejected, or transparently maps to an unsupported implementation model, record `BLOCKED_AT_REVIEW` and use only the documented independent audit fallback; never call Luna/Flash as the auditor and never relabel a Luna/Flash response as plan-review approval.
  - **Routing correction learned from user feedback:** when the user asks for plan review, explicitly report the 9Router model identifier and transport before/after the call. A review sent with `cx/gpt-5.6-luna` is an implementation-worker review, not plan review, even if it returns a detailed `REJECT`. For this user's lock/recovery work, use `plan-review-hard` through 9Router first; if that route fails, preserve the exact route error and use the documented fallback only, with its actual model name labeled.
  - **For this user's lock/recovery work, prefer the hard review route and include the exact current bytes/diff plus the regression-test scope. If the primary AG route has no active credentials, record that route failure and use the configured independent fallback; do not silently call the worker review instead.**
  - **Plan-review model used in this session: `plan-review` via 9Router (port 20128). The route returned parseable `VERDICT: APPROVED` with findings. This is the correct route for TikTok follow runner fixes. Do not use the session model or implementation worker as auditor.**
  - See `references/plan-review-routing.md` for the route-selection, downgrade-detection, and evidence checklist.
  - **Call the review before repeated polling or downstream Git actions.** Once a candidate is stable, bind its hashes, invoke the review model, and stop/reconcile if a concurrent writer changes either scoped file; do not burn turns waiting while no review request is in flight.
  - **Review Payload & Socket Timeout Safety:**
    - **Diff-scoped payload:** Chỉ gửi `git diff -U3`/`-U5` của các file sửa đổi và test case mới; KHÔNG đẩy toàn bộ repo diff lớn kèm hàng nghìn dòng mock/fixture boilerplate cũ khiến model bị nghẽn context hoặc timeout.
    - **Fail-Fast Socket Timeout:** Script gọi review (Python `urllib.request` / `requests`) BẮT BUỘC đặt `timeout=45` hoặc `timeout=60` trực tiếp ở socket layer để ngắt sớm và fail-fast/retry khi proxy/upstream bị kẹt socket, tránh block tiến trình terminal vô hạn.
    - **Ưu tiên OmniRoute (:20129) khi tải nặng:** OmniRoute có cơ chế Ordered Concurrency Spillover (`priority` combo strategy, maxConcurrent=5/account qua 8 tài khoản Antigravity) và `failoverBeforeRetry: true` lập tức nhảy sang account tiếp theo khi gặp 429/503, giải quyết triệt để nguy cơ treo socket khi 9Router (:20128) bị nghẽn.
  - if calling 9Router HTTP API (`:20128`), ensure `NINEROUTER_API_KEY` is sourced from `.env`; for large diffs or reasoning models (`plan-review`, Sol/Opus, DeepSeek), set timeout to 300-900s (or background runner) as reasoning and token generation can exceed 60s;
  - if the selected route fails, record the fallback and keep the fallback reviewer read-only with respect to the main worktree and remote.
  - **Plan-Review Pitfalls & Verification Invariants:**
    - **Test Mock Boolean Accuracy:** When implementing handlers requiring `getattr(res, 'ok', False) is True`, ensure unit tests explicitly configure `mock_res.ok = True` instead of relying on default `MagicMock` truthiness.
    - **Exact Type Check for Return Codes (Bool vs Int Subclass):** In Python, `bool` is an `int` subclass (`issubclass(bool, int) is True`), so `isinstance(val, int)` matches `False`, and `False == 0` evaluates `True`. When validating ADB/transport exit codes, strictly use `type(val) is int and val == 0` or `type(res.ok) is bool and res.ok is True` to prevent unverified boolean/mock transport results from passing fail-closed checks.
    - **Immutable XML Element Inspection & UIElement Wrappers:** Detectors must never mutate parsed `ET.Element` nodes (e.g., adding `__ignored_subtree__` to `node.attrib`). Note that `iter_elements(root)` creates fresh `UIElement` wrapper objects, so `id(node)` on raw `ET.Element` will not match `id(wrapper)`; when filtering subtrees (e.g. captions/comments) traverse raw `ET.Element` directly. Also `UIElement.__init__` does not accept `center` as an argument (`center` is a computed property from `bounds`).
    - **Post-Condition Fail-Closed Verification on Dismissers:** A popup/overlay dismisser must NEVER return `dismissed=True` simply because the target overlay is no longer matching. It MUST verify: (1) hierarchy dump and parse succeed, (2) foreground package remains verified target app, (3) no transition to system dialog/launcher or sensitive screens (login, OTP, captcha, verification), and (4) the screen returned to a valid feed/home/target state (`classify_tiktok_screen(root)` non-manual-needed). Any unexpected transition or failed dump MUST fail closed (`dismissed=False`).
    - **Synchronous Selector and Popup_Type on Dismiss Success:** Every registry dismisser returning `PopupDismissResult(dismissed=True, ...)` MUST explicitly populate `selector={"action": "allowlist_dismiss", "popup_type": "<popup_name>"}`. Missing `selector` causes downstream callers (`_apply_popup_dismiss_result`) to receive `popup_type=None`, causing retry guards (`_is_allowed_popup_retry_allowed`) to treat successful dismisses as blocked (`manual-needed` / `known TikTok screen` freeze as seen in Case 67). Public dismissers (`dismiss_allowed_generic_popup`, `dismiss_any_popup`) must defensive-normalize `selector` if missing or non-dict.
    - **Display Name Exclusion from Switcher Anchors:** When detecting profile header anchors for account switching (`find_switcher_anchor`, `_find_sticky_profile_header`), explicitly exclude display-name node resource IDs (`:id/pkh`, `:id/pke`, `:id/pau`, `:id/s9b`, `tv_content_name`). On new accounts lacking `@username` headers, tapping a display name opens the Edit Name Subpage overlay ("Thêm tên bạn mong muốn") with soft keyboard, blocking the account switcher.
    - **Multiprocess Subprocess Fixtures on Windows:** When authoring concurrent multiprocess tests (`subprocess.Popen` running scripts written to `tmp_path`), always normalize all interpolated paths with `.replace('\\', '/')` and explicitly inject `sys.path.insert(0, ...)` for both `automation-core` and consumer repo roots to ensure child processes never fail with unhandled `ModuleNotFoundError` or backslash escaping bugs.
    - **Dynamic Resolution for Modal Bottom Sheet Bounds:** Never hard-code modal coordinate thresholds (e.g. `bounds.top >= 1650` or `c_bounds[1] >= 600`). Compute screen dimensions dynamically from root bounds (`screen_h = root_b[3] - root_b[1]`, `min_modal_y = int(screen_h * 0.25)`) to support varying screen resolutions.
    - **Bounded Modal Container Enforcement:** Multi-marker popup detectors must verify that candidate labels belong to a common bounded modal container (`c_bounds[1] >= min_modal_y` and not the full-screen root `[0,0,W,H]`), preventing disconnected option labels scattered across the feed from triggering false-positive `KEYCODE_BACK` dismissal.
    - **UiAutomator XML Attribute Access:** Standard `xml.etree.ElementTree.Element` nodes in UiAutomator dumps store strings in attributes (`node.attrib.get("text")` and `node.attrib.get("content-desc")`), not element attributes (`node.content_desc` raises `AttributeError`). Always use `.attrib.get(...)` with fallback to `getattr(node, "text", "")`.
    - **Dynamic Resolution Call Assertion:** When handlers query `wm size` or screen dimensions dynamically prior to an action, use `mock.adb.shell.assert_any_call(...)` instead of `assert_called_once_with(...)` to account for preceding dimension probe commands.
    - **Overlay Fail-Closed Scope:** Detectors must never accept OCR alone without validating target package ownership in XML; dismissers must verify target package foreground focus both before and after actions, failing closed if third-party/system/permission dialogs appear.
    - **Document Gate Scope Fidelity:** Never document fixes or test passes in `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`) for external repos (e.g. `automation-core`) unless those changes are actually committed in the active candidate.
  - A reviewer timeout, empty response, malformed response, missing parseable verdict, or a background reviewer that has not returned yet is a **review-route failure**, not a rejection and not an approval. Immediately retry through a different independent reviewer route with a compact forced-output format (for example: `VERDICT: APPROVED|REJECTED|BLOCKED` plus one findings line). Dispatching a reviewer is not evidence of approval; do not commit or push until a valid verdict is obtained.
  - If a fallback reviewer also returns empty/malformed output, try one more independent route before declaring `BLOCKED_AT_REVIEW`; preserve the exact evidence (timeout/empty) in the final report.
- A reviewer may fix a small review finding only in an isolated copy/worktree and must return a patch. The coordinator independently checks and applies that patch; the reviewer does not commit or push.
- After merge/apply/rebase, review and test the exact final candidate before push. If the SHA or tree changes, repeat the gate.
- **Auto-remediation on REJECT is user-intent gated:** A `REJECT` may reopen implementation only when the user explicitly asks to fix/revise/continue that rejected candidate (for example, “REJECT thì sửa đi” or “Làm tiếp”) and that candidate is still the active task. If the user says `chốt phiên`, `đóng phiên`, or otherwise asks for closeout, do not interpret the rejection as permission to start another remediation loop: freeze the current candidate, record the failed review gate, and stop at `BLOCKED_AT_REVIEW` or `BLOCKED_AT_SCOPE_RECONCILIATION`. **This is a hard stop: do not apply even a “small” reviewer fix, add tests, re-stage, or rerun review in the same closeout turn.** Never let a stale handoff, TODO, or old reviewer finding silently expand a small closeout into a new engineering project. When explicit continuation reopens the work, preserve the original allowlist, treat every post-rejection edit as invalidating prior tests/review, rebuild the exact candidate from the current scoped bytes, and obtain fresh verification plus review before any commit/rebase/push. See `references/closeout-rejection-and-concurrency.md` for the exact stop/reopen matrix.
- **Effective-route identity is part of verdict validity:** A response that says `VERDICT: APPROVED`/`REJECT` is not a valid plan-review result if the requested `plan-review`/`plan-review-hard` route was silently served by a different implementation model. Record both requested and effective model; if they differ without an explicitly supported route mapping, classify `BLOCKED_AT_REVIEW_ROUTE`, not reviewer approval/rejection, and do not use the content to authorize Git actions. A 200 response alone never proves the requested reviewer ran.
- **Candidate snapshot commands must use index-safe forms:** `git hash-object :path` is not a valid portable way to hash an index entry. Use `git ls-files -s -- <allowlist>` plus `git cat-file blob <INDEX_BLOB_SHA>` (or materialize `git write-tree`/`git archive`) and record the resulting tree/blob hashes. If a file is staged and also has unstaged edits (`MM`), the staged candidate and working tree are different byte sets; review/test/commit only after explicitly choosing and freezing one set.
- **Closeout scope is current-session-only:** derive the exact allowlist from the user's current request and the session change ledger. Historical remediation candidates, prior-session errors, worker handoffs, old rejected diffs, and newly discovered adjacent findings are evidence to report—not implementation scope. If the small change being closed cannot be identified without guessing, ask one narrow scope question or report `BLOCKED_AT_SCOPE_RECONCILIATION`; do not dispatch workers or patch broadly.
- **One writer and no scope drift:** during closeout, use at most one owned writer for the candidate. Stop/reconcile any worker before review or Git actions. Never dispatch multiple workers against the same shared worktree, and never continue editing a scoped file after a concurrent writer or commit changes it until the exact candidate is rebuilt and re-reviewed.
- **Review-model evidence gate:** A worker/subagent review is diagnostic input only. The closeout gate requires a parseable verdict from the configured `plan-review`/`plan-review-hard` model over the configured transport (normally 9Router HTTP). Record the actual model/route, candidate hash or staged tree, verdict, and route errors. Never claim “review đã gọi plan-review” merely because a delegation completed, and never convert a 200 response, passing tests, or a worker `APPROVED` into model approval.
- **Audit-route/model separation (user correction):** For Taadaa lock/recovery work, implementation workers may use Luna, but the review gate must call the named `plan-review` or `plan-review-hard` model through 9Router. Never substitute the current session model or a worker model (especially `gpt-5.6-luna`) as an auditor. If the named route fails, record the exact transport/model error, then use the configured audit fallback in the routing policy; do not silently downgrade to an implementation model. Bind the verdict to the exact staged bytes and report the route explicitly.
- **Reject-loop freshness:** After every remediation edit, invalidate all prior review and test evidence. Re-read the full scoped files, compare hashes, rebuild the exact staged candidate, run focused tests on that candidate, then issue a fresh review request. Do not keep polling while no valid review request is in flight; do not commit a candidate whose latest bytes were never reviewed.
- **Review-route fallback:** If the primary AG review route is unavailable, record the exact auth/transport failure and use the configured independent fallback reviewer without silently presenting it as AG. If every allowed route fails to return a parseable verdict, stop at `BLOCKED_AT_REVIEW`; do not commit/push or soften the result into “chốt xong”.
- If review or test fails permanently or cannot be resolved, a local exact-scope checkpoint commit is allowed, but **push is forbidden**. Report `BLOCKED` and the real evidence.
- Focused tests may be sufficient for push when they pass and any full-suite failures are proven baseline or environment failures, not new regressions. Report those classifications explicitly.
- When removing a merged branch/worktree, require `absorbed`/`superseded` evidence **after integration and before removal**, never before the merge.

For authorized dirty-worktree scope expansion and downloader-only canaries, follow [`references/scope-expanded-downloader-closeout.md`](references/scope-expanded-downloader-closeout.md). For repairing a rejected review before re-review, follow [`references/review-rejection-repair.md`](references/review-rejection-repair.md). For preserving an in-scope dirty worktree while resolving a live target and running Gate 0, see [`references/closeout-candidate-and-canary.md`](references/closeout-candidate-and-canary.md). For code-only/general-flow tasks without an explicit live target or qualifying incident evidence, use focused semantic verification (tests/compile/static checks), not a device canary. A fresh reviewer verdict is required after any candidate fix.

## Required workflow

### 0. Live Canary Test (chỉ khi task có target live hoặc incident evidence)

- Chỉ chạy live canary nếu task hiện tại nêu machine/row/serial/device target cụ thể, user yêu cầu kiểm chứng máy thật, hoặc incident evidence do user cung cấp ở đầu session (ảnh/screenshot/alert/log) xác định được máy/target và lỗi runtime cụ thể đang debug.
- Với code-only/general-flow task không có target live hoặc incident evidence, ghi `CANARY_NOT_APPLICABLE` và tiếp tục Gate 0.5.

### 0.5. Cập nhật & Rà Soát Case Fix & Anti-Pattern Catalog (BẮT BUỘC cho Farm Automation)

- **Quy tắc đọc trước khi sửa (Pre-read Catalog):** Trước khi sửa bất kỳ bug nào trên farm (UI, selector, navigation, recovery), BẮT BUỘC phải đọc kỹ `docs/farm-automation-cases.md` (hoặc `docs/uiautomator.md`) và `AGENTS.md` trước để đối chiếu xem lỗi hiện tại có thuộc case nào đã xử lý hay chưa, tránh viết đè/trùng lặp code hoặc phá vỡ các case cũ.
- **Vị trí tài liệu:** `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`).
- **Phạm vi bắt buộc:** MỌI task có sửa code/logic liên quan đến farm automation (UI, Popup, Keyboard, Switcher, Cron, Sync, Cohort, Device Lock, ADB, Follow, Upload, Reg, Mail...).
- **Nội dung yêu cầu:** Ghi rõ (1) Vị trí áp dụng, (2) Nguyên nhân gây lỗi / Anti-Pattern, (3) Giải pháp chuẩn / Case Fix thực tế, (4) Kiểm tra không trùng lặp với các case trước đó.
- **Quy tắc chặn Gate:** Nếu phiên có sửa logic farm mà CHƯA có file diff cập nhật `docs/farm-automation-cases.md` $\rightarrow$ **CẤM Commit và CẤM Push**, dừng ngay ở Gate 0.5.
- **Quy tắc Báo Cáo Chốt Phiên:** Khi báo cáo chốt phiên, BẮT BUỘC phải nêu rõ đích danh số Case vừa ghi nhận / cập nhật (ví dụ: Case 56, Case 57) trong `docs/farm-automation-cases.md` (hoặc nêu rõ số Case hiện tại trong catalog nếu phiên không thêm case mới).

### 1. Freeze the exact scope

Before mutating Git state, record:

- repository root, current branch, actual upstream remote/branch, and `HEAD`;
- `git status --short --untracked-files=all`;
- worktree/merge/conflict state;
- the exact production, rule, and test allowlist;
- foreign or concurrent-owned paths that must remain untouched.

Do not use `git add .`, `git add -A`, broad globs, or an inferred “all changed files” scope. Never read, print, stage, or commit secrets, credentials, OAuth state, workbooks, local session state, logs, caches, backups, or generated runtime artifacts. For cross-repository rule propagation, use the inventory/allowlist/EOL procedure in `references/all-repo-rule-propagation.md`.

A dirty path outside the allowlist is preserved, not reset, stashed, cleaned, or absorbed into the candidate. It is **not a blocker**: do not wait on unrelated test/build processes, inspect unrelated failures, or let foreign paths widen the candidate. Classify those paths as `OUT_OF_SCOPE` and continue. A staged/unstaged path inside the allowlist is also not automatically a conflict; staged state, an old mtime, or a non-empty status only becomes a stop condition when the requested hunk is actively owned, content changes during the current ownership window, or the candidate cannot be separated safely. If an active writer owns a path or overlapping region in the requested scope, stop and report the ownership conflict rather than clobbering it.

**Dirty-tree classification checkpoint:** before each review/commit boundary, report three separate sets: `unrelated dirty preserved`, `in-scope candidate`, and `proven overlapping conflict`. Never collapse them into one generic `BLOCKED` state. `SCOPE_DRIFT` means this agent/worker changed outside its own allowlist; it does not mean pre-existing foreign dirt exists.

**Concurrent-writer freeze gate:** record `HEAD`, branch, status, and the staged candidate before review. Re-check `HEAD`, `git status --porcelain=v2 --branch`, and staged paths immediately before every review, commit, rebase, and push boundary. If another process commits, changes the branch tip, changes a scoped file, or introduces a staged/unstaged path while closeout is in progress, invalidate all previous review/test evidence and stop for reconciliation. Do not continue patching against the old candidate, do not push a local branch that is ahead with unreviewed mixed-scope commits, and do not claim exact-scope closeout when the requested fix is only embedded inside a broad concurrent commit. Preserve the new dirty state untouched and report `BLOCKED_AT_RECONCILIATION` with the old/new SHAs and paths.

**Candidate-byte reconciliation gate:** a reviewer approval and test result bind to exact bytes, not merely to the same filenames or unchanged `HEAD`. Immediately before staging, hash or otherwise compare every scoped candidate file against the bytes supplied to the reviewer. If any scoped file differs—even when `HEAD == origin/<branch>`—invalidate the approval and prior tests, re-read the current diff, reconstruct the candidate from current `HEAD` plus only the intended hunks, and obtain a fresh review. Never whole-file-stage a mixed dirty file just to recover an approved change; preserve unrelated same-file hunks unstaged. The reusable reconstruction and verification recipe is in `references/candidate-byte-reconciliation.md`.

Allowlists are file-granular, but candidates can be hunk-granular. When a file inside the requested scope mixes candidate hunks with unrelated dirty hunks, do not treat the file as fully owned: name the split in the review findings, keep the unrelated hunks preserved, and stage with hunk-level selection (`git add -p` or equivalent) — never a whole-file add. For read-only review requests (no commit authorized), prove zero mutation: snapshot `git status --porcelain` before and after and require identical output; prefer artifact-free checks (AST parse, `python -B`) over commands that write bytecode or caches into the worktree.

### Route-scoped disable closeouts

For a disable/fail-closed fix that names one alert, trigger, or route, treat the route boundary as semantic scope—not merely a list of files:

- Name the producer route, the exact side effect to block, and the sibling routes that must remain live. A producer guard that blocks Farm Alerts' recovery `Popen` while preserving alert delivery is in scope; an unconditional early return in a shared consumer entrypoint is not, even if it stops the symptom.
- Before touching a consumer, inventory direct callers and prove how the target route is distinguished. If it cannot be distinguished safely, keep the fix at the producer seam or add an explicit invocation marker/adapter plus a focused preservation test; never blanket-disable the consumer.
- When source and installed/runtime copies may differ, inspect the actual production interpreter/module path and compare raw file hashes. A runtime hotfix must be backed up outside the repository and reconciled with the committed source; stage and commit only the explicit source/test allowlist.
- A reviewer verdict binds to the exact candidate bytes. Any edit, reversion, or scope change invalidates it: re-read the full affected files, confirm byte identity for reverted paths, rerun the focused gate, and obtain a fresh verdict. Do not carry a rejection or approval from a stale diff into commit/push.

See `references/route-scoped-disable-closeout.md` for the producer/consumer matrix, runtime-provenance checks, and the clean-worktree rebase recipe.

### 2. Inspect and independently review the candidate

Review the exact current diff and allowlist with the correct route:

- `plan-review` for ordinary/single-repository work;
- `plan-review-hard` for core, multi-repository, state, lock, or recovery work.

The HTTP request must use `stream: false`, `tools: []`, and `tool_choice: "none"`; `Authorization: Bearer ...` is an HTTP header, not request-body content; include the required `reasoning_effort`. Pass review prompts through stdin or a file, never by unsafe shell interpolation.
- **Diff Scope for Multi-Repo / In-Flight Commits:** Khi review diff đa repo hoặc diff đã có commit dở dang trong phiên, so sánh diff với commit base đầu phiên (`git diff <base_commit>`) thay vì chỉ `git diff HEAD`, để reviewer nhìn thấy đầy đủ các alias và hàm phụ trợ (tránh false-rejection).
- **Vòng lặp tự sửa lỗi khi REJECT:** Nếu reviewer trả về `REJECT`, agent BẮT BUỘC tự động phân loại finding (syntax, circular import, priority collision, fail-closed handling), sửa code, chạy test và gọi lại review cho đến khi nhận được `DECISION: APPROVED`. Tuyệt đối CẤM dừng lại báo blocker hoặc push lên remote khi chưa có `DECISION: APPROVED`.

The reviewer must return a parseable verdict and findings. A reviewer may make a small correction only in an isolated copy/worktree, then return a patch. The coordinator must inspect the patch, apply only the approved exact scope, and rerun the relevant checks. No reviewer may commit or push.

Do not fabricate `APPROVED`. An unavailable or malformed review is a review failure, not an approval.

### 3. Integrate before the final gate

If merge/apply is required, verify ownership, allowlist, branch mapping, and conflict state first. Merge only owned branches/worktrees. Do not require `absorbed`/`superseded` before merging; that evidence is checked only after integration and before any requested branch/worktree removal.

After integration, stage only the exact allowlist and create a local checkpoint commit if appropriate. Verify `git show --name-status` contains only the allowlist. A checkpoint commit is not a release approval.

### 4. Commit exact scope before Pull & Rebase

Khi làm việc trong môi trường đa máy (2+ PC dùng chung repo), thứ tự chuẩn là:
1. **Commit local trước:** Đóng băng các thay đổi và test đã pass vào commit local (`git commit -m "..."`), tuyệt đối không pull khi working tree chưa commit sạch phần cho phép để tránh conflict/mất code.
2. **Xử lý dirty files ngoài allowlist trước khi pull:** Nếu working tree còn uncommitted changes hoặc untracked files ngoài allowlist mà `git pull --rebase` từ chối thực hiện, dùng `git stash -k -u` để tạm cất các file ngoài scope, sau đó `git pull --rebase <remote> <branch>`, rồi `git stash pop` để khôi phục nguyên vẹn.
3. **Pull rebase sau:** Kéo commit mới nhất từ remote về và rebase commit local lên đầu (`git pull --rebase <upstream-remote> <upstream-branch>`).
4. Nếu sau rebase có commit mới từ remote kéo về, chạy lại quick test/compile để bảo đảm tính tương thích trước khi push.

### 5. Final review and verification on the exact candidate

Review and test the candidate **after** merge/apply/rebase and before push. The final candidate is the tree that will be pushed, not the pre-rebase diff.

Minimum evidence:

- if the final suite exposes legacy fixtures that mock `_capture_xml_text` without satisfying a newly enforced artifact-first validator, update the fixtures minimally (exact XML+screenshot artifact or a documented validator mock); never weaken production validation to preserve stale fixtures;
- focused regression tests for the changed behavior;
- compile/typecheck/lint or equivalent checks where applicable;
- `git diff --check`;
- full-suite result when affordable, with baseline/environment failures separated from new regressions;
- final staged path allowlist and SHA/tree identity.

If review or test fails, commit a local exact-scope checkpoint if needed, do not push, and report `BLOCKED` with the command and actual failure. Never downgrade a failed final gate to “done” because a wrapper exited zero.

### 6. Push explicitly, verify the remote, and synchronize local main worktree

Only after the final review/test gate passes:

```bash
git push <upstream-remote> HEAD:<upstream-branch>
git ls-remote <upstream-remote> <upstream-branch>
```

The `ls-remote` SHA must equal the pushed commit SHA. Never use force-push unless the user explicitly authorizes it.

**Local Worktree Synchronization Gate:**
When a candidate was reviewed and pushed from an isolated temporary worktree or clone, the main worktree's local branch may remain behind `origin/<branch>`. Before declaring closeout complete:
1. Reconcile the local main branch: if the main worktree has unrelated dirty work, stash it (`git stash`), fast-forward/rebase local branch to the newly pushed remote commit (`git pull --rebase <upstream-remote> <branch>`), and pop stash (`git stash pop`).
2. Resolve any non-conflicting merge markers in preserved tests/files, mark resolved, and run test verification.
3. Verify `git rev-parse HEAD` on the local main branch equals `origin/<branch>` and matches the remote SHA. A session is fully closed only when both remote and local main checkout are synchronized.

### 7. Optional branch/worktree removal

Do not remove unrelated or concurrently owned branches/worktrees. If removal is part of the requested closeout, first verify the integrated work is `absorbed` or `superseded`, then remove only the owned target and verify the resulting worktree state.

## Final report contract

Keep the report concise and factual. Include:

1. trigger and exact repository/scope;
2. số Case cụ thể (Case N) vừa ghi nhận / cập nhật trong docs/farm-automation-cases.md (Gate 0.5);
3. independent review route and parseable verdict;
4. focused/full test evidence and any classified baseline/environment failures;
5. branch/upstream/rebase state;
6. exact committed paths and local commit SHA;
7. push result and verified remote SHA;
8. preserved outside-scope dirty paths or the exact `BLOCKED` gate.

Never claim `đã chốt`, `đã xong`, or `đã hoàn tất` from a summary alone. The final state is either verified closeout or `BLOCKED_AT_<STEP>`.

## Non-negotiable safety

- **LIVE CANARY CÓ ĐIỀU KIỆN:** Chỉ bắt buộc chạy canary khi task hiện tại nêu machine/row/serial/device target cụ thể, user yêu cầu kiểm chứng máy thật, hoặc incident evidence do user cung cấp ở đầu session xác định machine/target cùng lỗi runtime cụ thể đang debug. Với code-only/general flow không có target live hoặc incident evidence, ghi `CANARY_NOT_APPLICABLE` và tiếp tục review/test/commit/rebase/push; không coi mọi ảnh TikTok/farm là target, không biến thiếu target thành blocker và không chạy mù.
- Never run live registration, device automation, workbook mutation, account actions, or lock deletion merely to close a coding session.
- Never reset, clean, stash, or stage unrelated dirty files.
- **CẤM TỰ Ý `git reset --hard` / `git clean -fd`:** Tuyệt đối không bao giờ tự ý chạy các lệnh destructive như `git reset --hard` hoặc `git clean -fd` trên live farm repos khi gặp trạng thái branch diverged hoặc rebase conflict. Luôn bảo toàn diff, kiểm tra `git diff origin/<branch> HEAD` và giải thích rõ nguyên nhân cho user thay vì phá hủy lịch sử/working tree.
- Never push an unreviewed or untested final candidate.
- Never treat HTTP 200, process exit 0, or a passing wrapper as an `APPROVED` verdict without reading and parsing the actual evidence.

## Verification checklist

- [ ] One of the four explicit close-session commands triggered the workflow.
- [ ] Progress questions did not trigger Git mutations.
- [ ] Automation task: Đã đọc trước file MD catalog và cập nhật Case Fix & Anti-Pattern tương ứng vào `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`), đảm bảo không trùng lặp code/case cũ.
- [ ] Exact allowlist and outside-scope dirty paths were frozen.
- [ ] Correct independent review route was used.
- [ ] Any reviewer patch came from an isolated copy and was rechecked.
- [ ] Merge/apply/rebase happened before the final review/test gate.
- [ ] Focused tests passed; broader failures were classified honestly.
- [ ] Exact-scope checkpoint/commit was verified.
- [ ] Push used `HEAD:<actual-upstream-branch>`.
- [ ] Remote SHA matched local `HEAD`.
- [ ] Absorbed/superseded was checked before any branch/worktree removal.
