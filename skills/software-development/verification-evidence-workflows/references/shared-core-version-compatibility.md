# Shared-core version compatibility: strict wire-contract regression

Use this recipe when a consumer is pinned to an older shared-core version and a
newer status/exception/API shape has accidentally entered the consumer code.
The goal is compatibility at the boundary without changing lock or live state.

## Evidence-first sequence

1. Record the exact dependency artifact used by the runner, not merely the repo
   requirements pin:

   ```text
   import importlib.metadata as metadata
   import automation_core
   print(metadata.version("automation_core"))
   print(automation_core.__file__)
   ```

2. Snapshot scoped status, mtimes, hashes, and the existing diff. Ignore unrelated
   dirty paths; do not revert or stage them.

3. Make the test double stricter than the old permissive mock. For a lease/status
   seam, reject unsupported wire values explicitly so the test fails for the real
   compatibility reason rather than accepting any string.

4. Run the exact regression node before production code changes. The desired RED
   is a contract mismatch, not a collection error or a fake setup failure.

5. Change only the production wire value/adapter seam required by the pinned
   dependency. Preserve the surrounding behavior: successful release remains
   successful release; failed startup retains a handoff; no workbook/state/live
   operation is added.

6. Run the focused node with the exact dependency artifact, then compile and
   `git diff --check`. Run the broader suite when affordable, but report focused
   proof and suite proof separately.

## Fresh ad-hoc verifier on an `unverified` harness

Create the verifier outside the repo with an OS-safe path:

```python
import tempfile
path = tempfile.NamedTemporaryFile(
    prefix="hermes-verify-", suffix=".py",
    dir=tempfile.gettempdir(), delete=False,
).name
```

In one evidence window, write it, run the focused pytest node and any fake-only
contract assertions, then delete it in `finally`/shell cleanup. The verifier must
not touch devices, locks, accounts, workbooks, credentials, or live processes.
Confirm the exact temp path is absent afterward. Label the result **Ad-hoc
verification: PASS**; it is not equivalent to a full-suite result.

## Example strict lease seam

A permissive fake can hide a shared-core mismatch:

```python
def finish(self, *, succeeded, failure_status):
    self.finish_calls.append((succeeded, failure_status))
```

Make the supported contract executable:

```python
def finish(self, *, succeeded, failure_status):
    if failure_status != "blocked":
        raise ValueError(f"unsupported device lock status: {failure_status}")
    if succeeded:
        raise AssertionError("failure path cannot finish as succeeded")
    self.finish_calls.append((succeeded, failure_status))
```

Then assert both the call and the result details:

```python
assert lease.finish_calls == [(False, "blocked")]
assert result.details["lock_release"]["device"] == {
    "action": "retained_handoff",
    "run_id": result.details["lock"]["run_id"],
    "status": "blocked",
}
```

## Pitfalls

- Do not infer the imported version from a repository pin; print the actual
  distribution version and module path.
- Do not use a permissive mock for compatibility work; it can make the test pass
  while production still sends an unsupported status.
- Do not call the full suite instead of first proving the focused RED and GREEN.
- Do not leave verifier scripts in `%TEMP%`; stale verifier paths can keep the
  harness marked unverified and obscure which evidence is fresh.
- Do not call a retained lock "released". Assert the handoff/blocked status and
  ensure success release behavior remains distinct.
