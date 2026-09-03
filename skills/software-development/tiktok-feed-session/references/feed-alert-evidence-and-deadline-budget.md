# Feed alert evidence and deadline budget

## Exact-attempt triage

Record before forming a hypothesis:

- run ID, machine, device/serial, account, timestamp, exact step
- adjacent `log.jsonl` events before and after the alert
- exact attempt directory with both `ui.xml` and `screen.png`
- expected tab, detected tab, focused package, XML error, safety status
- retry/probe count and enclosing `max_duration_seconds`

Open the XML and screenshot from the same attempt. `xml_available=true`, a classifier result, or an artifact directory is not proof that the evidence was inspected.

## Valid feed rejected as wrong tab

If XML and screenshot both show a real TikTok video feed but a different selected top tab than requested, classify it as a navigation/tab drift, not "feed unavailable". Recover only at the boundary that owns the expected tab, require safe package and real XML evidence, and record:

- `status=degraded` or equivalent continued state
- `feed_drift_recovered=true`
- `feed_drift_from=<expected>`
- `feed_drift_to=<observed>`

Do not weaken the general `_is_feed_confirmed` predicate or accept classifier-only evidence.

## Deadline starvation in popup probing

Compare timestamps around the timeout. If a later capture raises `run plan max_duration_seconds exceeded` after an earlier valid feed capture, inspect the blind-popup/recovery loop. A caller that passes the exact post-swipe XML should not recapture every rule after an initial miss unless an actual popup action was found. Make that retry policy explicit at the post-swipe call site and add a regression assertion; preserve retry behavior for other checkpoints unless independently justified.

## Verification boundary

After the patch, run the focused feed tests in a fresh process, then compile and `git diff --check`. If broader tests fail in pre-existing or unrelated dirty code, report them as separate blockers; do not claim the whole suite is green and do not edit adjacent paths merely to remove those failures.
