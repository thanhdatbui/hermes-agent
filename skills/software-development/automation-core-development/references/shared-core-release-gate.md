# Shared-core release gate: source → artifact → consumer

Use this checklist when a shared Python core is consumed through a pinned wheel or local artifact.

## Required evidence

1. **Source candidate**
   - Confirm the production diff and regression test are in the exact allowlist.
   - Run the focused core test against the intended source, not an ambient editable install.

2. **Artifact**
   - Bump the package version only after the source/test gate passes.
   - Build the wheel from that exact source tree.
   - Inspect wheel metadata for the new version.
   - Verify the wheel contains the changed production marker.
   - Hash the built wheel and the consumer-facing copied artifact; require equality.

3. **Consumer pin and provenance**
   - Update only the dependency pin to the new wheel.
   - Run consumer focused tests using the wheel in an isolated import path or temporary environment.
   - Print both distribution version and imported module path.
   - If the ambient interpreter still resolves an editable older checkout, report that as a dev-environment/rollout caveat; do not call the live runtime upgraded.

4. **Failure classification**
   - Test failures in the changed dependency seam are release blockers.
   - Failures rooted in unrelated concurrently dirty consumer files are classified separately and must not be “fixed” by broadening scope.

5. **Closeout**
   - Commit core source/test/version separately from the consumer pin.
   - Stage exact paths only.
   - Run focused tests and `git diff --check` after commit.
   - Fetch/rebase against the actual upstream, push non-force, and verify `git ls-remote` equals local HEAD for each repository.
   - Report preserved dirty paths outside scope.

## Common partial-delivery failure

A source fix plus passing unit tests is not the shipped fix when consumers install a wheel. The release is incomplete until the new artifact exists, the consumer pins it, and provenance is verified against that artifact.
