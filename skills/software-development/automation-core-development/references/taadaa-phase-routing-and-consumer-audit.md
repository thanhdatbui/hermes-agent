# Taadaa automation-core phase routing and consumer-audit notes

## Routing

- Primary plan/code audit: `ag/claude-opus-4-6-thinking` through the AG audit wrapper.
- Fallback only after a documented AG route failure: Terra for ordinary cases, Sol for difficult/high-risk cases, then OpenCode audit as the last fallback.
- Implementation/build/fix: one fresh Luna/high or Flash/high worker with an exclusive scope. `delegate_task(role=leaf)` does not choose the model; a child inherits the parent model.
- Keep the selected auditor across re-audit rounds. Do not call a Luna/Flash implementation child a read-only auditor.
- Gate sequence: plan audit APPROVED -> phase build -> deterministic verification -> AG audit -> fix/re-audit -> commit -> next phase.

## Windows AG-wrapper path rule

The AG Python wrapper is native Windows Python. Pass `D:/...` paths to the Python script. An MSYS `/d/...` path can be created or consumed by Bash, but native Python `open()` may fail on it. When this happens, reuse the same files with Windows-native paths rather than recreating the work.

Audit prompt should require:

- verdict on line 1: `APPROVED | MINOR_FIXES | REJECT`;
- exact locators, trigger and consequence for every finding;
- explicit treatment of pre-existing baseline failures;
- read-only behavior and no live/ADB/credential/workbook access.

## Phase 4 consumer-audit pattern

For a read-only audit of consumers listed by `automation-core/docs/scope.md`:

1. Inventory all nine named repos before drawing conclusions. Use `pathlib`/`os.walk` or carefully quoted paths; shell tools can mishandle Windows paths containing spaces.
2. Inspect only safe source, tests, dependency pin files, and docs. Exclude `.env*`, secret/token/password/auth/session/OTP/serial-named files, credential files, workbooks/data exports, logs/raw runs, `.ai-runs`, generated outputs, and mailbox/account data. Record `NOT_INSPECTED`; never infer contents.
3. For each consumer record FACT with exact path/symbol/line, or `NOT_FOUND` / `NOT_INSPECTED` / `NEEDS_PROOF`. Do not label a consumer DONE from static claims or process status.
4. Build a trigger matrix for every consumer: `NO_HANDLER single`, `preflight`, `incomplete handler`, `HARD_STOP`, `NON_RETRYABLE`, `generic exception`, `budget exhausted`, `no-hook`.
5. Distinguish package-version baselines precisely: recovery migration target `0.4.25` is not the same as lock-ownership rollout sync `0.4.24`. A pin such as feed `0.4.18` is below both thresholds.
6. Separate local retry/final states from core `FAILED_LOCKED` proof. Static retry caps or `FINAL_BLOCKED` strings do not prove durable lock retention, AI hook registration, or live execution.
7. Report only the report artifact in core; do not modify consumer repos. Include the exact environment/test blocker if the planned verify command resolves an installed stale package instead of the worktree (`PYTHONPATH=src` is required for authoritative core tests).
8. Before audit sign-off, verify report line count/hash, nine consumer sections, eight trigger labels per consumer, redaction markers, and git status. Then use the same AG audit route for the report and fix only documented attribution/precision findings.

This reference captures the reusable routing and safe static-audit pattern; it is not evidence that any particular consumer has migrated.
