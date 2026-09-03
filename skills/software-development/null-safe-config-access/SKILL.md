---
name: null-safe-config-access
description: "Fix and prevent 'NoneType' object has no attribute 'get' crashes from config values (YAML/JSON) that deserialize to null. Covers the minimal _cfg_subdict normalization helper, the fail-closed default strategy, and the TDD RED-phase trap for present-but-null keys."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [python, config, yaml, json, defensive-coding, bugfix, tdd]
    related_skills: [test-driven-development, systematic-debugging, code-audit]
---

# Null-Safe Config Access

## Overview

A recurring crash class in config-driven Python: code reads a nested value
with a chained `.get()`, assuming the intermediate mapping is always a dict:

```python
config.get("safety", {}).get("allow_feed_swipe")   # BOOM if safety is null
config.get("timeouts", {}).get("adb_seconds", 15)  # BOOM if timeouts is null
```

When a YAML/JSON key is present but `null` (e.g. `safety: null`), Python
stores `None`. `config.get("safety", {})` then returns `None` — **not** the
`{}` default, because the default only applies when the key is *absent*. The
next `.get(...)` raises:

```
AttributeError: 'NoneType' object has no attribute 'get'
```

This is especially common where ops write/tweak YAML by hand and leave a
section as `null` instead of omitting it or writing `{}`.

## When to Use This Skill

- You see `'NoneType' object has no attribute 'get'` (or `.items`, `.keys`)
  on a value that came from config / parsed YAML / JSON.
- You are hardening config parsers against hand-edited YAML.
- You are writing a TDD regression test for a previously-crashing config.
- Code review of config access — flag every `x.get(k, {}).get(...)` chain
  where `x` is a value loaded from external config (not a freshly-built dict).
- You see the same exception in a flow that consumes a result object, handler
  response, or recapture metadata. First prove whether the nullable value is
  config or a result field; do not apply `_cfg_subdict` blindly to non-config
  data.

## Diagnostic Boundary: Config Null vs Result Null

The exception text is not enough to identify the owner of the `None`. Inspect
 the exact traceback/call-site and persisted run evidence before patching.
For popup/recovery flows, a common shape is a result that reports
`dismissed=True` while `after_attempt=None`; the correct fix is a verified
postcondition guard, not config normalization:

```python
if not dismiss.dismissed or dismiss.after_attempt is None:
    # fail closed; never dereference after_attempt below
    return row
```

Treat a success flag as usable only when the evidence it promises is present.
For UI dismissal, that evidence is a fresh recapture/attempt. Preserve the
manual-needed or blocked outcome when recapture is absent, and add a regression
test for the contradictory result (`dismissed=True`, `after_attempt=None`).
See `references/result-null-recapture-guard.md` for the focused recipe.

## Minimal Fix — the `_cfg_subdict` helper

Add one tiny helper and route nested access through it. Keep it fail-closed:
a null / non-dict value becomes an empty dict, so opt-in gates stay OFF and
defaults apply. This is the smallest change that fixes every site without
changing intended behavior.

```python
def _cfg_subdict(config: dict[str, Any], key: str) -> dict[str, Any]:
    """Return config[key] as a dict, normalizing null / non-dict to {}.

    YAML `safety: null` makes the key present but None; config.get(key, {})
    then returns None (not {}), so a chained .get(...) raises
    'NoneType' object has no attribute 'get'. Fail-closed: treat the bad
    value as an empty dict so gates that require explicit opt-in stay off.
    """
    value = config.get(key)
    return value if isinstance(value, dict) else {}
```

Replace each broken site:

```python
# before
if not ctx.config.get("safety", {}).get("allow_feed_swipe"):
# after
if not _cfg_subdict(ctx.config, "safety").get("allow_feed_swipe"):
```

Why fail-closed (`{}`) and not fail-open? For safety/permission gates
(`allow_*`), an empty dict means "no opt-in granted" — the conservative,
safe default. For timeout/threshold lookups (`timeouts.adb_seconds`), the
empty dict makes the *inner* `.get("adb_seconds", 15)` fall back to its
own hard default. Either way the prior default value still applies.

## TDD RED-Phase Trap (critical)

To write a regression test that *actually reproduces* the crash, you must
give the config the **present-but-null** key. Two wrong ways that produce a
spurious GREEN:

- **Omitting the key**: `config.get("safety", {})` returns `{}` → no crash →
  test passes without exercising the bug. You never saw RED.
- **Setting it to a dict**: also no crash.

The correct way:

```python
cfg["safety"] = None          # present but null — reproduces the AttributeError
```

If `None` is itself a legitimate default you must distinguish from "absent,"
use a sentinel and only attach the key when a real value was supplied:

```python
_UNSET = object()

def make_cfg(*, safety=_UNSET, timeouts=_UNSET):
    cfg = {...}
    if safety is not _UNSET:
        cfg["safety"] = safety      # call with safety=None to reproduce the bug
    if timeouts is not _UNSET:
        cfg["timeouts"] = timeouts
    return cfg
```

### Fixture boundary when the crash is upstream of the unit under test

If the same `key: null` bug also exists in an object the test must construct
(e.g. `DeviceContext.__post_init__` reads `config.get("safety", {}).get(...)`),
the fixture blows up *before* reaching your flow code. To keep the test
focused on the flow-level fix without patching that out-of-scope module,
normalize in the test helper only:

```python
def make_ctx(config):
    config = dict(config)
    if config.get("safety") is None:   # out-of-scope upstream bug; isolate here
        config["safety"] = {}
    return DeviceContext(config=config, ...)
```

Document why in a comment so a future reader doesn't "clean it up" and
silently resurrect the spurious-GREEN trap.

## Verification (after the fix)

- Run the new regression test → must go RED before the fix, GREEN after.
- Full suite → no regressions; pre-existing failures unrelated to the change
  should be identical before and after (diff them).
- `python -m compileall -q <changed files>` → clean.
- `git diff --check` → no whitespace/trailing issues.
- If a suite run is slow or flaky, also run a small ad-hoc script in
  `%TEMP%` (`hermes-verify-*.py`, cleaned up after) that drives the fixed
  functions directly — see `references/repro-recipe.md`.

## Anti-Patterns

- Don't add `if value is None: value = {}` inline at every call site — centralize
  in `_cfg_subdict` (DRY, one place to reason about).
- Don't "fix" by deleting the default arg (`config["safety"].get(...)`) — that
  turns a null-value crash into a KeyError crash for the *absent* case.
- Don't make the helper raise on null unless the value is genuinely required;
  prefer fail-closed `{}` for optional sections.

## References

- `references/repro-recipe.md` — end-to-end reproduction + ad-hoc verify script
  template for the `safety: null` / `timeouts: null` crash class.
