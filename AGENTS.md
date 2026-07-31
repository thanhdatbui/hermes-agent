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
