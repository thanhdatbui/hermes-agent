# Interrupted 2FA batch and Gateway restart audit

## Incident pattern
A row-1 batch started one target, then the Phase B runner returned `BLOCKED_ENABLED_2FA_WITHOUT_RECOVERABLE_JOURNAL`. The orchestrator retried the same target and then repeated `DEVICE_LOCK_UNAVAILABLE` because a stale `handoff` lock remained. This is a stop-and-audit condition, not a retry condition.

## Safe audit order
1. Stop the orchestrator if the same machine produces three repeated blocked results.
2. Confirm no `run_capture_phase_b.py` process remains.
3. Inspect the machine and serial lock files. A lock with `status=handoff` and `owner_active=false` is stale only after verifying the project and process owner; do not delete it blindly.
4. Read encrypted DPAPI journals using the same Windows identity. Report only machine, source row, username, journal state, and timestamps; never print the secret.
5. Cross-check journal states with the workbook's 2FA column:
   - `WRITTEN` or `EMAIL_DISABLED` plus a 32-character Excel secret = persisted result.
   - `OTP_SUBMITTED` or `AUTHENTICATOR_CONFIRMED` with an empty Excel 2FA cell = urgent recovery candidate.
6. Verify the workbook modification time against the batch start time. This is supporting evidence only; the journal/workbook pair is authoritative.
7. Check the device's current activity/UI read-only before deciding whether it was in a password/change-info flow.

## Gateway restart interaction
Restarting Hermes Gateway preserves durable cron definitions. It can terminate a cron script that is actively executing at the exact restart moment; future scheduled ticks normally continue after the Gateway reconnects. Never restart during a live farm batch. After restart, verify `hermes gateway status`, the next scheduled tick, and absence/presence of the live worker process.

## Reporting language
Do not claim "no account risk" solely from a silent or blocked batch log. Say exactly which target was reached, which state was observed, whether an encrypted journal exists, and whether the workbook has a matching 32-character secret. Keep the report short and separate confirmed facts from remaining blockers.
