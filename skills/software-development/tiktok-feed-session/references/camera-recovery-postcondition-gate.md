# Camera Recovery Postcondition Gate

## Trigger
Use when feed/profile verification reports `camera-recovery-failed`, or when the Profile navigation path detects TikTok's Camera/Creation screen.

## Root-cause pattern
A BACK/close command succeeding at the transport layer is not proof that the Camera screen closed. The old flow sent `KEYCODE_BACK`, ignored the dismiss result, and immediately retried Profile navigation. If Camera remained, the later failure was flattened into a generic `camera-recovery-failed`.

## Safe recovery sequence
1. Detect Camera from the current XML using at least two independent Camera/Creation markers; do not trust a single marker.
2. Execute the existing semantic close-button/BACK handler. Do not clear app data, restart ADB, or use blind coordinates.
3. Check the dismiss result. If `dismissed` is false, stop fail-closed and preserve the handler reason.
4. Wait for the UI transition, then capture a fresh XML **and** the matching screenshot artifact.
5. Validate the fresh artifact: exact `ui.xml`, valid `screen.png`, parseable XML, and metadata/file consistency.
6. Re-run the Camera detector on the fresh XML. Only continue if the overlay is absent. If the overlay remains after a successful dismiss, treat that as a possible asynchronous UI transition: re-issue the same narrowly safe dismiss handler once, then recapture and revalidate.
7. Bound the recovery attempts (the consumer currently allows two dismiss/recapture attempts). A persistent overlay, unavailable recapture, failed dismiss, or incomplete artifact must stop fail-closed; never retry Profile navigation on unverified state.
8. Only then retry Profile navigation and capture/validate a fresh Profile artifact. Never navigate or verify identity while Camera is still present.

## Failure classification
Keep the most specific evidence-backed reason instead of overwriting it with a generic final label:
- `camera dismiss failed: <handler reason>`
- `camera dismiss recapture unavailable`
- `camera overlay remained after dismiss recapture`
- `capture-artifact-incomplete` with the validator reason
- `profile navigation retry failed: <navigation reason>`

The final generic `camera-recovery-failed` status is acceptable as a status field, but `reason`, logs, and recovery records must retain the specific failure.

## Regression tests
Cover both paths:
- BACK reports success but recapture still contains Camera: no second Profile navigation; fail-closed with the remaining-overlay reason.
- Recapture no longer contains Camera: retry Profile, validate the new artifact, and allow identity verification to proceed.

Do not claim live-machine success from unit tests. A real canary still requires fresh device XML/screenshot evidence and the repository's live verification gate.
