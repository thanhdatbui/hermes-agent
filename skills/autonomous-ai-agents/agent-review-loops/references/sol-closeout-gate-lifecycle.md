# Sol Closeout Gate and Dispatch Lifecycle Semantics

Use this reference when operating or updating the Sol closeout state machine, dispatch contract hook, or review verification loops.

## 1. Dispatch Contract Hook Plan-Failure Semantics

When validating SOL plans in `hooks/guard_dispatch_contract.py`:
- Plan failures include:
  1. Missing plan file (`valid_sol_file` not found on disk)
  2. Expired plan (age `time.time() - created_at > 600s`)
  3. Unreadable plan file (corrupted JSON or I/O error)
  4. Missing plan metadata (`created_at` missing or `<= 0`)
- **Required lifecycle emission**:
  - `state`: `REMEDIATION_REQUIRED`
  - `lifecycle`: `REMEDIATION_REQUIRED`
  - `plan_state`: `SOL_PLAN_REQUIRED`
  - Explicit `blocker` and `next_action` describing remediation
- **Rationale**: Plan issues are recoverable through re-running the planner or regenerating a valid plan. Emitting `REMEDIATION_REQUIRED` signals to the coordinator that action is needed while maintaining `plan_state: SOL_PLAN_REQUIRED` for gate tracking.

## 2. Closeout Gate HARD_STOP Boundaries

In `closeout_gate.py` (`run_sol_closeout_state_machine`):
- `HARD_STOP` is **strictly restricted** to:
  1. `safety_failure`: verified safety violation or dangerous operation
  2. `integrity_failure`: audit log hash chain tamper or corruption
  3. `unauthorized_fallback`: unapproved or malformed fallback bypassing planning contracts
- **Generic `nonrecoverable` rule**:
  - A reviewer or verification hook emitting generic `nonrecoverable=True` **must not** trigger `HARD_STOP`.
  - Instead, failed verification or sub-threshold review follows the bounded retry lifecycle:
    - Attempt < max_attempts: emits `REMEDIATION_REQUIRED`
    - Attempt >= max_attempts: emits `REVIEW_REMEDIATION_EXHAUSTED` (recoverable=True, terminal=False)
- Arbitrary nonrecoverable flags without safety, integrity, or unauthorized fallback failures remain recoverable and bounded.
