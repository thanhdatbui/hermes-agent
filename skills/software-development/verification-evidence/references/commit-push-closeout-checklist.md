# Commit/push closeout checklist

Use this after a code change receives an approved closeout review.

## Evidence sequence

1. Inspect `git status --short` and separate authorized paths from unrelated dirty/untracked paths.
2. Run the final focused tests against the live bytes.
3. Run the closeout gate on the exact scoped paths; require exit code 0 and `Verdict: APPROVED` with score >= 85.
4. Stage only the authorized source and test paths. Never stage a helper test, temporary script, `docs/ai/workflows/`, or unrelated changes merely to make Git accept the commit.
5. Commit directly from the coordinator or an explicitly authorized release lane. Capture the new SHA.
6. Push through the repository's existing authenticated remote/branch. Do not add credentials to source, tests, or ad-hoc helper scripts.
7. Read back the remote branch SHA and require it to equal the commit SHA before reporting `DONE`.

## Failure classification

- Closeout approved, commit failed: `INCOMPLETE — approved but not committed`.
- Commit succeeded, push failed: `INCOMPLETE — committed locally, not published`.
- Push command returned zero but remote SHA was not checked: `UNVERIFIED`, not DONE.
- A test attempts `git add`, `git commit`, or `git push`: reject the test as a release-side-effect violation and remove it from the candidate.

## Anti-patterns

- Do not use a pytest test as a deployment launcher.
- Do not claim push success from a worker summary, an old session, or a local commit log.
- Do not create a guessed authenticated URL or expose a token in a file.
- Do not stage all changes to bypass unrelated dirty files.
