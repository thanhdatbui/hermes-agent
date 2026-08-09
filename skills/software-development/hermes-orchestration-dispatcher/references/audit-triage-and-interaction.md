# Audit triage and interaction discipline

## Ask vs. act

When the user asks only for analysis, trade-offs, or a recommendation, answer that question only. Do not patch a skill, AGENTS.md, config, or workflow until the user explicitly says to decide/update/apply it (for example: “chốt”, “cập nhật”, or an execution request).

## Long-running task communication

- During a long batch, do not narrate tool-by-tool progress or paste intermediate output.
- Give a final summary when a phase is complete.
- If the user asks for an update, report only: current verified state, exact blocker/gate remaining, and next verification. Do not claim “almost done” while an audit/approval gate remains.

## Finding acceptance gate

Before opening an implementation worker for an audit finding, classify it:

- **CONFIRMED** — includes `file:line`, a concrete executable path/input, production consequence, and a RED test or short reproducible test plan. Batch it for implementation.
- **NEEDS_PROOF** — plausible concern without enough evidence. Do not automatically modify production code; request/reason through the missing proof first.
- **DUPLICATE / SAME-INVARIANT** — belongs to an already confirmed safety invariant. Add it to that invariant’s test matrix rather than opening a one-finding worker.

## Invariant batching and circuit breaker

Group confirmed findings by shared invariant (for example, recovery durability, caption semantic identity, or parser strictness). For each group, create a state table/test matrix, then run one exclusive sequential implementation phase.

If two consecutive audits reject the same invariant, stop incremental patching. Perform a short design/state-table review and write the missing tests before the next implementation batch. This prevents “fix one edge case, discover the adjacent edge case” loops without dismissing concrete P1s.

## Standard vs. blind audit

- Standard re-audits should evaluate the changed invariant plus the current batch’s evidence.
- A blind audit is an independent final cross-check after standard audit approval; it is not a routine discovery loop between every patch.
- Auto-fix only concrete P0/P1 findings. Do not auto-open work for style-only, speculative, or ungrounded P2 findings.

## Worker budget

Keep the hard 50-call cap. For a same-file task, phase workers sequentially and reserve verification calls. If two workers in a row exhaust their budget before verification, stop spawning broad follow-ups; switch to a narrow deterministic checklist/batch verification or escalate to the user.