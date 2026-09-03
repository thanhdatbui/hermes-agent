# Scope-expanded closeout for downloader work

Use this reference when the user explicitly authorizes committing dirty paths beyond the original implementation allowlist, especially for a downloader/non-device runtime change.

## 1. Treat the authorization as a scope expansion

Do not translate “commit all non-conflicting changes” into `git add .` or `git add -A`. Freeze the current `HEAD`, branch/upstream, status, and active processes. Audit each additional path independently and keep a path-level decision:

- **Include:** parseable, public/non-sensitive, no active writer conflict, and clearly intentional.
- **Exclude:** credentials/cookies/tokens, local state, logs, caches, runtime output, generated artifacts with no reproducible source, unexplained binaries/models, or tests/manifests whose required fixture is missing.
- **Needs decision:** ownership or content cannot be established safely.

For JSON/source manifests, parse the file and inspect field names and values for secrets before staging. For binaries, record type/size/hash and purpose; do not infer that a model or archive is safe merely because it has a familiar extension.

## 2. Validate tests and fixtures before claiming green

A newly added test is not a passing deliverable if it references a manifest or fixture absent from the repository. Run the exact focused tests; if one fails with a missing fixture or `StopIteration` caused by absent test data, classify it as a real blocker for that path and exclude the broken test from a “verified” commit unless the user separately authorizes fixing the fixture.

Do not repair an unrelated historical test during closeout just to make the suite green. Keep the failure evidence and state the excluded path.

## 3. Downloader canary versus device/farm canary

The mandatory device canary is for device/farm changes with a real machine/row target. For a downloader-only change with no device target, do not launch a feed-session command or touch phones merely to satisfy the gate. Use an isolated production-equivalent downloader canary instead:

- temporary state DB, runtime, output, and ledger directories;
- explicit all-language/source mode and a bounded folder range;
- `dry-run` or another no-media-write mode when validating entrypoint/source allocation;
- never the production Kibe state, output, or shared ledger;
- inspect process state and artifacts after the run.

A timeout is **inconclusive**, not success and not automatically a reason to retry. Inspect for a still-running child, partial artifacts, and whether the active production worker was untouched. Do not recursively delete the temporary directory or retry a blocked destructive command without a fresh approval boundary.

## 4. Semantic downloader checks learned from review

Do not treat a printed `DONE`, a subprocess exit code, or a wrapper's apparent success as proof that the Python entrypoint returned the correct status. Run an in-process or subprocess canary that asserts the wrapper's return value is numeric `0`, creates the isolated state artifact, and leaves the shared ledger untouched in dry-run mode. This catches single-worker paths that accidentally return `None` because `return rc` exists only in a parallel branch.

Review the entire success path for symbols that are only used after media verification. An independent review caught a removed `append_record` import while the success path still called it; either remove the obsolete call when coordination is intentionally source-only or keep the import and test the path. Re-run the focused test and obtain a fresh reviewer verdict after every such fix.

For cross-machine downloader coordination, use a normalized `source/channel` claim as the shared primitive. Keep video IDs/perceptual hashes local unless the user explicitly requires cross-machine video dedupe; rare eventual-sync races are an accepted policy exception when stated. Discovery tests must reject search/browser results whose handle/author does not match the claimed source, and must assert that the parsed identifier is the video ID rather than the account handle.

## 5. Final candidate evidence

After the final audited path set is fixed, stage only those paths and verify `git diff --cached --name-status`. Run focused tests, compile/import checks, and `git diff --check` against the candidate. If the index changes afterward, prior evidence is stale. Review and test again before commit, then rebase, rerun quick checks, push, and verify the remote SHA.

## 6. Reporting

Keep the user-facing report short and factual: purpose, included paths, test/canary result, excluded paths with blocker, local commit SHA, and remote SHA. Never say “all dirty files committed” when any path was excluded; name the exact exclusions.
