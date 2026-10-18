---
name: closeout-scope-evidence-triage
description: "Use when closeout scope or reviewer evidence is ambiguous."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [closeout, scope, evidence, payload, handoff, git]
    related_skills: [closeout-review-discipline, session-close-protocol, concurrent-workspace-safety]
---

# Closeout scope and evidence triage

Use this skill when a closeout gate rejects a candidate but the rejection may be caused by review transport, mixed Git scope, ownership collisions, or a reviewer circuit breaker rather than by the implementation itself. Keep four evidence domains separate: behavioral tests, reviewer context completeness, gate approval/token state, and Git candidate scope.

## Required sequence

1. Freeze the evidence frame before editing: exact `HEAD`, upstream SHA, `git status --short --untracked-files=all`, staged and unstaged path sets, `git log <upstream>..HEAD --oneline`, and the intended target allowlist.
2. Check candidate shape. If local commits ahead of the selected base contain paths outside the target allowlist, do not pretend the commit is partial with a file filter. Reconcile the exact candidate in an isolated worktree or review the exact commit.
3. Check reviewer payload completeness. Inspect implementation and test diffs separately with the repository payload diagnostic. `NEED_CONTEXT`, truncation manifests, and partial/L4 digests are context failures, not code-quality scores.
4. Run focused tests after the final write. Record command, interpreter, duration, pass/fail counts, and warnings. Label this as behavioral evidence only; green tests do not imply approval.
5. Read the audit record. Confirm verdict, score, threshold, scope hash, diff hash, reviewer handoff streak, and token/approval kind. Runtime output and audit metadata outrank memory or prose.
6. Honor the circuit breaker. When the gate emits `REVIEWER_HANDOFF_TRIGGERED` for one scope, stop speculative score-chasing. Use the mandated handoff; if it times out or returns `valid: false`, report that exact hard-stop evidence and do not dispatch another speculative repair.
7. Preserve foreign work. Never reset, restore, clean, stash-drop, whole-file overwrite, or edit protected guard sources merely to manufacture a reviewable candidate. Distinguish unrelated dirty paths, overlapping ownership, agent-caused scope drift, mixed committed scope, and tool failure.

## Threshold and Grace discipline

Never claim that 80–84 is approved merely because a source branch or memory note contains a Grace condition. Verify runtime output plus audit/token metadata. Grace is conditional on the actual policy: focused tests, exact diff/file limits, no protected paths, no critical finding, no handoff lock, and the correct approval kind. If the gate prints threshold 85 or returns `REJECTED`, report that observed state until the policy is reconciled and tested.

## Remediation boundaries

- A score below threshold is actionable only when the reviewer had complete context and the candidate scope was valid.
- A timeout or `valid: false` repair proposal is not a successful patch.
- Do not add docstrings, telemetry, tests, or architecture solely to chase points after a handoff circuit breaker fires.
- Do not create a new closeout runner or change a guard before existing gate, scope, ownership, and token contracts are reconciled.
- If a candidate cannot be safely isolated, report BLOCKED with the command, error, hashes, and ownership evidence; never fabricate approval.

## Reporting format

- `Candidate:` exact base, HEAD, target paths, staged/unstaged state.
- `Payload:` complete/partial, digest level, reviewer context status.
- `Tests:` exact command and result.
- `Gate:` score/verdict/threshold/scope hash/handoff streak.
- `Action:` remediation, handoff, or blocked reason.
- `Not done:` commit, push, token, or approval claims lacking evidence.

Detailed incident evidence belongs in `references/closeout-payload-scope-and-handoff-incident-20261018.md`.
