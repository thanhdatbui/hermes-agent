# Focused account-switcher fixture fidelity

## Failure pattern

The account-switcher smoke path can capture XML more than once for one attempt:
initial capture, settled capture after animation, and recovery captures after
BACK or profile re-navigation. A short mock `side_effect` then raises
`StopIteration`, which is a stale fixture rather than a production failure.

A second stale-fixture shape is a re-navigation mock that keeps returning the
old profile/switcher XML. The production helper correctly rejects that state as
not a profile root, so the test never reaches the intended missing-account
classification.

## Minimal repair recipe

- Trace the helper's exact capture labels and count calls for the failing branch.
- Add the missing repeated XML capture to the existing `side_effect` sequence.
- For re-navigation, return a valid profile-root XML at the navigation call, then
  return the switcher XML for the subsequent switcher observation.
- Preserve assertions that distinguish a recognized switcher missing the expected
  account from a login/manual-needed screen.
- Do not change production logic when the production branch already implements the
  distinction.

## Verification contract

Run only the requested focused command, bounded by the user's timeout:

```bash
PYTHONPATH= python -m pytest -q -p no:cacheprovider \
  python_runner/tests/test_feed_session_smoke.py -k account_switcher_missing
```

Report the real pytest pass output and scoped `git diff --numstat` for both the
fixture file and the production file. Do not commit. Preserve unrelated dirty
files.
