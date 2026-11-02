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
8. Operational / No-Code Audit Package Standards (`--input`): When reviewing operational investigations, telemetry audits, or database state without code diffs, Sol Reviewer requires verbatim raw evidence rather than summary narratives:
   - Verbatim test outputs showing every test case node, duration, and exit code.
   - Verbatim Git environment outputs (`rev-parse HEAD`, `diff --exit-code`, and clean `git status`) tying the audit to an exact repository ref.
   - Mathematical proof of disjoint partition ($Total = \sum Buckets$, $A \cap B = \emptyset$) across all clusters.
   - Complete census audit (100% check with 0 conflicts) when attributing telemetry warnings to historical schema transitions.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
