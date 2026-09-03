# Nested-config `None` regression pattern

## Incident shape
A `multi-machine-feed-session` alert reported:

```text
'NoneType' object has no attribute 'get'
```

The execution path contained chained reads such as:

```python
ctx.config.get("safety", {}).get("allow_feed_swipe")
ctx.config.get("timeouts", {}).get("device_seconds")
child_config.get("timeouts", {}).get("adb_seconds")
```

Python only uses the default passed to `dict.get()` when the key is absent. If YAML/JSON contains `safety: null` or `timeouts: null`, the first `.get()` returns `None` and the chained call crashes.

## Offline investigation recipe
1. Start from the exact alert entrypoint, not the screenshot alone.
2. Search the call chain for chained `.get()` calls and inspect every config section that can come from YAML/CLI merges.
3. Build a focused fixture with the section present-but-null, not only missing:
   - `{"safety": None, "timeouts": None, ...}`
4. Run the fixture before the patch and verify it reproduces the exact exception or reaches the same failing branch.
5. Normalize sections at the boundary:

```python
safety = config.get("safety")
safety = safety if isinstance(safety, dict) else {}
timeouts = config.get("timeouts")
timeouts = timeouts if isinstance(timeouts, dict) else {}
```

6. Re-run the same entrypoint fixture and assert fail-closed behavior: config/manual result, per-machine result row/artifact, or another explicit terminal status — never an uncaught `AttributeError` and never an implicit live action.
7. Run focused flow tests, compile, and `git diff --check` before any live rerun.

## Scope and safety
- Preserve unrelated dirty worktree changes; inspect status before patching.
- Do not use a live rerun as the reproducer.
- Do not weaken safety flags to make a malformed config pass.
- Test both parent preflight and child-context/hook reads when the same section is consumed at multiple layers.
- If the alert lacks a traceback, report the exact root cause category and affected call-chain locations, but distinguish confirmed evidence from the still-unknown exact source line.

## Incident addendum — 2026-08-22, `[MÁY 38]`
Concrete production repro of the above pattern in `tiktok-luot nuoi acc`.

**Symptom:** `multi-machine-feed-session` báo `[ALERT] [MÁY 38] Dừng: failed | Lý do: 'NoneType' object has no attribute 'get'`.

**Confirmed path:** `execute_multi_machine_feed_session` → `ThreadPoolExecutor.submit(_run_child)` per machine. The crash lands in the worker, is caught at the executor `future.result()` site, and surfaces as `final_status="failed"` with `stop_reason=str(exc)`.

**Exact crash sites at time of incident (in `python_runner/flows/multi_machine_feed_session.py`):**
- `_run_child` per-child, `ctx.config.get("timeouts", {}).get("device_seconds", DEFAULT_DEVICE_TIMEOUT_SECONDS)` (timeout + deadline monotonic used for per-device watchdog). `timeouts: null` ⇒ `None.get(...)` văng. This is the most likely line for Máy 38 because it runs on the real `ctx.config` inside the worker.
- `prepare_tiktok_for_smoke` (`python_runner/flows/device_prepare.py:633`): `ctx.config.get("safety", {}).get("allow_prepare_tiktok")`. Runs per-child inside `_run_child`'s try-block → caught → same `stop_reason=str(exc)`.
- Parent preflight `prepare_multi_machine_feed_session`: `ctx.config.get("safety", {}).get("allow_navigation_only"|"allow_feed_swipe")`. `safety: null` ⇒ văng at batch start.

**Fix shipped in worktree (read-only diagnosis confirmed it):** a typed boundary helper
`def _cfg_subdict(config, key): value = config.get(key); return value if isinstance(value, dict) else {}`
replaces every `config.get(section, {}).get(...)` in `multi_machine_feed_session.py` (safety/timeouts at prepare, `_build_child_context` adb_seconds, follow/upload hooks, `_run_child` timeouts). Regression test `NullConfigRegressionTests` in `test_multi_machine_feed_session.py` covers `safety=None` (fail-closed CONFIG_ERROR) and `timeouts=None` (adb default 15.0).

**Residual unguarded sites (SAME pattern, still vulnerable if `safety: null`):**
- `python_runner/core/device.py:62` — `DeviceContext.__post_init__`: `self.config.get("safety", {}).get("capture_on_failure")`. NOTE: the test fixture `make_ctx_with_cfg` already has to self-normalize `safety:None→{}` because this is not yet fixed; that is a latent second bug.
- `python_runner/flows/device_prepare.py:633` — `prepare_tiktok_for_smoke` (per-child).
- `python_runner/flows/feed_swipe_smoke.py` — ~35 sites `ctx.config.get("safety", {}).get(...)` (e.g. 1988, 4005, 5775, 6281, 6640, 9002, 11580, 15270, 15274, 15346, 17031, 18338…).

**Durable recommendation:** fix once at the load boundary (normalize `safety`/`timeouts` to `{}` in `run_tiktok.py` or `DeviceContext.__post_init__`) so every downstream `.get("safety", {}).get(...)` is safe without rasp-file edits. Until then, any new consumer reading these sections must use `_cfg_subdict` or the inline `isinstance` guard.

**Workbook is NOT the None source:** `select_feed_session_accounts` already guards cell reads with `or ""` / `isinstance`, so `accounts.xlsx` parsing cannot produce this `AttributeError`. Root cause is exclusively the runtime `ctx.config` YAML/CLI-merged sections.
