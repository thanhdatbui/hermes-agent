# Code-Quality Invariants — automation-core PRs

Apply to every edit touching `alerts.py`, `batch_aggregator.py`, or any module with a public `bool`-returning function or directory-scanning logic.

---

## Bool return-type discipline

Functions typed `-> bool` must return **only** `bool` from every branch, including suppression / early-exit paths. Returning a `dict` is a type bug that breaks truthiness checks upstream.

**Bad (dict from bool function):**
```python
if _should_suppress_immediate_machine_alert():
    return {"status": "suppressed_for_batch", "machine": machine, "suppressed": True}
```

**Good:**
```python
if _should_suppress_immediate_machine_alert():
    log.info("Suppressed for machine %s (batch aggregation mode)", machine)
    return False
```

Tests that previously asserted `isinstance(result, dict)` become `assert result is False` after the fix.

---

## `iterdir()` → always `sorted(iterdir())`

`Path.iterdir()` returns entries in **filesystem order**, which is non-deterministic on Windows NTFS. Any loop over a directory that populates a result list must wrap with `sorted()`:

```python
# WRONG — non-deterministic on Windows NTFS
for machine_dir in machines_dir.iterdir():

# RIGHT — stable alphabetical order, reproducible results
for machine_dir in sorted(machines_dir.iterdir()):
```

Applies in `load_results_from_run_dir` (both Layout 1 `machines/` subdirs and Layout 2 generic subdirs) and anywhere else results are collected from a directory.

---

## Named exception + log.warning, never bare `continue`

Silent `except Exception: continue` buries parse failures with no observable trace.

**Bad:**
```python
except Exception:
    continue
```

**Good:**
```python
except Exception as exc:
    log.warning("Failed to parse run manifest for %s: %s", manifest_path.parent.name, exc)
    continue
```

---

## Check `logging` import before adding `log.*` calls

When adding `log.warning` / `log.info` to a module that had no prior logging, add **both** lines:

```python
import logging          # in the imports block
...
log = logging.getLogger(__name__)   # module-level, after imports
```

Probe before writing: `grep -n "^log = " <file>` — if empty, add the logger.

`batch_aggregator.py` lacked both lines entirely when `log.warning` was first introduced in this session.

---

## Early-exit guard on directory arguments

Any function accepting a `run_dir` / `Path` argument that calls `.iterdir()` must guard at the top:

```python
run_path = Path(run_dir)
if not run_path.is_dir():
    return []
```

Without this, an invalid/missing path raises `NotADirectoryError` instead of returning gracefully to the caller.

---

## Session context

Discovered and applied: 2026-09-08 session — "Sửa return False khi suppressed, sorted iterdir, cập nhật test"
Claude Opus review: **VERDICT: APPROVED** (43 tests green)
Files affected: `src/automation_core/alerts.py`, `src/automation_core/batch_aggregator.py`, `tests/test_alerts.py`
