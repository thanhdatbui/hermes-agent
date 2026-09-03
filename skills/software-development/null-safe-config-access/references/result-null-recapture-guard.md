# Result-Null / Recapture Guard

## Trigger

A flow reports a runtime `'NoneType' object has no attribute 'get'` after a
popup/recovery handler. Do not assume the source is YAML config: inspect the
call-site and the persisted run record first.

## Reproduction shape

Use the contradictory handler result that exposed this bug:

```python
dismissed = True
after_attempt = None
```

The success flag alone is not sufficient. The downstream code needs a fresh
recapture dictionary before it can read `detected_screen`, `focus_package`, or
`artifact_path`.

## Safe guard

Place the guard immediately before the first dereference:

```python
if not dismiss.dismissed or dismiss.after_attempt is None:
    if dismiss.dismissed:
        row["popup_dismissed"] = False
        row["reason"] = "popup dismiss reported success but recapture was unavailable"
        row["safety_reason"] = row["reason"]
        return row
    # preserve the existing bounded recovery/manual-needed path for a normal
    # dismiss failure
```

Keep the behavior fail-closed: no success status and no follow-on action when
recapture evidence is missing. Do not synthesize an empty attempt, because an
empty dict would hide the evidence failure and could turn a popup into a false
success.

## Regression test shape

- Build a popup row with `detected="manual-needed:popup"` and one prior attempt.
- Patch the popup dispatcher to return `dismissed=True`, `selector=None`, and
  `after_attempt=None`.
- Call the narrow row handler, not the live/device runner.
- Assert the same row is returned, `popup_dismissed` is false, and the explicit
  recapture-unavailable reason is recorded.

## Verification

Run the focused regression with the repository's Python environment. If the
runner imports a broken or shadowing Pillow installation from another Hermes
environment, isolate `sys.path` so the repository/automation environment is
used; this is a verification setup detail, not a reason to weaken the test.
Then run the owning test class, compile the changed files, and run
`git diff --check`. Do not run a live device/farm action for this unit fix.
