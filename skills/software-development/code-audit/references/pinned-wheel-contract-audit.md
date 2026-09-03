# Pinned-Wheel Contract Audit (read-only, Windows/MSYS)

Worked 2026-08-14 auditing the ACCOUNT_READY checkpoint in `D:\taadaa\tiktok-follow`
(automation-core switcher chain + device-lock semantics) without installing,
upgrading, or touching the environment.

## Trigger

The audit must verify a shared-core API chain (e.g.
`open_account_switcher -> select_exact_account -> verify_selected_account`,
`DeviceLockLease.finish(succeeded=False, failure_status=...)`, `_DEVICE_LOCK_STATUSES`)
that the repo pins via `requirements-automation-core.txt`:
`automation-core @ file:///D:/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl`,
while the ACTIVE interpreter has an older version installed (0.4.43).

## Recipe

1. **Confirm the version skew first** — never assume:
   ```
   pip show automation-core | head -5
   python -c "import automation_core; print(automation_core.__file__)"
   ```
2. **Extract the exact pinned wheel, read-only, into a disposable dir.** Native
   Windows paths ONLY for both the wheel arg and `--target` (see pitfalls):
   ```
   python -m pip install --quiet --no-deps \
     --target 'C:\Users\<u>\AppData\Local\Temp\ac044test' \
     'D:\Taadaa\automation-core\dist\automation_core-0.4.44-py3-none-any.whl'
   ```
3. **Probe the pinned API with signature/source inspection:**
   `inspect.signature(...)` for call contracts and `inspect.getsource(...)` for
   return/exception semantics (e.g. `verify_selected_account` raises
   `AccountSwitcherError("ACCOUNT_VERIFY_MISMATCH", ...)` and returns the XML;
   `finish(succeeded=False)` calls `set_status(failure_status)` = retain-handoff,
   never force-unlock). For optional exceptions use presence probes:
   `getattr(device_lock, "DeviceLockNeedsUserDecision", ())` — 0.4.44 lacks it.
4. **Prove the probe resolved the PINNED copy, not the env:**
   ```
   PYTHONPATH='C:\...\ac044test' python - <<'EOF'
   import automation_core
   print(automation_core.__file__)          # must be the temp dir
   from importlib.metadata import version
   print(version("automation-core"))        # must be 0.4.44
   EOF
   ```
5. **Run the scoped suite against the pinned wheel** so tests exercise the pinned
   API, not the env's older one:
   ```
   env -u PYTHONPATH PYTHONPYCACHEPREFIX=/tmp/ac044pyc \
     PYTHONPATH='C:\...\ac044test' \
     python -m pytest follow_runner/tests/... -q
   ```
6. **Verify the repo is untouched** afterwards: `git status --short` must show
   only the original M/?? markers, and the disposable dirs live under the OS temp
   dir, never inside the repo.

## Pitfalls (all hit this session)

- **pip mangles MSYS `/d/...` wheel paths** → `ERROR: No such file or directory:
  'D:\d\Taadaa\automation-core\dist\...'` (it prepends the drive root). Use the
  native `D:\...` form for the wheel argument.
- **`--target /tmp/...` silently lands where native python cannot import it** —
  MSYS `/tmp` is not `C:\tmp`. Resolve the real location with `cygpath -w /tmp`
  (`C:\Users\<u>\AppData\Local\Temp`) and use that Windows path for `--target`
  and `PYTHONPATH`.
- **`pip install --target` into an existing dir with a failed prior attempt**
  leaves the dir EMPTY with exit 0 (the earlier mangled-path run created the dir
  but installed nothing). Always `ls` the target for `automation_core/` +
  `.dist-info` and re-run the version probe; a "passed" test run can silently
  fall back to the env's installed copy when `PYTHONPATH` points at an empty dir.
- **A `-q`-suppressed install may hide a failed wheel copy** — `grep -v notice`
  the output; the mangled-path error is a WARNING+ERROR pair.
- **`getattr(module, "Symbol", ())` for optional exception types**: the consumer
  uses `isinstance(exc, ())` which is always False — safe degrade when the
  symbol is absent, exact tuple when present.

## Reusable one-liner

```bash
# resolve real temp dir for native tools
cygpath -w /tmp
```
