# Runtime Guard and Allowlist Edits (Claude CLI / Worker Delegation)

## Problem Pattern
The user requests an allowlist update against a familiar workspace hook path (for example, `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`), but the gate implementation lives in a separate runtime plugin (such as `%LOCALAPPDATA%/hermes/plugins/farm-coordinator-guard/farm_policy.py`).

If the delegation contract forwards the user-stated path without preflight validation, the worker cannot find the target symbol (`coordinator_terminal_gate`) or regex (`(?:inspect_machine|closeout_gate|done_gate|cage_gate)`), leading to empty diffs or invented structures.

## Safe Delegation Workflow

1. **Preflight Symbol Resolution**
   - Check whether the requested symbol exists in the user-named file.
   - If missing, locate the canonical runtime definition before building the prompt.
   - Disclose the path redirection explicitly in the delegation contract.

2. **Strict Single-File Contract**
   - Bind the worker to the exact runtime path.
   - Provide the exact line or unique regex anchor.
   - Require `Read` before `Edit`.
   - Require abort/report if the expected regex or function is not present; forbid synthesizing replacement gates.

3. **Untrusted Worker Self-Report**
   - A self-report claiming `pytest 11/11 pass` or `exit code 0` is necessary but not sufficient.
   - Verify the diff independently (`git diff` or focused file inspection).
   - Check both positive acceptance (the new allowed binary/tool runs) and negative rejection (unlisted tools remain blocked by default-deny).
   - Do not mistake a script's `--help` output for proof of gate approval unless executed through the restricted terminal path that the guard enforces.

4. **Runtime Cache and Reload Policy**
   - Distinguish process-per-run execution from long-lived gateway processes.
   - If the runtime imports the policy module persistently, note that the running daemon may require a restart to pick up edits.
