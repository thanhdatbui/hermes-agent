# Live recovery preflight and bounded reclaim

Use this recipe for a user-authorized recovery run against an explicit machine list.

## Required order

1. Read the repository's `AGENTS.md`, `HANDOFF.md`, and `PROJECT_RULES.md` before device work. Use the existing runner/handler; do not edit source for a live-only recovery task.
2. Resolve the current machine→serial mapping from the approved safe workbook/config. Compare it with the lock/artifact identity before using a device. A mismatch is a hard stop.
3. Check both ownership planes before any action:
   - shared machine and serial lock files, including `status`, `owner_active`, `pid`, and `lock_id`;
   - live processes for the nurture runner, recovery watcher, and other consumers such as `tiktok_workflow --machine N`.
   Lock-store absence is not proof that a device is free.
4. Capture a fresh screenshot and UI XML for **every named target** before recovery. Store an absolute artifact path per machine. Use bounded timeouts; if UI capture fails, preserve the screenshot/error artifact rather than retrying blindly.
5. Read the current recovery ledger per target. If a target has an active recovery/reservation or live owner, do not run a second recovery. Reconcile it or wait for its terminal event. A historical `FINAL_BLOCKED`/`MANUAL_REQUIRED` is not active; confirm with the latest ledger event and live process/lease state.
6. Classify the live surface from the fresh capture. Stop fail-closed on login, OTP, 2FA, CAPTCHA, security/account-credential, phone-entry, payment, or other sensitive/manual surfaces. Preserve screenshot, XML, runner artifact, and the exact blocker stage.
7. Group targets by the runner's required account-row/slot input. Run separate bounded commands when the target list spans different account rows; never silently use one row for all machines.
8. Use only the named target list, guarded takeover, and the existing bounded runner. Keep concurrency bounded. Do not add like/follow or unrelated actions unless explicitly requested.
9. After each runner completes, inspect each machine independently: `summary.txt`, `run_manifest.json`, `log.jsonl`, final screenshot/XML/recovery artifacts, and `recovery_lock_handoff.json`. Batch exit code is not proof.
10. Report success only when the machine has verified feed/focus evidence, the requested bounded swipe count, and released machine+serial locks. For manual/blocked results, keep the blocked lock and return absolute artifact paths.

## Special ownership cases

- **Active ledger recovery:** never overlap it, even if a stale-looking lock file exists. Wait/reconcile until terminal, then re-check ownership before taking over.
- **Stale reservation from a killed batch:** reclaim only when same-host owner PID is independently proven dead and the reservation/lock evidence identifies the exact target. Use the runner's guarded takeover; do not delete lock files by hand.
- **Inactive `blocked`/`handoff` lock:** preserve evidence and reclaim only through the user-authorized exact-scope takeover path. Do not broaden scope.
- **Sensitive surface:** existing benign-popup handlers do not override a user prohibition on security-sensitive/account surfaces. Never tap a security prompt, phone-entry field, `Continue`, login, or credential control.

## Reporting shape

For each machine, report `SUCCESS`, `MANUAL_REQUIRED`, `FINAL_BLOCKED`, or `SKIPPED_LOCKED`, plus:

- serial identity (redacted if needed),
- absolute summary/manifest/log/handoff paths,
- final swipe count when applicable,
- lock handoff (`released` vs retained/blocked),
- exact safety blocker and preflight screenshot/XML paths when not successful.

The session-specific evidence and command patterns are in this file's companion artifact paths; do not treat old artifacts as current proof—always recapture first.
