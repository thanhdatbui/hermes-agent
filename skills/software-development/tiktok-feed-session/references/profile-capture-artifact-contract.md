# Profile capture artifact contract

## Incident pattern
A consumer-side gate added in `6dfd722` required `xml_path`, `screenshot_path`, and `capture_artifact_status=complete`, while the active legacy `automation-core` producer exposed only `artifact_path`. The result was a fleet-wide `profile verification capture-artifact-incomplete` classification even when capture XML itself was returned.

## Correct boundary

1. Read exact producer metadata from the same capture attempt.
2. If only `artifact_path` exists, derive `artifact_path/ui.xml` and `artifact_path/screen.png`.
3. Treat metadata as provenance, never as proof.
4. Require exact XML and screenshot files to exist and be non-empty.
5. Require persisted XML to match the XML being parsed using line-normalized comparison (`line.strip()` / strip blank lines) to avoid false positives caused by `\r\n` vs `\n` line endings between disk writes and ATX in-memory captures.
6. Validate PNG structure, chunk bounds, CRCs, IHDR dimensions, IDAT presence, and terminal IEND.
7. Parse the persisted XML successfully.
8. Only then normalize legacy status to `complete` / `xml_available=true` and classify profile identity.

Missing or invalid artifacts must remain fail-closed as `capture_artifact_missing`/UNPROVEN. Never weaken production validation just to satisfy mocked fixtures.

## Delayed alert wave vs new regression triage
When a batch run is launched prior to a fix commit, worker processes already running in memory continue executing the old code until completion (often 15-25 minutes later at the `verify_profile` stage).
- Do not assume an alert arriving after a commit means the fix failed or regressed.
- Check the batch launch timestamp in `wmic process` / `log.jsonl` against the git commit timestamp.
- If the running process started before the commit, verify artifacts offline against current HEAD code before taking any action.

## Regression matrix

- Modern metadata: explicit XML/screenshot paths + `status=complete` + valid files => accepted.
- Legacy metadata: `artifact_path` only + valid derived files => accepted.
- Legacy metadata: missing derived file => rejected.
- XML differs from persisted capture => rejected.
- Malformed XML => rejected.
- Truncated/invalid PNG => rejected.
- Stale previous-attempt metadata => rejected or replaced by current attempt metadata.

## Verification

Focused command:

```bash
PYTHONPATH=".;python_runner" python -B -m pytest -q -p no:cacheprovider python_runner/tests/test_feed_swipe_smoke.py -k 'profile_capture or verify_profile'
```

Do not infer runtime producer version from requirements or current source alone; correlate live process, target `log.jsonl`, and source chronology when investigating a live alert.
