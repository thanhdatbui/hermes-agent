# Session-close remediation discipline

Use this reference whenever the user says `chốt phiên`, `chốt`, `done`, `wrap up`, or asks whether the work is finished.

## Non-negotiable behavior

- A reviewer result of `REJECTED` or a score below 85 is an active remediation work item, not a result to hand back for permission.
- Continue the loop: extract the reviewer findings as a bounded patch contract, apply the smallest safe fix, run the focused offline test, then rerun the closeout gate.
- Do not ask the user whether to continue. The coordinator already has authority to perform the remediation loop.
- Stop only when the reviewer returns `APPROVED` with Overall Score >=85, or when a genuine external blocker remains after the scoped remediation path is exhausted.
- Do not label an incomplete loop `BLOCKED`. A real blocker needs concrete evidence such as an authentication/credential failure on push.
- Keep closeout scope explicit. Do not let reviewer remediation drift into unrelated dirty files, broad refactors, device actions, or unverified production claims.

## Evidence checklist

1. Exact target files and reviewer findings are recorded.
2. Focused offline tests pass after the fix.
3. The next closeout gate uses the same scoped file list.
4. The gate output contains the final verdict and score.
5. Push is attempted only after APPROVED; verify the remote result, or report the exact credential/transport error.
