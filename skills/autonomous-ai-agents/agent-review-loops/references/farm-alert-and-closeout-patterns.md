# Farm Alert and Closeout Patterns

## Alert loop

`ALERT → EVIDENCE → CLASSIFY → WORKER → VERIFY → CANARY → DONE/BLOCKED`.
Diagnosis is not terminal. Resolve exact host/machine/serial, read bounded log/XML/screenshot evidence, classify the fingerprint, dispatch a scoped fix, independently verify, then run a bounded canary.

## Worker lanes

Select a lane before dispatch instead of using a generic long timeout:

- read-only evidence: ~120s
- exact patch: ~180s
- scoped code surgery: ~300s
- policy/docs: ~240s
- runtime/canary: ~600s
- long batch: background launcher + event-driven completion

Split evidence, code patch, focused verification, and live canary into separate tasks. After timeout, inspect shared diff/artifacts before retrying; partial work is parent-verified, and any retry uses a materially narrower contract.

## Policy-only closeout evidence

For Markdown/AGENTS policy changes, add one deterministic offline focused test that reads the policy files and asserts state machine, R1–R4 bounds, schema, safety invariants, and closeout triggers. Run that test explicitly. `closeout_gate.py` can otherwise fall back to the repository-wide suite when no staged Python source/test is mapped; use `--skip-test` only after the focused test passes, while retaining the independent reviewer gate.

## Exact-scope closeout

Session-close triggers are: `chốt phiên`, `chốt`, `đóng phiên`, `xong phiên`, `kết thúc phiên`, `done`, `wrap up`. Stage only the task-contract allowlist; preserve unrelated dirty/staged/untracked files. Require `closeout_gate.py` reviewer exit 0 and score >=85 before commit/push, then push the configured upstream branch and verify the remote SHA.

## Common pitfalls

- Do not retry the same broad worker prompt after timeout.
- Do not interpret unrelated dirty files as a blocker for a scoped commit.
- Do not claim DONE from a single process exit code.
- Do not use the full test-suite fallback as focused evidence.
- If a reviewer route fails, diagnose the endpoint/model mismatch and use the configured fallback; never invent a verdict.
