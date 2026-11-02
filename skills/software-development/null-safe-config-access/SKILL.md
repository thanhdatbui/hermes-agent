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
- Chained `.get("field", {}).get(...)` in telemetry / log line parsers or JSONL events
  where `field` is deserialized as `None` or non-dict (e.g. `event = {"extra": None}`).
- You are hardening config or event parsers against hand-edited YAML or sparse JSON lines.
- You are writing a TDD regression test for a previously-crashing config or event log parser.
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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
