# Alert dedupe: one producer alert per machine per feed session

## Incident shape
A feed runner can be relaunched multiple times during one logical feed-session window. Each process may independently finish the same machine as failed/manual-needed or hit the hard outer watchdog. Calling `send_farm_machine_alert()` directly from each path creates repeated Telegram alerts even though the watchdog's `reported_sessions` state only deduplicates summary reports.

## Durable claim contract
Use a stable session key, not the per-process UUID:

```text
logical_day + ca/phien + machine
```

When the live launcher creates row folders such as `runtime/.../live/2026-08-24/row-2-060028`, `row-2-063028`, and `row-2-073031`, derive the logical day from the parent and the session window from the row timestamp. If the flow has an authoritative manifest/session index, prefer that over heuristics.

Store claims above individual row run directories, for example:

```text
<logical-day-root>/alert-claims/<session-key>/machine_<N>.claimed
```

Claim with an atomic create (`os.open(path, O_CREAT | O_EXCL | O_WRONLY)`). Only the caller that successfully creates the marker may invoke the Telegram producer. `FileExistsError` means the alert was already sent and must be silently skipped. If the claim store cannot be created/read, fail closed rather than allowing duplicate alerts.

## Required wiring
Use one helper from every producer branch:

- terminal child result where `final_status` is not `success`/`degraded`;
- hard outer watchdog timeout;
- any later producer branch added to the same multi-machine flow.

Do not put the claim only in the watchdog: the watchdog summary and machine alert have different lifecycles and state. Do not put it only in memory: cron relaunches and separate processes will bypass it.

## Regression matrix
1. Same machine, same session, same process: first claim true, second false.
2. Same machine, same session, two different `row-HHMMSS` run folders: first true, second false.
3. Different machines, same session: each machine claims independently.
4. Same machine, next session window: claim is true again.
5. Claim collision and filesystem error: no Telegram call on the duplicate/error path.
6. Run focused tests, then the full consumer test file; report pre-existing failures separately. Always run `python -B -m py_compile` and `git diff --check` before claiming completion.
