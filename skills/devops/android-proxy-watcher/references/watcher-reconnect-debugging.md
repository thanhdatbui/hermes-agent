# Watcher reconnect debugging (Windows Android farm)

## Proof hierarchy

Do not infer current behavior from another machine or old artifacts. For one target and one watcher generation, verify:

1. Scheduled Task action and enabled/running state.
2. Tray → watcher launcher → `gan_proxy_fleet.py watch` process tree.
3. Fresh target `watch-events.jsonl` in the current runtime run.
4. `tun0` plus Android VPN `CONNECTED/CONNECTED` (not merely Wi-Fi).
5. Central machine/serial lock release or a retained lock with target-specific reason.

## Common circular dependency

Normal consumer locks can require proxy readiness. A proxy-recovery watcher event needs exclusivity **before** it calls `START_VPN`; requiring readiness on that event lease produces:

`VPN off → readiness-gated lock rejected → watcher cannot START_VPN`.

Use readiness bypass only for the watcher’s narrowly scoped per-event recovery lease. Normal login/account/device consumer locks must retain readiness checks.

## Per-event lock contract

- Dead retained eligible lock: request central takeover; central core remains the atomic final check.
- Live-owner lock: bounded wait only, write `SKIPPED_DEVICE_LOCKED`, do not call proxy assignment, then keep monitoring.
- Never retain an idle watcher lock.
- Keep consumer preflight eligibility consistent with the central lock owner-active/status/PID contract.

## Worker robustness

A long-lived worker must record sanitized telemetry transitions: worker start, monitor start, event detect, mapping refresh, lock result, readiness result, proxy-set begin/success/failure, and telemetry-write error.

- Transient readiness/watch exceptions: bounded backoff then resume monitoring.
- Mapping serial mismatch: end/restart that worker with refreshed mapping; do not poll stale serial forever.
- Maintain `max_events` correctly across restarts.
- Give telemetry stages distinct names so operators can distinguish readiness, lock, mapping, proxy, and instrumentation failures.

## User preference

When enabling/restarting watcher infrastructure, do not start unrelated TikTok login/feed/registration schedules unless their task/tray code has been checked and proven not to start them.
