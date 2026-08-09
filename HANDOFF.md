# Hermes Local Handoff

This file is the short current-state handoff. Historical task details are in
`docs/ai/hermes-handoff-history.md`; do not load that file unless the task
requires historical reasoning.

## Workspace

- Repository: `D:\taadaa\Hermes`
- Product direction: Kanban-first, cost-aware AI orchestration.
- Worker models are replaceable role bindings, not hard-coded lifecycle states.

## Current State

- The checkout contains the upstream Hermes agent plus local orchestration
  policy files.
- The latest recorded work completed safety, reconciliation, concurrent-source
  guards, and review-state integrity for external worker lanes.
- This branch is applying a documentation-only context-loading cleanup.
- No live provider, messaging, browser, cron, account, or deployment action is
  authorized by this handoff.

## Operating Rules

- Use `AGENTS.md` as the startup entrypoint.
- Read `PROJECT_RULES.md`, `PROJECT_STRUCTURE.md`, or the historical handoff
  only when the task requires them.
- Keep persistent memory for stable user preferences and durable facts, not
  task transcripts or run history.
- Keep task state, attempts, artifacts, and detailed history in Kanban or
  repository artifacts rather than in always-loaded prompt files.

## Validation

- Python tests: `bash scripts/run_tests.sh <target>`.
- Compile-only checks: use the repository's existing test/validation scripts.
- Review `git diff --check` and the final diff before commit.

## Next Action

- For runtime work, read the narrow implementation path and its tests first.
- For context-loading work, keep root instructions short and move detailed
  guidance or historical state under `docs/ai/`.

## 2026-08-09 — Active Audit Routing Policy v6 phủ AGENTS.md
Chuỗi mới: AG Claude (ag/claude-opus-4-6-thinking/HIGH, 1 route/task) → GPT review (cx/gpt-5.6-terra-review|sol-review/HIGH) → combo opencode-audit (9Router: nemotron-3-ultra-free → big-pickle → longcat-2.0-free → ling-3.0-tiny-free) → AUDIT_ALL_ROUTES_FAILED.
Planner: cx/gpt-5.6-terra (thường) | cx/gpt-5.6-sol (khó) → AG Claude → opencode-audit.
CẤM: gpt-5.6-luna làm planner/auditor (worker), cmc/* (không quota), opencode-free/oc/deepseek-v4-flash-free (DeepSeek Flash = worker), Gemini, Command Code.
Backup AGENTS.md bản cũ: %TEMP%\policy-routing-v6-* / policy-routing-v6b-* / v6e-* (sha trong manifest.json).
