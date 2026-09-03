# Closeout case note: no-target canary and cron race

## Reusable rule
A live canary is conditional on the current task having an explicit, authorized machine/row/serial/device target, the user explicitly requesting real-device validation, or user-provided opening-session incident evidence (screenshot/alert/log) identifying a machine/target plus a concrete runtime failure being debugged. For example, `[MÁY 4] DỪNG PHIÊN` plus an account and `profile verification`/`camera-recovery-failed` qualifies; resolve machine → row → serial canonically before running it. For code-only/general-flow work without a live target or qualifying incident evidence, record `CANARY_NOT_APPLICABLE` and continue the remaining closeout gates. A generic TikTok/farm screenshot is not enough. Never invent a target, run a live action blindly, or turn missing target inventory into `BLOCKED_AT_GATE_0`.

## Correct closeout sequence
1. Freeze the exact candidate and outside-scope dirty paths.
2. Determine whether the current task explicitly names an authorized live target, requests real-device validation, or begins with user-provided incident evidence that identifies a machine/target plus a concrete runtime failure being debugged. If none applies, record `CANARY_NOT_APPLICABLE` and continue.
3. If a target exists, resolve it canonically and run the canary; if resolution or canary fails, stop at the matching Gate 0 blocker.
4. Obtain an independent parseable review of the exact candidate.
5. Run focused tests and static checks.
6. Stage only named candidate files, verify the staged diff, commit, pull/rebase, push, and compare remote SHA.

## Cron/process race handling
A scheduled wrapper can relaunch a stale or broken invocation while closeout is in progress. Before every review, staging, commit, rebase, and push boundary:
- enumerate real processes using executable/path and parent chain;
- exclude the probe's own shell/process from matches;
- if a process owns the in-scope runtime/workbook path, stop only that exact process tree when authorized by the closeout scope;
- preserve unrelated cron wrappers, Gateway, and other project processes;
- recheck process absence and lock metadata after stopping.

Do not treat `tasklist`/`psutil` output that captured the inspection command itself as evidence of a live owner. Conversely, do not assume a cron relaunch is harmless: a live writer invalidates the frozen candidate until reconciled.

## Evidence discipline
- Worker completion is not reviewer approval; wait for a parseable `APPROVED` verdict bound to the current bytes.
- Offline regression tests do not substitute for a canary when the current task has an explicit authorized live target, but they are the correct verification evidence when `CANARY_NOT_APPLICABLE` applies.
- Stale workbook lock files must be handled by the repository's official recovery path; never delete lock JSON or journal files manually.
