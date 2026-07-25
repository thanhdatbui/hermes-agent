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

Run it from any working directory; replace `<hermes-repo>` with the Hermes checkout path. State and artifacts default to `<repo-path>/.hermes/agent-loop`. Use `--state-root` to override that location, or `--state` to resume a specific state file. Backend/model defaults are role-based: Codex Sol `gpt-5.6-sol/high` for planning AND coding, Claude Opus `low` for review, and OpenCode fallback. Reviewers are read-only; only the worker may edit source.

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

### Coordinator Role (Hermes) - STRICT RULES

**During Plan and Code loops (Phase 1 and Phase 2): Coordinator is a dispatcher and messenger. DO NOT:**
- Read, inspect, or review the code during the Codex-Claude loop
- Make decisions about whether fixes are correct during the loop
- Jump into the worker-reviewer loop while they are resolving
- Substitute your own judgment for the worker-reviewer consensus

**Phase 3 (FINAL GATE): After Codex + Claude reach APPROVED consensus:**
- Coordinator READS the final result (files, code, tests)
- Coordinator MAY propose additional changes or improvements
- If coordinator proposes changes → dispatch Claude to discuss/respond
- Claude and coordinator exchange until they agree on final state
- When coordinator + Claude agree → report DONE to user

**Flow:**
```
1. Codex + Claude self-resolve (plan or code loop) until APPROVED
2. Hermes reads final result
3. Hermes proposes changes (if any) → Claude responds
4. Hermes + Claude discuss until agreed
5. Hermes reports DONE to user
```

### Pre-Implementation Consensus Pattern (Audit → Plan → Code → Review)

When the user requests workflow audit + rebuild, use a 4-phase flow BEFORE the standard worker-reviewer loop:

### Phase 1: Worker-Reviewer Plan Loop (Codex and Claude self-resolve)

Spawn 2 subagents with **distinct roles**, then RELAY their outputs to each other until both agree. Coordinator does NOT read, summarize, or arbitrate.

```
Step 1: Dispatch Codex → PLAN (architecture, timeline, modules)
         Dispatch Claude → AUDIT (risks, edge cases, what NOT to do)
         Wait for BOTH to return.

Step 2: Relay Claude's audit findings to Codex → Codex responds/adjusts plan
         Relay Codex's adjusted plan to Claude → Claude re-audits
         Repeat until BOTH explicitly state AGREEMENT / NO MORE FINDINGS.

Step 3: When consensus reached, coordinator reads BOTH final outputs ONCE
         and presents a brief summary table to user for approval.
```

**Rules:**
- Coordinator does NOT synthesize or merge outputs — relay raw outputs between them
- If Claude has findings, send them to Codex as-is. If Codex adjusts, send adjustment to Claude as-is
- Continue looping until Claude says "APPROVED" or "no more findings"
- Maximum 3 rounds before escalating to user
- Only after both agree does coordinator present summary to user

**Subagent prompts:**

```text
Subagent 1 (Codex): PLAN
  - Design architecture for independent tool
  - State machine, module layout, contracts
  - Follow project conventions (AGENTS.md, PROJECT_RULES.md)

Subagent 2 (Claude): AUDIT
  - Find redundant steps, risks, behaviors to change
  - CRITICAL/HIGH/MEDIUM/LOW severity
  - Identify what must NOT be copied from old workflow
```

### Phase 2: Code Implementation → Code Review Loop (self-resolve)

After user approves the plan, spawn worker-reviewer loop for code:

```
Step 1: Dispatch Codex → CODE (implement per approved plan)
         Dispatch Claude → REVIEW (review actual diff, not prose)
         Wait for BOTH to return.

Step 2: Relay Claude's findings to Codex → Codex fixes
         Relay Codex's fixes to Claude → Claude re-reviews
         Repeat until BOTH explicitly state APPROVED.

Step 3: When consensus reached, coordinator does ONE final verification
         (files exist, tests pass) then reports DONE to user with brief summary.
```

**Rules — same as Phase 1:**
- Coordinator does NOT read/review code during the loop
- Relay raw outputs between Codex and Claude
- Continue until Claude says "APPROVED"
- Maximum 3 rounds before escalating
- Only after consensus does coordinator verify and report

### Role Assignment Lesson

**DO NOT** assign both agents the same role. User wrote "codex plan, claude audit" — explicit role separation. Default to:
- Codex: planning/architecture → implementation
- Claude: auditing/review → verification

This matches their mental model: builder vs inspector, separated by phase.

### When to Use This Pattern

- Replacing proprietary/vendor-locked automation
- Refactoring complex workflows with many edge cases
- Building independent tools from reverse-engineered specs
- Any task where audit + design must precede implementation

### Pitfalls

- Do not send both agents to audit — wastes one agent's capability
- Do not skip consensus check — plan and audit may contradict
- Do not let audit agent also code — breaks separation of concerns
- Do not rush to code before consensus — audit findings must shape architecture
- When user explicitly states roles (e.g., "Codex plan, Claude audit"), follow exactly — do not reinterpret or "optimize" their flow

## Support Files

For automation scheduler design patterns in the D:/Taadaa ecosystem (device lock policy, timeline constraints, subprocess timeout, tray icon pattern), see `references/automation-scheduler-patterns.md`.

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

## Hermes Role Constraint (CRITICAL)

**When user assigns agent roles (Codex/Claude/etc), Hermes MUST be orchestrator ONLY.**

Hermes responsibilities:
- Dispatch subagents with proper context
- Collect and synthesize results
- Route to next phase (e.g., audit → plan → code → review)
- Present consolidated findings to user
- Make flow decisions (consensus check, approval gates)

Hermes MUST NOT:
- Write code when Codex is assigned as coder
- Perform audit/review when Claude is assigned as reviewer
- "Help out" by coding directly because subagent seems slow or you "already have the files open"

If you find yourself writing code when user assigned Codex as coder → **stop and dispatch instead**. The user's flow is: Codex plans + codes, Claude audits + reviews. Follow it exactly.

### Model Assignments

Default model routing for this workflow (user has enforced this — do not deviate):
- **Codex planning/design**: `gpt-5.6-sol` at `high` effort
- **Codex coding/implementation**: `gpt-5.6-sol` at `high` effort
- **Codex debugging** (D:/Taadaa): `gpt-5.6-luna` at `high` effort
- **Claude audit/review**: `claude-opus-5` at `low` effort

When dispatching Codex for planning or coding, always use `model: {"model": "gpt-5.6-sol", "effort": "high"}`.
When dispatching Claude for audit or review, always use `model: {"model": "claude-opus-5", "effort": "low"}`.

Common mistake: using `gpt-5.6-luna` for planning or coding. Luna is for debugging under D:/Taadaa only. Sol handles all plan/build work.

## Pitfalls

- **Do not code directly when user assigned Codex as coder.** Even if you have context loaded, even if it seems faster. Dispatch. The user's mental model requires separation.
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
