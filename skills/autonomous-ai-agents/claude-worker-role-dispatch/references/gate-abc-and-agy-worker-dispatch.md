# 3-Stage Mechanical Gate (Gate A-B-C) and Agy Worker Dispatch

## Architecture Overview (Updated 2026-10-22)

The pair-programming flow for Taadaa Farm operates under a deterministic 3-stage mechanical verification pipeline:

```
[Gemini Coordinator] -> Gate A (Evidence Pack) -> PASS
         |
         v
[Claude Sonnet 5.5]  -> Gate B (Plan & Rollback) -> PASS
         |
         v
[Agy CLI (Tier 1)]   -> Gate C (Git Diff Scope & Acceptance Tests) -> PASS
 (Haiku Fallback)
         |
         v
[Claude Reviewer]    -> Independent Verification -> APPROVED
```

## Role & Model Matrix

| Role | Model / Tool | Gate / Stage | Turns / Cap | Responsibility |
|------|--------------|--------------|-------------|----------------|
| **Coordinator** | Gemini | Gate A (Pre-flight) | N/A | Gather ground-truth evidence (file, OCR, cmd, log). Verify via `plan_exec_gate.py A`. |
| **Planner** | Claude Sonnet 5.5 (`claude_worker.py --role planner`) | Gate B (Planning) | Max 15 turns | Read Gate A evidence, produce `plan.json` (files_to_edit, acceptance, rollback). Verify via `plan_exec_gate.py B`. |
| **Worker (Tier 1)** | Agy CLI (`ag_cli.py fix`) | Gate C (Execution) | Max 15 calls | Primary code modifier. Bound to `plan.json` scope lock. |
| **Worker (Tier 2)** | Claude Haiku 5.5 (`claude_worker.py --role worker`) | Gate C (Fallback) | Max 15 turns | Fallback only when Agy exhausts quota or fails execution. |
| **Reviewer** | Claude Sonnet 5.5 (`claude_worker.py --role reviewer`) | Closeout / Audit | Max 15 turns | Independent adversarial audit of code diff and test suite. |

## Single Dispatch Gateway (`dispatch_worker.py`)

Code modification dispatch is centralized in `D:/Taadaa/tools/dispatch_worker.py`:
- **Default Tier 1 (Primary):** Agy CLI via `python D:/Taadaa/tools/ag_cli.py fix`.
- **Default Tier 2 (Fallback):** Claude Haiku CLI via `python D:/Taadaa/tools/claude_worker.py --role worker`.
- Command-line override: `--primary agy` (default) or `--primary haiku`.
- Environment variable override: `DISPATCH_PRIMARY_WORKER=agy`.

## Mechanical Gate Contract (`plan_exec_gate.py`)

1. **Gate A (`python D:/Taadaa/tools/plan_exec_gate.py A --task-id <id>`):**
   - Validates `evidence_pack.json`.
   - Requires empirical evidence (OCR text match, log pattern, sha256 checksum, or cmd exit code 0).
   - Anchors base commit sha in git ref `refs/gates/<id>/a` and append-only ledgers. Fail-closed if anchor fails.

2. **Gate B (`python D:/Taadaa/tools/plan_exec_gate.py B --task-id <id>`):**
   - Validates `plan.json`.
   - Requires clean git working tree.
   - Enforces scope lock (files_to_edit count <= 2, acceptance test command < 30s, non-empty rollback command).
   - Signs receipt with HMAC canonical JSON.

3. **Gate C (`python D:/Taadaa/tools/plan_exec_gate.py C --task-id <id>`):**
   - Compares working tree git diff against Gate B base commit sha.
   - Strictly rejects any untracked or modified file outside `files_to_edit`.
   - Executes acceptance commands from `plan.json`.
   - Signs passing receipt with HMAC canonical JSON.

## Trust Boundary Specification

- **Co-operative Guardrails:** Protects against developer/agent accidents (scope creep, uncommitted files, skipped tests, receipt tampering, commit drift).
- **Same-User OS Constraints:** Under Windows same-user execution, adversaries can mutate user-level artifacts (`git update-ref -d`, `%TEMP%` files). True adversarial isolation requires external sandboxing (Job Object Low-Integrity, AppContainer, separate OS account).
