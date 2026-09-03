# Profile verification review gate

## Why this reference exists
A profile-verification patch can look correct because focused tests pass while the exact artifact contract is still incomplete. Use this review gate before commit/push.

## Required review questions
1. Does every classification path require `capture_artifact_status == "complete"`?
2. Are both `xml_path` and `screenshot_path` non-empty, existing files from the same attempt?
3. Is the persisted XML the exact XML used for parsing, and is the screenshot a valid PNG?
4. Does malformed/empty XML return `capture_artifact_missing`/`unproven` instead of raising or becoming mismatch?
5. After each retry, are metadata, XML path, screenshot path, and parsed XML replaced together?
6. Can stale metadata or a previous complete capture mask a failed current capture?
7. Do fixtures model complete artifacts, or explicitly mock the validator for a unit that is not testing persistence?
8. Was an unrelated behavior change removed or separately justified with its own regression test?
9. Was a fresh independent review run against the exact staged diff after fixes?

## Closeout gate
- `REJECT` means no commit and no push.
- Fix all high/medium findings.
- Run focused tests, compile, and `git diff --check` again.
- Re-review the exact staged candidate.
- Preserve unrelated dirty files; stage explicit paths only.
- Report blockers honestly; do not convert a partial test pass into approval.

## Evidence terminology
- `confirmed`: exact log + XML + matching screenshot support the claim.
- `excluded`: exact evidence rules out the candidate.
- `unproven`: required artifact is missing, malformed, stale, or timestamp-mismatched.
