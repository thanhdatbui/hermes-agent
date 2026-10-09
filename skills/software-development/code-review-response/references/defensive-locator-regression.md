# Defensive Locator Regression Recipe

Use this reference when extracting or hardening a browser/UI challenge detector.

## Contract

The detector should return its normal ordered availability tuple plus a named locator map. A single stale locator must not abort discovery. Treat the option as unavailable when the handle is absent, zero-count, hidden, or raises during a readiness probe.

## Minimal regression matrix

```python
class FakeLocator:
    def __init__(self, state):
        self.state = state

    @property
    def first(self):
        return self

    def count(self):
        if self.state == "raise_count":
            raise RuntimeError("count failed")
        return 0 if self.state == "absent" else 1

    def is_visible(self):
        if self.state == "raise_visible":
            raise RuntimeError("visibility failed")
        return self.state == "visible"
```

Exercise at least:

- all absent/hidden → all flags false and all returned locators `None`;
- `count()` raises → no exception escapes;
- visibility probe raises → no exception escapes;
- all healthy → original keys, tuple order, and actionable locators remain intact;
- no available options → classifier returns `None`.

## TDD evidence

1. Run the new edge-case test before the guard. The expected RED is the uncaught external-handle exception, not collection or fixture setup failure.
2. Add the smallest readiness helper, normally:

```python
def _is_loc_ready(locator):
    if not locator:
        return False
    try:
        return bool(locator.count() > 0 and locator.is_visible())
    except Exception:
        return False
```

3. Rerun the exact regression test, then the owning module.
4. Run `python -m py_compile` on touched Python files and `git diff --check`.
5. Report dependency warnings separately from the pass count.

Keep selector discovery, priority classification, clicking, telemetry, and retry/continue orchestration as separate responsibilities.
