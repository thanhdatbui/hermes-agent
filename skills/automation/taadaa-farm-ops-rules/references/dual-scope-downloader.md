# Dual-scope downloader: VN worker + Admin all-source worker

> Coordination rule: allocate public channel/source, not individual videos. A normalized `source_url` claim excludes that source on the other machine; occasional video duplicates from discovery or sync races are accepted when the user chooses simpler source purity. Keep hashes local only.

Use this reference when a production downloader must keep a Vietnamese worker running while adding a second worker for another machine or a broader language/source policy.

## Contract

- Existing VN entrypoint remains the default and must keep its current behavior.
- The new mode is explicit (`--all-languages` or a dedicated wrapper); never infer it from the machine name.
- The task is complete only when the new mode is independently testable and the existing worker is still alive and making progress.

## Isolation matrix

| Concern | Kibe/VN worker | Admin/all-source worker |
|---|---|---|
| entrypoint | existing downloader | dedicated wrapper/launcher |
| local runtime | Kibe runtime | separate Admin runtime |
| SQLite state | Kibe `state.db` | separate Admin `state.db` |
| output root | Kibe output | separate Admin output |
| reports/cache/tmp | local to Kibe runtime | local to Admin runtime |
| cross-machine coordination | shared global ledger | same shared global ledger |
| ledger identity | canonical `Kibe` | canonical `Admin` |

Never use a shared SQLite database as a coordination mechanism between machines. The global ledger is the cross-machine layer; local state remains local.

For cross-machine allocation, the unit is the public source/channel: read the shared ledger and claim `source_url` before discovery/download; skip any source already claimed by either machine. Do not use global `video_id` or cross-machine perceptual hashes as the primary distribution mechanism when source purity is the requirement. Those checks add unnecessary coordination complexity. Keep perceptual hashes local as a safety check against accidental duplicates within the current worker, not as the source allocator. Record a verifiable `source_claimed` entry and treat OneDrive/file-sync propagation as the remaining race window.

## All-language policy boundary

All-language mode may remove only the Vietnamese-language acceptance and VN discovery bias:

- skip the Vietnamese Whisper acceptance gate;
- do not force `geo_bypass_country=VN`;
- do not force `region=vn-vi` in public search;
- preserve duration, exclusion, media download, duplicate/perceptual-hash, metadata stripping, `ffprobe`, clean-MP4 and ledger checks.

“All-language” is a policy mode, not proof that the manifest contains foreign sources. Inspect and count the manifest before claiming international coverage. If the source pool was built from Vietnamese niches, broadening the downloader does not create new international sources.

## Launcher safety

- Never guess the Admin folder range or hard-code a starting folder from stale context.
- Require `--start-folder`, validate it against `1..total-folders`, and make the operator choose the non-overlapping range.
- Default to `parallel=1` for a new machine until a canary proves higher concurrency is safe.
- Pass the canonical `--ledger-machine-id` and the shared ledger path explicitly.
- Do not start the Admin worker merely because the launcher exists; creation and live execution are separate approvals.

## Verification loop

After each code/test edit, run a fresh focused test in the same turn. Cover at least:

1. default entrypoint selects Vietnamese mode;
2. explicit all-language entrypoint selects all mode;
3. all mode does not call Whisper or force VN geo/search region;
4. VN mode still calls/retains its language gate;
5. wrapper injects the flag once;
6. launcher requires an explicit start folder and uses isolated paths/ledger identity.

Then run `py_compile`/import checks and `git diff --check`. Independently verify the existing worker with process state plus a changing log timestamp/size and current DB timestamps/counts. A wrapper exit code or an old report is not proof of active progress.

## Reporting

Use a short Vietnamese report with facts only: files/paths changed, focused test result, isolation paths, current-worker evidence, and blockers. Do not say “all sources” unless the manifest inventory supports that claim. Do not claim deployment or live execution when only the launcher was tested.

## Related implementation reference

The reproducible pattern and regression checklist are in this file; keep session-specific paths and command output here rather than bloating the main skill.