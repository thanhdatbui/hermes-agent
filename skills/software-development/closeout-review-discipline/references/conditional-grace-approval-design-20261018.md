# Conditional Grace Approval Design

## User-corrected intent
Grace Band is not to be deleted. It prevents low-value Sol nitpicks from creating an endless remediation loop. It is a conditional approval path, not a generic pass.

## State machine
- `STRICT_APPROVED`: score is an integer `>= 85`; normal HMAC token.
- `GRACE_APPROVED`: score `80..84` and every condition below is true.
- `REJECTED`: score `<80`, or any Grace condition fails.

## Required Grace evidence
1. Focused test executed and green.
2. Total diff <= 30 added + deleted lines.
3. At most 2 changed files, including the focused test.
4. No protected/system path modified.
5. No critical/P0 finding.
6. No reviewer-handoff/strike lock active.
7. Audit record binds repository, target scope, score, evidence, and approval kind.

## Implementation contract
- `closeout_policy.json` must define `strict_threshold: 85`, `grace_threshold: 80`, and `grace_budget: {max_files: 2, max_lines: 30}`.
- `gate_common.strict_passes(score)` must only accept integer scores >=85.
- `gate_common.grace_eligible(score, evidence)` must enforce 80<=score<85 plus every evidence condition.
- Token payload must include `approval_kind` (`strict` or `grace`); issue/verify must reject a mismatched kind.
- `closeout_gate.py` must emit `STRICT_APPROVED`, `GRACE_APPROVED`, or `REJECTED`; never map Grace to generic `APPROVED`.
- Push/DONE guards must accept a verified strict or grace token according to their policy, and must never accept a bare score or text claim.

## Critical pitfall
Do not make a generic `passes()` default to Grace. That caused `passes(84)` to return true where strict tests expected false and blurred the meaning of the gate. Keep strict and conditional decisions separate.