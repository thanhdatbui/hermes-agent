# Scheduled telemetry and socket polling

Reusable pattern for cron workers that start an external profile/service, wait for a debug socket, and persist both event history and daily aggregates.

## Failure pattern

A worker records an event with `reason`, then the completion loop rebuilds `events` while updating counters. With concurrent futures, that second write can load a stale snapshot and overwrite a previously recorded event. A separate report may then render `reason` with `dict.get("reason", fallback)`: the fallback is not used when the key exists with an empty string, so the output ends in a blank colon.

## Correct state split

- `record_event(...)`: append-only bounded history (`events[-N:]`), protected by a process-local lock.
- `update_daily_summary(...)`: mutate only aggregate fields (`used_proxies`, success IDs, retry/block lists); do not touch `events`.
- Make aggregate list updates idempotent (`if email not in values`) so worker completion order cannot create duplicates.
- Return a bounded `reason` in every result that can enter a report. For legacy state, render `(reason or "").strip() or status or "Unknown"`.

## CDP/debug socket polling

After the start API returns `host:port`, poll with a monotonic deadline instead of a fixed sleep:

```python
def wait_for_socket(address, timeout=6.0, interval=0.5):
    host, port_text = address.rsplit(":", 1)
    deadline = time.monotonic() + timeout
    while True:
        try:
            with socket.create_connection((host, int(port_text)), timeout=interval):
                return True
        except (OSError, ValueError):
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval)
```

A polling timeout should remain observable in the normal error/telemetry path. Do not add an unbounded retry loop or silently classify it as success.

## Focused regression matrix

1. Record an event, update the daily summary, reload state, and assert the event count/reason remains unchanged.
2. Feed the report a current event with `reason: ""`; assert the rendered detail uses its status rather than an empty reason.
3. Exercise the polling helper with a local listening socket and a closed port; assert success and bounded timeout behavior offline.
4. Run `python -m py_compile`, scoped `git diff --check`, and the focused test module after the final edit.

## Runtime sync evidence

Copy the repository scripts to the Hermes runtime directory only after focused tests pass. Run the repository's sync watchdog, then compare source/runtime hashes. Sync success proves deployment parity, not behavioral correctness.
