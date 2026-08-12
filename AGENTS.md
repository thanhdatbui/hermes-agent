# Hermes Agent Instructions

This file is the always-loaded entrypoint for AI coding assistants. Keep it
short. Read the detailed development guide only when the task needs it.

## Startup

- Read this file first.
- Read `PROJECT_RULES.md` only when the task needs execution or safety rules.
- Read `HANDOFF.md` only when current repository state, blockers, or explicit
  continuation context matters.
- Read `PROJECT_STRUCTURE.md` only for architecture, runtime flow, or
  cross-file work.
- Read only the source files and tests directly relevant to the assigned task.
- If no task is assigned, stop after startup and wait.



## Scope And Safety

- Keep the change narrow and evidence-based.
- Preserve the upstream Hermes architecture: Kanban is the workflow engine;
  do not create a second orchestrator database or workflow engine.
- Do not run live messaging, browser, cron, billing, account, or provider
  actions unless the user explicitly authorizes them.
- Never read, print, edit, stage, or commit credentials, OAuth state, local
  sessions, user memory, `.env`, `.hermes`, logs, caches, or generated output.
- Use profile-aware Hermes paths such as `get_hermes_home()`; never hardcode
  `~/.hermes` in runtime code.
- On Windows, preserve explicit encodings and avoid POSIX-only assumptions.

## Context And Cost Invariants

- Preserve per-conversation prompt caching and strict message-role
  alternation.
- Do not rebuild the system prompt or mutate prior conversation context
  mid-session except in the existing context-compression lifecycle.
- Every core tool adds schema cost to every model call. Prefer existing code,
  CLI plus skill, service-gated tool, plugin, or MCP before a new core tool.
- Keep persistent memory concise and stable. Store task history in durable
  task state or artifacts, not in user memory or this file.
- For batch or isolated review work, use the existing `skip_memory` and
  toolset-filtering paths where the caller supports them.

## Work Loop

1. Confirm the expected behavior and inspect the relevant implementation.
2. Make the smallest safe change.
3. Run the narrowest meaningful test through `scripts/run_tests.sh` when
   applicable.
4. Review the diff for unrelated churn, secrets, generated files, and
   prompt-cache regressions.
5. Update `HANDOFF.md` only when the next session needs new state.

If the same error remains after two meaningful attempts, stop and hand off the
evidence instead of retrying blindly.

## Detailed References

- Full development and architecture guidance:
  `docs/ai/hermes-development-guide.md`
- Full historical handoff and prior decisions:
  `docs/ai/hermes-handoff-history.md`
- Stable architecture map: `PROJECT_STRUCTURE.md`
- Execution guardrails: `PROJECT_RULES.md`
- Context compression implementation: `agent/context_compressor.py`

## Merge / Cleanup Rule (bắt buộc, 2026-08-08)

Khi thực hiện merge nhánh về main hoặc dọn nhánh/tree quan trọng:
1. Lên PLAN bằng subagent TRƯỚC khi merge (không merge mù).
2. Worker thực thi merge/resolve.
3. Chạy AUDIT lại sau khi worker xong — lặp tới khi audit APPROVED mới xoá nhánh/tree.
4. Xoá nhánh chỉ sau bằng chứng absorbed/superseded (merge-tree/reflog/fsck).

<!-- WORKER-CHECKPOINT-TERMINATION-POLICY:START -->
## Worker checkpoint và gate dừng process (bắt buộc)

- Worker/background run phải ghi checkpoint và report riêng theo từng vòng: scope, thời điểm, phase, diff/test thật và điều kiện chờ kế tiếp; không chỉ ghi report ở cuối.
- Không suy luận code lỗi từ stdout đứng yên hoặc `exit code -15`. Chỉ được terminate khi có lỗi fatal/quota/transport machine-readable, hoặc sau ít nhất 3 quan sát cách nhau tối thiểu 30 giây (tổng >=90 giây) cùng chứng minh output/checkpoint/file mtime/process tree không tiến triển, không còn child code/test/tool hoạt động.
- Trước khi terminate phải lưu đầu/cuối log, process tree, mtime, `git status` và `git diff`; nếu worker có thể đã ghi code thì chạy hậu kiểm diff/test độc lập trước kết luận.
- Kill/exit bất thường phải phân loại `WORKER_TERMINATED_EXTERNALLY` hoặc `WORKER_EXITED_WITHOUT_REPORT`; không rollback mù, không tin report cũ, không chạy worker thay thế chồng. Reconcile exact scope và verifier độc lập trước replacement/commit.
- Quy tắc này bổ sung `agent-review-loops`; không cho phép bỏ qua gate riêng của repository hoặc mở rộng side effect/live scope.
<!-- WORKER-CHECKPOINT-TERMINATION-POLICY:END -->

## Canonical Script Reuse Rule (bắt buộc, 2026-08-12)

- Khi cùng một workflow/operation chỉ thay input data (ví dụ Tik1/Tik2/TikN, account row 1/2/N, machine list hoặc config path), PHẢI dùng lại canonical script/entrypoint đã chạy chuẩn.
- Chỉ thay tham số hoặc file dữ liệu qua CLI/config; KHÔNG tạo launcher/runner/script tạm mới và KHÔNG ghép shell loop/xargs để thay thế flow canonical.
- Nếu canonical script chưa nhận data variant cần thiết hoặc còn hardcode path cũ: sửa/build chính script đó theo hướng parameterized, giữ nguyên safety gate hiện có; ghi baseline rollback trước edit, test/preflight variant cũ + mới, audit/verify rồi mới chạy live.
- Chỉ tạo script mới khi workflow thực sự khác và user đã chốt rõ; phải ghi lý do vì sao entrypoint hiện tại không thể tái sử dụng.
- Trước launch phải ghi evidence gồm canonical script path và data path/row đã chọn; việc đổi data không được bypass lock, account/target verifier, confirmation, recovery hoặc report contract.

