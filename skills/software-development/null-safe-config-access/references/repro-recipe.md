# Repro recipe: `safety: null` / `timeouts: null` → AttributeError

## The crash (exact shape)
```python
ctx.config.get("safety", {}).get("allow_feed_swipe")
# YAML has: safety: null
# config["safety"] is None -> .get on None -> AttributeError
```
Message: `'NoneType' object has no attribute 'get'`

## Minimal repro (standalone, no project deps)
```python
config = {"safety": None, "timeouts": None}
try:
    config.get("safety", {}).get("allow_feed_swipe")
    print("NO CRASH (wrong — means key was absent, not null)")
except AttributeError as e:
    print("REPRODUCED:", e)
```

## The fix
```python
def _cfg_subdict(config, key):
    v = config.get(key)
    return v if isinstance(v, dict) else {}

# before: ctx.config.get("safety", {}).get("allow_feed_swipe")
# after:  _cfg_subdict(ctx.config, "safety").get("allow_feed_swipe")
```

## Ad-hoc verify script template
Place under `%TEMP%` with a `hermes-verify-` prefix, run, then delete.
Drives the fixed functions directly — no full suite needed for a quick gate.
```python
import os, sys, tempfile, sys
sys.path.insert(0, r"<repo>/python_runner")
from flows.multi_machine_feed_session import _cfg_subdict, prepare_multi_machine_feed_session

assert _cfg_subdict({"safety": None}, "safety") == {}          # null -> {}
assert _cfg_subdict({"timeouts": {}}, "timeouts") == {}        # absent -> {}
cfg = {"adb_path": "adb", "_account_workbook": "x.xlsx",
       "_machines": "11,12", "safety": None}
# wrap in DeviceContext only if its __post_init__ also reads safety safely,
# otherwise normalize safety=None -> {} in the fixture helper first
r = prepare_multi_machine_feed_session(ctx)
assert r.status.name == "CONFIG_ERROR"   # fail-closed, NOT a crash
print("OK")
# cleanup: os.remove(__file__)
```
Run: `python %TEMP%\hermes-verify-null-config.py` → expect `OK`, exit 0.

## TDD order that actually works here
1. Write the regression test with `cfg["safety"] = None` (present-but-null).
2. Run it → must FAIL with `AttributeError` (RED, real).
3. Add `_cfg_subdict` + swap the 6 sites.
4. Run it → PASS (GREEN).
5. Full focused suite + `compileall -q` + `git diff --check`.
