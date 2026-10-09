# Machine-scoped live canary gate

For a single-device incident, a successful workbook/DB reconciliation does not authorize a canary while a live fleet owner still holds that device.

## Required evidence

- Exact target serial and current `inspect_machine.py <N>` output.
- Workbook physical row plus runner slot/index, with the conversion proven from the actual runner command.
- Direct DB result for the target machine/slot/account.
- Target-only lock JSON, owner PID liveness, exact command line, run/lock ID, `owner_active`, `pinned`, authorization, heartbeat age, and TTL.
- Exact current target artifact path, or an explicit statement that the target machine artifact has not been emitted yet.

## Decision rule

Proceed only if mapping is unique and the target lease is absent/released canonically. A root `.canary_pending` marker with `reason: fleet_busy` is a blocker signal. Never delete the lock, force-kill the owner, or use a parent-lock option as an override.

## Report shape

Use `MACHINE_SCOPED_BLOCKER` when blocked. Name the lock owner and exact missing artifact/mapping evidence. Do not report a generic “worker lacked context” blocker and do not broaden to a fleet scan.
