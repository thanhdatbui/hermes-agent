# Audit-loop execution and worker budgets

## Decision before side effect

When the user asks for analysis or a choice (for example, whether a rule loops, whether a review is overthinking, or which option is best), answer the analysis first. Do **not** edit a skill, AGENTS.md, config, gateway, or workflow merely because an option appears preferable. Apply a change only after an explicit action instruction such as “chốt”, “update”, “áp dụng”, or equivalent.

## Keep the 50-call guardrail; plan within it

The hard 50-tool-call cap is a safety guardrail, not a reason to spawn endless workers.

- For the same file/component, split work into sequential exclusive phases: diagnosis/production edit, then tests/docs/verification.
- Budget roughly 25–30 calls for investigation and implementation; reserve 10–15 calls for focused tests, full verification, EOL, and diff checks.
- Parallelism is allowed only for separate repos or non-overlapping files.
- A handoff must state: changed files/diff, tests run and failures, line-ending status, temporary artifacts, and the one next action.
- If two workers on the same component exhaust their budgets before verification, do not autonomously launch an ambiguous third worker. Narrow the remaining work to a mechanical checklist/batched verification, or request a user decision when scope truly cannot be reduced.
- Batch independent mechanical operations with a script/tool call rather than repeatedly rereading or invoking one test at a time.

## Audit-loop communication

During long implementation or audit batches, stay quiet unless the user asks for status. When asked, answer briefly with the current phase, independently verified evidence, and any real blocker. Send a full report only at decision milestones: green tests, audit verdict, commit/push, gateway restart, or a user decision.

## Audit quality gate (khớp D:\Taadaa\AGENTS.md rule 8, meta-audit Sol R1)

Finding phải được auditor phân loại thành: `CONFIRMED_P0`, `CONFIRMED_P1`, `NEEDS_PROOF`, `NOTE`, `DISPROVED`, `DUPLICATE`.

- **Admission gate**: chỉ auto-fix `CONFIRMED_P0/P1` khi đủ `(a)` stable locator (file:line hoặc file + symbol/key/state-transition), `(b)` executable production branch/input/state, `(c)` hậu quả production cụ thể, `(d)` **executed** RED reproduction hoặc artifact-backed production trace. Reproduction plan chưa chạy → `NEEDS_PROOF`: mở đúng MỘT evidence-gathering phase có owner/boundary/verifier; không sửa production trừ containment incident. P2/speculation → `NOTE`, không mở worker.
- **Batch theo invariant**: gom confirmed findings cùng một safety invariant (recovery durability, caption semantic identity, validator fail-closed...). State table/test matrix phải ghi known paths, cách khám phá path, dependency/contract boundary, assumptions, negative-space cases. Một worker consolidated phase sửa toàn matrix + regression bundle, không `1 finding → 1 patch → full audit`.
- **Circuit breaker**: đếm 2 chu kỳ `implementation material → standard audit` REJECT cùng invariant (không đếm rerun cùng evidence, không đếm blind chạy sai thời điểm). Chạm ngưỡng → dừng patch chắp vá, chạy read-only design/impact audit để tái-baseline matrix, rồi ĐÚNG một consolidated implementation phase. 2 chu kỳ liên tiếp ra CONFIRMED P0/P1 mới ngoài matrix (cross-invariant) cũng dừng patch → impact/design audit; không tạo chuỗi invariant mới vô hạn.
- **Audit scope**: audit thường = changed code + invariant matrix + impacted dependency cone, contract/data boundary, regression surface. Blind adversarial CHỈ sau standard APPROVED, kèm task spec, invariants, dependency surface, verifier artifacts và full diff; KHÔNG kèm history finding/fix/verdict. Model giữ Sol khi user đã pin; blind gọi chính xác là `context-blind`, không tự đổi model family.
- **Exit/release gate**: 2 audit liên tiếp chỉ còn NEEDS_PROOF/NOTE → dừng reviewer churn, NHƯNG không phải APPROVED/release. Mọi NEEDS_PROOF credible P0/P1 phải được disposition `DISPROVED` (có evidence), `ACCEPTED_RISK` bởi owner có thẩm quyền, hoặc `FINAL_BLOCKED`. `DISPROVED/DUPLICATE` phải kèm evidence hoặc liên kết finding gốc để không lặp lại. Không cap cứng số vòng với CONFIRMED P0/P1 thật.

## Telegram progress and pinned-auditor transport

- **Silence means no message at all.** Never send visible placeholders such as `[SILENT]`, raw tool/process markers, or a fake “waiting” reply. During a long batch, report only at real milestones (verified test result, audit verdict, commit/push, blocker) or when the user explicitly asks status.
- Keep the concepts separate in updates: a **chat-session fallback** (for example, Terra → DeepSeek) does not change a separately pinned worker/auditor model. State the exact model and transport used by the worker; do not imply that Telegram’s current reply model reviewed the code.
- If the pinned auditor’s normal proxy route returns an upstream-auth failure, retry once. If it persists, preserve the pinned model and probe an already configured alternate transport directly (for Codex CLI: `-c model_provider="<configured-provider>"`). Verify with a tiny read-only request first, then rerun the audit. Do not silently substitute a different model family. Record the route change as audit provenance.
- A tool’s read-only sandbox may fail suite setup because it cannot create cache/temp files. Treat that as an environment limitation, not a code failure; release evidence must come from the coordinator’s real repository test run.
