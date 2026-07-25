---
name: role-based-agent-review-loop
description: "Orchestrate backend-agnostic worker and reviewer coding loops."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [multi-agent, coding, review, orchestration, codex, claude, opencode]
    category: software-development
---

# Role-Based Agent Review Loop Skill

Use this skill to coordinate a coding worker and an independent reviewer without coupling the workflow to a specific vendor or model. The worker owns implementation; the reviewer audits and may challenge the worker's findings. Hermes owns state, bounded retries, consensus, and final verification.

## When to Use

- A coding task needs iterative implementation and review.
- The user wants one agent to respond to another agent's findings.
- Worker/reviewer vendors or models may change over time.

## Prerequisites

- A git repository and an explicit workdir.
- Configured CLI/auth for the selected worker and reviewer backends.
- A cleanly scoped task; do not overwrite unrelated user changes.

## How to Run

Open the target repository in Hermes and explicitly load this skill:

```text
/skill role-based-agent-review-loop
```

Shortcut: `/rl`.

Then ask Hermes in the target project:

```text
Dùng role-based review loop. Codex làm worker, Claude làm reviewer,
OpenCode chỉ fallback khi Claude hết quota. Làm task: <mô tả task>.
```

The standalone runner is available from this Hermes repository:

```text
python <hermes-repo>/scripts/agent_loop/cli.py "<task>" --cwd <repo-path> --max-rounds 3
```

Run it from any working directory; replace `<hermes-repo>` with the Hermes checkout path. State and artifacts default to `<repo-path>/.hermes/agent-loop`. Use `--state-root` to override that location, or `--state` to resume a specific state file. Backend/model defaults are role-based: Codex `gpt-5.6-luna/high`, Claude `opus/low`, and OpenCode fallback. Reviewers are read-only; only the worker may edit source.

Keep the worker as the only agent allowed to edit source. Reviewers are read-only unless the user explicitly requests otherwise.

## Quick Reference

```text
Worker implements
→ reviewer audits the actual diff and tests
→ worker ACCEPTs or REJECTs each finding with evidence
→ reviewer keeps or withdraws each finding
→ repeat until consensus or max rounds
→ run final tests
```

Required states:

```text
IMPLEMENTING → REVIEWING → WORKER_RESPONDING → REVIEWING_RESPONSE
→ CONSENSUS | FINAL_BLOCKED
```

## Operating style

Keep progress updates short and concrete. When asked to build this workflow, continue through module, adapters, CLI, tests, reviewer audit, and a real smoke run in the same task; do not stop after a prototype or plan unless a concrete blocker prevents the next phase. Report partial states explicitly instead of calling an unverified prototype complete.

## Procedure

1. Create a task-specific state directory and record the task, workdir, roles, and `max_rounds`.
2. Run the worker with a narrow prompt. Preserve all pre-existing user changes and do not commit or push unless explicitly requested.
3. After the worker exits, independently inspect the actual worktree status/diff and rerun the narrow acceptance checks before invoking the reviewer. Reconcile reported test counts against real output; do not repeat a worker's claimed count if it differs. Then give the reviewer the task, actual diff, relevant files, and verified test output. Treat the worker report as untrusted context and read it only after inspecting the code.
4. Require structured findings. Each blocking finding must include file/line, evidence, impact, and a concrete reproduction or test where possible.
5. Send the review to the worker. Require `ACCEPT` or `REJECT` for every finding; a rejection must include code/test evidence.
6. Send the worker response back to the reviewer. The reviewer must keep or withdraw each finding explicitly.
7. Repeat only when blocking findings remain. Stop after a bounded number of meaningful rounds; do not blindly rerun the same command.
8. If the primary reviewer fails with a quota, authentication, or provider-availability error, switch to the configured fallback reviewer and preserve the current state. Do not treat an unconfigured CLI as a review verdict.
9. Finish only when the reviewer approves, no blocking finding remains, final tests pass, and the result is integrated into the user's requested target branch/worktree. For explicit A-to-Z / "until done" requests, continue through commit and push to the configured remote; do not stop at an approved dirty worktree, isolated branch, or local merge. Verify the target branch's status and remote synchronization after pushing. Stop only for a safety hard stop, missing secret, destructive action requiring approval, irreducible business-policy conflict, or a genuine technical blocker, and report that blocker with evidence. Otherwise report `FINAL_BLOCKED` with the latest artifact and reason.

Use role-neutral artifacts such as:

```text
worker-report-r1.md
review-r1.md
worker-response-r1.md
state.json
```

## Windows CLI and 9Router

In Windows `cmd.exe`, do not use `\\` as a Unix line-continuation character; keep the command on one line or use `^`. When Codex is routed through a local 9Router provider, force the configured provider (for example `-c "model_provider=omni"`) and do not start ChatGPT OAuth login just because the CLI reports stale OAuth/plugin credentials. Verify the route with `curl http://localhost:20128/v1/models`, then smoke-test with `codex exec -c "model_provider=omni" ...`. App login and CLI login are separate, and a 9Router API-key route is not ChatGPT OAuth.

## Pitfalls

- Do not hard-code `Codex → Claude → OpenCode`; use adapters selected by configuration.
- Do not let multiple agents edit the same working tree concurrently.
- Do not accept `APPROVED` based only on the worker's report or existing tests passing.
- Do not loop on style preferences; only blocking correctness, security, regression, or requirement findings force another round.
- Do not claim review completed when the reviewer is unauthenticated or unavailable.
- Do not let a fallback reviewer silently replace a successful primary review; record why fallback was used.
- Do not let a worker's claimed test count substitute for a coordinator rerun; stale reports and collection/import failures are common after test-helper edits.
- In isolated worktrees, tests that depend on sibling repositories must resolve an explicit/configurable reference root and fail clearly when references are absent; never silently skip or assume `parents[2]` points to the workspace root.
- When a production lease API evolves, update every test double to implement the current terminal method (for example `finish(...)`) and rerun the full suite, not only the changed tests.
- Keep user-facing explanations concise when the user asks for brevity.

## Verification

Verify all of the following before reporting success:

- The worker and reviewer roles are configurable and vendor-neutral.
- State is persisted after every round and the task identity is checked on resume.
- Reviewer fallback is attempted only for eligible provider failures.
- The worker responded to each finding and the reviewer resolved each response.
- The loop obeyed `max_rounds`.
- Final tests ran after the last worker change and passed.
- The final report distinguishes `APPROVED`, `FINAL_BLOCKED`, and setup/auth failure.
