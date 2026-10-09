# Import Namespace and Command Contract Verification

## Purpose

Use this reference when tests patch Python imports or assert subprocess/SSH command construction.

## Robust import patching

Production may resolve the same module under package-qualified and flat names, such as `python_runner.flows.upload_preflight` and `flows.upload_preflight`. A patch aimed at only one string can silently miss the production object. In tests, inspect `sys.modules` and use `ExitStack` to patch each loaded namespace conditionally:

```python
with ExitStack() as stack:
    for module_name in ("flows.upload_preflight", "python_runner.flows.upload_preflight"):
        module = sys.modules.get(module_name)
        if module is not None:
            stack.enter_context(patch.object(module, "check_upload_cooldown_eligibility", return_value=expected))
    result = call_under_test()
```

Keep this compatibility logic in tests. Do not add production import bypasses just to make a patch land.

## Fixture completeness

Before asserting transport details, satisfy every earlier gate explicitly: branch-controlling config flags (for example `_is_organic_rest=False` in both parent and child contexts), session identity, workbook row, cooldown eligibility, and the expected rendered media file. Otherwise the test can fail with an unrelated safe skip such as `video_not_rendered`.

## Command contract

A mocked subprocess returning success does not prove the intended transport was selected. Assert the actual constructed argv after all preflight gates pass. If the observed argv starts with a Python executable/module invocation while the test expects `ssh`, treat that as a real command-construction mismatch and investigate the production branch; do not weaken the assertion merely to obtain green tests.

## Gate evidence

Run the exact user-specified verification command literally from the requested repository. Report the exact pass/fail count and the separate `py_compile` result. A syntax pass or partial test pass is not completion while the exact gate remains red.
