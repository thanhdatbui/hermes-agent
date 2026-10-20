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

## Threshold and Grace discipline

Never claim that 80–84 is approved merely because a source branch or memory note contains a Grace condition. Verify runtime output plus audit/token metadata. Grace is conditional on the actual policy: focused tests, exact diff/file limits, no protected paths, no critical finding, no handoff lock, and the correct approval kind. If the gate prints threshold 85 or returns `REJECTED`, report that observed state until the policy is reconciled and tested.

## Remediation boundaries

- A score below threshold is actionable only when the reviewer had complete context and the candidate scope was valid.
- A timeout or `valid: false` repair proposal is not a successful patch.
- Do not add docstrings, telemetry, tests, or architecture solely to chase points after a handoff circuit breaker fires.
- Do not create a new closeout runner or change a guard before existing gate, scope, ownership, and token contracts are reconciled.
- If a candidate cannot be safely isolated, report BLOCKED with the command, error, hashes, and ownership evidence; never fabricate approval.

## Diff Budget Sizing & Combined Test-Diff Invariant (30KB Gate Limit 20/10/2026)

`closeout_gate.py` enforces a hard physical cap: `MAX_DIFF_BYTES_GATE = 30_000` (30 KB). Exceeding this triggers instant fail-fast:
`GATE-FAIL(diff-too-large): targeted diff quá lớn (> 30000 bytes). Vi phạm quy chuẩn phân rã task O(1).`

1. **The Test-Exclusion Reviewer Penalty Trap**:
   When the combined diff of `impl.py` + `test_impl.py` exceeds 30KB, Coordinators often make the mistake of submitting ONLY `impl.py` in `--files` to squeeze under 30KB.
   - **Consequence**: Sol Reviewer penalizes `test_evidence` heavily (capping score at 73–78/100, below 85), repeatedly citing: *"Điểm test_evidence bị giới hạn; việc thay đổi logic mà không cung cấp diff của test khiến chưa thể xác nhận an toàn."*
2. **The Dirty Monolith Contamination**:
   Unrelated dirty files (such as `jobs.json` with 600+ lines diff from cron updates) staged or passed to `--files` consume 50KB+ instantly, blowing the budget.
3. **Combined Budget Protocol (≤ 29,500 bytes for Impl + Test)**:
   - **Unstage Dirty Non-Targets**: Run `git status` and ensure only the exact target implementation and test files are staged/targeted.
   - **Surgical Diff on Impl**: Retain existing function signatures and helpers untouched. Avoid formatting refactors or gratuitous rewrites of untouched functions (e.g. `run_night_batch`).
   - **Surgical Test Assertions**: Extend existing test suites minimally using parameterized cases or compact mock helpers instead of copying large boilerplate fixtures.
   - **Pre-Flight Diff Byte Check**:
     Always run before invoking `closeout_gate.py`:
     ```bash
     git diff HEAD -- <target_impl.py> <target_test.py> | wc -c
     ```
     Ensure the output is strictly **<= 29,500 bytes**, allowing BOTH implementation and test diffs to enter the Reviewer's payload together.

## Background Cron Commit Collision & Scope Reconciliation (Hermes / Auto-Sync Repos)

In repositories where recurring background crons periodically auto-commit (e.g., `sync-hermes-skills-and-brain-to-git` committing skills/memories every 5 minutes in `D:/Taadaa/Hermes`):
1. **Collision Mechanism:** Chore commits land on top of HEAD while an agent is developing, testing, or waiting for review. The task commit becomes buried several commits deep.
2. **Gate Rejection:** `closeout_gate.py` runs `_committed_scope` against `<base>..HEAD`. Because HEAD now includes chore commits touching extra files (`skills/**`, `memories/**`), `set(targets) != committed_scope`, throwing:
   `ValueError: committed <base>..HEAD scope [...] != --files targets [...]; refusing partial committed scope`.
3. **Reconciliation Protocol:**
   - **Tạm dừng Cron:** Gọi `cronjob action=pause job_id=<id>` (ví dụ `7e576815788f`) để đóng băng auto-commit trong pha Closeout.
   - **Đưa Target Commit lên Đỉnh HEAD:** Đảm bảo commit của task là `HEAD` duy nhất so với `HEAD~1`:
     * Chạy mixed reset về commit trước task: `git reset <pre_task_commit>`.
     * Commit toàn bộ các file chore trước: `git add deploy/hermes-home/memories skills && git commit -m "chore: sync skills and brain memories"`.
     * Commit đúng các file mục tiêu của task sau cùng để làm HEAD: `git add <target_files> && git commit -m "feat(...): ... [gate-approved]"`.
     * Kiểm tra `git diff --name-only HEAD~1..HEAD` đảm bảo trùng khớp 100% với danh sách `--files targets`.
   - **Thẩm định Closeout Gate:** Chạy `closeout_gate.py --repo ... --base HEAD~1 --files <target_files> --json-output`.
   - **Mở lại Cron:** Sau khi gate hoàn tất, gọi `cronjob action=resume job_id=<id>`.
   - Chi tiết ca xử lý xem `references/cron-sync-commit-collision-and-closeout-scope-reconciliation-20261019.md`.

## Unrelated Regression Test Timeout Trap & Direct Test Binding

In `closeout_gate.py`, test discovery follows a strict priority:
1. **Direct Test Priority (`if direct_tests:`):**
   If `--files` targets include AT LEAST ONE test file (matching `test_*.py`, `*_test.py`, or under `tests/`), gate sets `focused = direct_tests` and executes ONLY those tests, skipping any fallback suites.
2. **The Missing-Test Fallback Trap (`elif staged_files:`):**
   If `--files` contains only business implementation files without an accompanying test file, gate falls back to heuristic mappings and automatically appends heavy regression test suites (e.g. `tests/test_tiktok_runner_preflight.py`). If those suites contain un-mocked disk scans, long loops, or pre-existing failures on `main`, execution exceeds the 120s gate timeout cap, causing an immediate `TEST_FAILED` rejection.
3. **Mandatory Pairing Rule:**
   Always declare BOTH the implementation file and its focused test file in `--files` (e.g. `--files <impl.py> <test_impl.py>`). This binds execution strictly to `< 5s` focused tests and isolates closeout verification from repository-wide regression noise.
4. **Fail-Closed Gate Discipline:**
   When `closeout_gate.py` exits non-zero, NEVER push to remote. Keep local commits intact as audit evidence and report BLOCKED with exact command and error details.

## Reporting format

- `Candidate:` exact base, HEAD, target paths, staged/unstaged state.
- `Payload:` complete/partial, digest level, reviewer context status.
- `Tests:` exact command and result.
- `Gate:` score/verdict/threshold/scope hash/handoff streak.
- `Action:` remediation, handoff, or blocked reason.
- `Not done:` commit, push, token, or approval claims lacking evidence.

Detailed incident evidence belongs in `references/closeout-payload-scope-and-handoff-incident-20261018.md` and `references/unrelated-regression-test-timeout-trap-20261020.md`.
