# StopIteration in ordered observation fixtures

## Reproduction pattern

A UI/state-machine unit test patches an observation helper such as XML capture with a finite `side_effect` list. The production flow may re-read the same screen while confirming a manual-needed terminal state. If the fixture contains fewer observations than the real path, pytest raises `StopIteration` before the behavior assertions run.

## Safe repair

1. Run the single failing node and inspect the traceback.
2. Count the actual observation calls in the retry/recheck path.
3. Add only the missing repeated fixture value(s), preserving the state sequence.
4. Keep safety assertions: expected manual-needed result, no forbidden account-switch tap, and no feed swipe.
5. Re-run the exact node after the final edit, then the neighboring focused tests/module.

Do not “fix” this by weakening production retry logic or replacing an ordered `side_effect` with an unconstrained return value when call ordering is part of the contract.

## Windows ad-hoc verification

When the verification harness requires fresh evidence, create the probe using `tempfile.mkstemp(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir())`; execute the literal generated path from the repository root; report it as **ad-hoc verification**; then remove only the owned probe and verify it is absent. Preserve any pre-existing `hermes-verify-*.py` files.
