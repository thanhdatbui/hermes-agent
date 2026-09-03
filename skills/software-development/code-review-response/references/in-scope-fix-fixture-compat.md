# In-scope fix patterns: exact-scope + out-of-scope fixtures (tiktok-follow P3, audit b33fc07)

Session: fixing AG audit MINOR findings in `follow_runner` with an exact 5-file scope
(adapter.py, mode1_search_follow.py, verify_follow.py, 2 test files) while `conftest.py`
was OUT of scope and its `FakeAdapter`/`xml_node` had to keep working unchanged.

## 1. Resolution-safe swipe without touching the fake

Audit: `swipe_feed` hardcoded `adapter.swipe(540, 1600, 540, 400, 300)` (1080x1920).

Fix shape (adapter.py):
```python
def _screen_size(adapter):
    getter = getattr(adapter, "screen_size", None)   # duck-type new API
    if callable(getter):
        try:
            size = getter()
        except Exception:
            size = None
        if size and size[0] > 0 and size[1] > 0:
            return (int(size[0]), int(size[1]))
    try:                                              # fallback: dump root bounds
        nodes = parse_nodes(adapter.dump_ui())
        box = nodes[0].get("bounds") if nodes else None
        if box and box[2] > 0 and box[3] > 0:
            return (box[2], box[3])
    except Exception:
        pass
    return None

def swipe_feed(adapter, n, sleep_after=1.2):
    n = max(0, n)
    if n == 0:
        return                      # CRITICAL: early return BEFORE any dump_ui()
    size = _screen_size(adapter)    # so the fake's XML queue never shifts
    if size is None:
        return                      # fail-closed: no blind swipe on unknown size
    w, h = size
    cx, y1, y2 = w // 2, int(h * 5 / 6), int(h * 1 / 5)
    for _ in range(n):
        try:
            adapter.swipe(cx, y1, cx, y2, 300)
            time.sleep(sleep_after)
        except FollowAdapterError:
            return
```
- The `n == 0` early return is load-bearing: existing tests rely on the fake's
  `dump_ui()` consuming one queue entry per call. Any size lookup that dumps
  unconditionally breaks every pre-existing test's dump budget.
- FakeAdapter stays compatible with ZERO conftest changes: it has no
  `screen_size` attr (duck-type miss) and its `xml_doc` root node carries
  `[0,0][1080,1920]` bounds (fallback hit). New tests push raw XML with
  `[0,0][720,1280]` root and assert `swipes == [(360, 1066, 360, 256)]`.

## 2. Fixture helpers that hardcode attributes → raw XML in the test

`conftest.xml_node` always emits `class="android.widget.TextView"`,
`focused="false"`, no `editable` attr. To test `parse_nodes` keeping
`class/editable/focusable/focused` (needed to tell the search EditText apart
from the icon that shares content-desc "Tìm kiếm"), build the XML string
inside the test file instead of extending the helper:

```python
def _edittext_input_xml(*, focused: bool):
    foc = "true" if focused else "false"
    return (
        '<hierarchy rotation="0"><node index="0" ... bounds="[0,0][720,1280]">'
        '<node index="1" class="android.widget.EditText" package="..." '
        f'content-desc="Tìm kiếm" editable="true" focusable="true" focused="{foc}" '
        'bounds="[80,120][640,240]"/></node></hierarchy>'
    )
```
Selector helper pattern (production): strict pass over `class=="android.widget.EditText"`
or `editable`; fallback pass over focusable nodes whose content-desc contains
the search label, picking the WIDEST node (input placeholder, not the small icon).
Regression assertions: `fake.taps == [(975,175),(360,180),(540,500)]` proves two
DISTINCT nodes were tapped — icon and input — not the same content-desc twice.
`focused=True` fixture variant proves no second tap at all.

## 3. Transport-dependency audit finding (pkill) — verify, comment, lock with test

Auditor claimed `adapter.shell` "likely depends on atx-agent" so
`pkill -9 -f atx-agent` in the recovery ladder kills its own transport.
Truth: `shell()` runs `subprocess.run([adb_path, "-s", serial, "shell"] + args)`
directly — plain adb daemon, independent of atx-agent. Per instruction, do NOT
change behavior. Evidence: comment in `shell()` + locking test:

```python
def test_shell_runs_adb_subprocess_directly(monkeypatch):
    import subprocess
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    ad = FollowAdapter("adb", "serialAAA")
    ad.shell(["pkill", "-9", "-f", "atx-agent"], check=False)
    assert calls == [["adb", "-s", "serialAAA", "shell", "pkill", "-9", "-f", "atx-agent"]]
```

## 4. Reload-budget off-by-one (unknown → not_followed)

`verify_after_tap`: the unknown-branch did `reload()` then `pass`-fell into a loop
starting at attempt 1 → total reloads = 1 + `verify_reload_retries`. Fix: a
`reloads_done` counter; loop `for attempt in range(reloads_done + 1, retries + 1)`.
Regression test that FAILS on old code: unknown dump → reload → not_followed →
reload → not_followed = blocked, assert `len(reloads) == 2` with
`verify_reload_retries=2` (old code does 3). Also assert the happy path
unknown → reload → followed still returns `success` (gate preserved).

## 5. Ad-hoc probe skeleton (no pytest needed for targeted evidence)

```python
import sys, tempfile, shutil
sys.path.insert(0, "D:/Taadaa/automation-core/src")
sys.path.insert(0, "D:/taadaa/tiktok-follow")
from follow_runner.core.adapter import parse_nodes, swipe_feed
# ... minimal Fake with queue/dump_ui/tap/swipe/type_text, xml_doc/node builders ...
checks = [("name", bool_expr), ...]
fails = [n for n, ok in checks if not ok]
for n, ok in checks: print(("PASS" if ok else "FAIL"), "-", n)
sys.exit(1 if fails else 0)
```
Name it `hermes-verify-p3-fixes.py` under `C:\Users\Kibe\AppData\Local\Temp`,
run with a literal `C:/Users/...` path (MSYS path mangling — see SKILL.md §9),
delete after, verify cleanup with `[ -e path ]`.

## 6. EOF anchor trap (see SKILL.md §8)

When the LAST function of a no-trailing-newline file is being replaced, the
`old` anchor must NOT end in `\n` (the file has none there) — count==0 assert.
Anchor without it; the `new` string re-adds the newline; keep the
ensure-trailing-newline step so the "missing newline at EOF" finding closes.
