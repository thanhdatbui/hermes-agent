# Pytest collection and bounded-timeout triage

Use this recipe when a repository-level `pytest` run fails before tests execute or does not finish within the task's bounded window.

## Import collection failure

1. Run from the repository root:

```bash
python -m pytest -q
```

2. Read the first collection traceback. If a test imports `tools.some_module` and `tools/some_module.py` exists, inspect whether `tools/` is a package. A minimal `tools/__init__.py` may be the correct repository fix when the tests intentionally use package imports.
3. Verify the import directly from the repo root, then run the affected file:

```bash
python -c "import tools.some_module; print(tools.some_module.__file__)"
python -m pytest -q tests/test_affected.py -x -vv
```

Do not change application code to mask a test-package import problem.

## Collection-only evidence

After the collection fix, run:

```bash
python -m pytest --collect-only -q
```

This proves test discovery and reports the exact collected count without starting long-running tests.

## Full-suite timeout

Run the full suite only with an explicit bounded timeout. If it passes collection and then exceeds the limit, report it as incomplete—not green. Use the focused affected test/module as the product verdict and collection-only output as suite-discovery evidence. Do not rerun the identical timed-out command repeatedly without narrowing scope or diagnosing the slow test.

## Reporting

Separate:

- collection/import failure vs product assertion failure;
- focused test pass count vs full-suite status;
- warnings and unrelated diff-check failures vs changed-path verification;
- repository package repair vs requested application-code change.
