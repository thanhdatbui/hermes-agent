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


<!-- CODEX-DIRECT-WORKER-POLICY:START -->
## Coordinator -> direct worker boundary (canonical)

- The desktop/main session is coordinator/report surface only: it may perform read-only triage/research, route handoffs, inspect artifacts/diffs, run deterministic read-only verification, and report.
- For every write, edit, build, package, deployment, or other side effect, the coordinator must dispatch exactly one fresh, non-resumed, non-forked in-process direct worker pinned to the session's own model (`deepseek-v4-flash` for Hermes, `gpt-5.6-luna` for Codex), `reasoning_effort=high`, and `role=worker`, with an exclusive exact file/component/worktree scope. `gpt-5.6-luna/high` and `deepseek-v4-flash/high` are equivalent worker roles.
- The direct worker is already the sole executor: it patches, builds, and tests its assigned scope directly. It must not inherit, spawn, resume, fork, or delegate to another worker/agent/session, and must not invoke an external agent or CLI route. If the tool surface exposes any delegation capability, the worker must fail closed with `NESTED_DELEGATION_FORBIDDEN` and must not call it.
- A created/bound direct worker treats its current session as the final executor; it must not probe for, request, or create another worker/runtime, and it must never self-report SUBAGENT_RUNTIME_UNAVAILABLE. Tool absence inside an existing worker is not pre-create transport failure; use WORKER_RUNTIME_NOT_VERIFIED or NESTED_DELEGATION_FORBIDDEN as applicable and stop.
- Terra/high, Terra/xhigh, Sol/high, and Sol/max are read-only planners/advisors/auditors; they never patch, build, or run live/side-effecting work.
- An external CLI transport is not the normal route. The coordinator may use it only as the separately gated fallback in the parent `D:\Taadaa\AGENTS.md`, after authenticated pre-create in-process `transport-unavailable`, machine-readable `capability-unavailable`, or in-process dispatch `429`, plus proof that no worker/session/process/lease/action exists for the exact scope. The same model/profile, reservation, binding, checkpoint, reconciliation, and post-verifier gates still apply.
- Failure labels are lifecycle-hard: `SUBAGENT_RUNTIME_UNAVAILABLE` is reserved exclusively for a pre-create transport failure, and only with machine-readable evidence plus exact-scope reconciliation proving that no child/worker, session, process, lease, tool event, or action exists. A worker that exists or is bound must never self-report or assign this code.
- Use `WORKER_PROFILE_MISMATCH` for a created worker with the wrong pin and `WORKER_RUNTIME_NOT_VERIFIED` when provider/profile binding cannot be verified. Use `WAIT_WINDOW_EXPIRED` when a bounded wait has no final while the worker remains active. A timeout never changes a label or becomes `SUBAGENT_RUNTIME_UNAVAILABLE`.
- A replacement is permitted only after the current worker has shut down and exact-scope lease/process/tool-event/action reconciliation proves no overlap; replacements never run in parallel, and a worker must not self-replace or initiate replacement.
- If no valid direct worker exists, stop all write/live/side-effecting work. Coordinator direct fallback is allowed only when the current user request explicitly authorizes it, both worker routes have failed and been reconciled, and the parent contract permits exact-scope offline repository files; it never authorizes live work.
- Worker self-report, process status, scheduler status, or exit code is not completion proof; the coordinator must independently inspect the exact diff and run the deterministic verifier.
<!-- CODEX-DIRECT-WORKER-POLICY:END -->

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
