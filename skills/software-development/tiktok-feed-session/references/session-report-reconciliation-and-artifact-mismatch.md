# Session report reconciliation and artifact mismatch

## Trigger
Use when a watchdog summary lists machines as failed, but machine-scoped run artifacts or manifests disagree, or when natural follows are reported separately from cross/module follows.

## Evidence-first procedure
1. Locate the exact live run artifact by date/cluster/row/session, then read `summary.txt`, `run_manifest.json`, and the relevant `log.jsonl` entries. Do not infer from the Telegram summary alone.
2. Build a per-machine table with `final_status`, swipe count, reason, stop_reason, and capture/ADB errors. A current Launcher/Sleep screen is only live-state evidence; it does not overwrite the historical run artifact.
3. Separate `report-listed-fail`, `artifact-confirmed-fail`, and `artifact-confirmed-success`. A machine listed as failed but recorded `success` in the same run is a report/aggregation mismatch, not automatically a feed-flow failure.
4. Treat missing traceback as `no Python traceback observed`, not as proof that the run was healthy.

## Follow reconciliation contract
Keep three distinct values per account:
- `natural_follow_detected`: feed detector count.
- `cross_follow_action_reported`: module/action result count.
- `web_following_delta`: server snapshot delta with a valid pre-session baseline and post-session snapshot.

The expected reconciliation target is the union of machines with cross follows and machines with natural follows. Do not early-return just because the cross-follow success list is empty. For each machine, expected reported count is `cross_followed + natural_follow_detected`; keep the two categories separate in the human report. Missing baseline, missing snapshot, or failed crawl is `pending/missing evidence`, never an automation failure.

## Focused regression pattern
For a code fix, use an offline mocked test where `fl_success=[]` and 2–3 machines have positive `natural_follows`. Assert that all usernames are passed to the tracker and that the rendered result preserves the natural/cross distinction. On Windows, create SQLite fixtures under `TemporaryDirectory`; do not keep a `NamedTemporaryFile` open while connecting to it.

## Pitfalls
- Do not use a feed failure from the newest artifact to explain an upload/verification failure when the artifact has no upload events.
- Do not call a web `+0` delta proof of failed follow without baseline, latest snapshot, timestamp, crawl status, and per-account action evidence.
- Do not repair a report mismatch by changing device state or retrying live machines before proving the aggregation contract.
