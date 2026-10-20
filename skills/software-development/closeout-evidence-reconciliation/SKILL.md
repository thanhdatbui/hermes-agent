---
name: closeout-evidence-reconciliation
description: "Use when closeout evidence conflicts or a gate times out."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [closeout, evidence, pytest, timeout, canary, audit]
    related_skills: [closeout-review-discipline, agent-verification-loop, verification-evidence, session-close-protocol]
---

# Closeout Evidence Reconciliation

## Trigger

Use when a closeout gate times out, rejects a candidate despite local green tests, a worker claims work that is not independently verified, or a canary/audit receipt may belong to another commit or subsystem.

## Core rule

The canonical closeout command is the acceptance oracle. Local tests, worker summaries, old reviewer scores, and old canary receipts are supporting evidence only. A timeout is not approval and a local pass is not proof that the gate accepted the same bytes.

## Procedure

1. Capture the exact gate command, exit code, timeout duration, base ref, candidate `HEAD`, and scope. Classify a timeout as `TEST_TIMEOUT` until a later exact gate run exits 0.
2. Reconcile the live workspace independently: `git status --short`, `git diff --name-only`, `git diff --numstat`, current `HEAD`, and the exact allowlisted files. Do not trust worker self-reports.
3. Run each mapped focused test file independently from the repository root using the same interpreter/pytest mode as the gate. Then run the exact combined command the gate maps. A shortened `-k` run or a single-file pass is diagnostic, not final evidence.
4. If a run hangs, use `-v -s` or `--durations` only to locate the first slow node. Inspect fixture deadlocks, subprocess/network/device calls, and interpreter/import-path differences before changing production code. Do not patch production merely to hide a test timeout.
5. After any test or fixture edit, discard all earlier counts and rerun the exact combined command. Only fresh exit code 0 from the canonical command is usable for the next closeout attempt.
6. Rerun `closeout_gate.py` with the exact implementation/test scope and wait for the actual reviewer verdict. Keep local-test evidence and gate evidence in separate report lines.
7. After `APPROVED >= 85`, verify the audit binding matches the current commit before push. If the gate passed an older SHA, rerun it; do not reuse the older token.

## Worker and canary evidence

- Worker completion metadata is untrusted until parent-side diff and tests confirm it. If a worker is scoped to one file, it may not edit another requested file; dispatch a separate bounded task or edit only under the applicable escalation rules.
- A canary receipt must be fresh, hash-valid, bound to the current candidate, and targeted to the subsystem changed in the diff. A generic feed screenshot cannot prove a sync, 2FA, switcher, or watchdog-taxonomy change.
- Never manufacture or rewrite a canary receipt, screenshot hash, reviewer token, or audit record to make a guard pass. If the official runner is unavailable, report the literal blocker and keep the release gate closed.

## Reporting format

Report, in order: current `HEAD`/scope; independent focused test results; exact closeout-gate result; audit-binding status; push/remote status. Say `INCOMPLETE` when any required gate or release step is missing. Do not report `DONE`, `closed`, or `pushed` from a local test pass or reviewer score alone.

## Pitfalls

- Do not call a gate timeout a stale wrapper without evidence from a later exact gate run.
- Do not use a passing local `58 tests` result to override a gate timeout.
- Do not rerun the same unchanged hanging command repeatedly; isolate the slow node first.
- Do not claim a prior commit's canary or closeout approval covers a new commit.

See `references/timeout-and-cross-evidence-reconciliation.md` for the tested pattern from mixed watchdog/sync focused suites.
