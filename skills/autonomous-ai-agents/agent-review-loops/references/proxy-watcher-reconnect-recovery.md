# Proxy watcher reconnect recovery

## Evidence-first diagnosis

For a per-device proxy watcher, distinguish these stages with a sanitized per-machine JSONL/event artifact:

1. Worker started / monitoring entered.
2. Android online and boot-id observed.
3. Startup, reconnect, or boot-id-change event detected.
4. Event lock acquired, timed out, or safely skipped.
5. Readiness passed/failed.
6. Proxy action began, succeeded, or failed.
7. `tun0` UP and Android VPN connected proof.

A scheduled task being enabled, a tray process being alive, or launcher stdout showing the command is not proof that a particular machine received `START_VPN`.

## Lock and readiness rules

- A proxy-recovery event is the action that restores a VPN; its event lock must not require that VPN to already be ready. Use a narrowly scoped readiness bypass only for that event lease, while retaining machine+serial exclusivity.
- A dead retained `recovery`/`handoff` lock may be claimed only when consumer preflight eligibility exactly matches the central lock implementation. Do not approximate a dead-owner check.
- A live or uncertain owner must get bounded waiting and a `SKIPPED_DEVICE_LOCKED` event, never an infinite wait and never unsafe takeover.
- A runner's generic `DONE` is report creation; inspect its per-machine summary before declaring success.

## Resilience rules

- A readiness, mapping, or telemetry exception must not silently terminate a long-lived worker. Emit a distinct sanitized error event, use bounded backoff, then resume monitoring when appropriate.
- Mapping serial mismatch is not lock contention. End/reload the affected worker rather than continuously polling a stale serial.
- Keep telemetry names one-to-one with root causes. Examples: `WATCH_EVENT_LOCK_TIMEOUT`, `WATCH_EVENT_READINESS_FAILURE`, `WATCH_MAPPING_RELOAD_ERROR`, `WATCH_PROXY_SET_FAILURE`, `WATCH_EVENT_LOCK_ACQUIRED_TELEMETRY_ERROR`.

## Live validation recipe

1. Verify the full watcher process tree.
2. Confirm the target has no live lock; audit dead retained locks before takeover.
3. Reboot the one authorized machine under a central recovery lease; wake/swipe after `boot_completed`.
4. Release the reboot lease so watcher can acquire its event lease.
5. Poll for a **fresh** target event artifact and independently verify `tun0` plus Android VPN state.
6. If VPN is absent, use the new telemetry stage to route the next code fix; do not blind-retry reboot or `START_VPN`.
