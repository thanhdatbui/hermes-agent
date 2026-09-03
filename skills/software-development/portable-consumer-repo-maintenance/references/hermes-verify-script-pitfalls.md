# hermes-verify script pitfalls (Windows, multi-drive)

Verified 2026-08-11 during the automation-core `auto_enable_wifi` session
(ad-hoc verification of a watcher feature in `D:\Taadaa\automation-core`).

## 1. Cross-drive relative path → SILENT import of a stale installed package

Symptom chain:

- Temp verifier lives in `C:\Users\Kibe\AppData\Local\Temp`.
- Script builds the repo src with
  `os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "Taadaa", "automation-core", "src")`.
- Five `..` reach `C:\` — but `..` **cannot cross drives** to `D:\`. The joined
  path is `C:\Taadaa\automation-core\src`, which does not exist.
- `sys.path.insert(0, <nonexistent>)` is inert; the `import automation_core...`
  then resolves the package from site-packages — an OLD installed copy without
  the new API → `TypeError: watch_device_reconnect() got an unexpected keyword
  argument 'auto_enable_wifi'`.
- The dangerous variant: if the old copy happens to have a compatible surface,
  the verifier **PASSES while testing old code** — a false positive.

Fixes:

```python
REPO_SRC = r"D:\Taadaa\automation-core\src"   # pin the absolute path, never derive it
sys.path.insert(0, REPO_SRC)
import automation_core.device_recovery as dr
assert dr.__file__.startswith(REPO_SRC), dr.__file__   # prove which module you imported
```

Context: an earlier "11/11 passed" run only worked because the shell command
happened to set cwd-relative `PYTHONPATH=src`. Dropping the env var silently
changed what was tested. Make the verifier self-sufficient and prove the
module file.

## 2. Watcher loops hang when the gate function succeeds against fakes

Re-verifying `watch_device_reconnect`'s wifi-failure branch: the REAL
`wait_for_wifi` returns True on the first probe against a fake ADB whose
`wlan0` shows `state UP` + `inet` → the `while ... not wait_for_wifi(...)`
failure branch (the code under test) never runs, and without `max_events` or
a `stop_event` the watcher loops forever → 60s tool timeout.

Fix: monkeypatch the gate exactly like the pytest regressions do, and always
bound the loop:

```python
dr.wait_for_wifi = fail_then_stop(stop)          # fail once, then set stop_event
# or for the ready case:
dr.wait_for_wifi = lambda *a, **k: True
dr.watch_device_reconnect(adb, on_ready, ..., max_events=1)  # or stop_event=...
```

Applies to any loop whose exit depends on a function you replaced with a fake.

## 3. `patch` tool + CRLF: `replace_all` on a short anchor destroyed the header

Sequence that corrupted `tests/test_device_recovery.py` twice this session:

- `patch(mode='replace')` with a 1-line `old_string` → "Found 9 matches".
- `replace_all=true` with a 2-line anchor (`if args == ["wm", "size"]:` +
  blank line + `if args == ["settings", "get", "system", ...]`) matched EIGHT
  sites — including the top-of-file import block — and rewrote the header with
  indented garbage (`if args == ["wm", "size"]:` at line 1). Fuzzy matching
  ignores indentation/context differences; short anchors on repetitive CRLF
  test files are dangerous.
- The tool also normalizes the whole file's line endings; its diff output then
  shows every line as `+`/`-` (whole-file rewrite).

Recovery and rule:

- `git checkout -- <file>` restores instantly. Run it the moment the diff shows
  whole-file churn or header corruption — do not try to repair in place.
- On CRLF files, use `patch` only with a long, unique, multi-line anchor; for
  insertions use a Python byte-edit script (`read_bytes`/`write_bytes`, explicit
  `\r\n` anchors, `assert data.count(anchor) == 1`, then `git diff --stat` to
  confirm no whole-file rewrite). See `crlf-safe-surgical-edits.md`.
- Pytest regressions were written once via a temp `write_file` script with
  explicit `\r\n` in the inserted block; even then a `\n` inside a string
  literal needed a follow-up byte fix (`bytes([92, 110])` → `\\n`).

## 4. Baseline-proof before claiming "no regressions"

Full suite shows failures → prove they are pre-existing before attributing:

```bash
git stash -q && PYTHONPATH=src python -m pytest <failing-test> -q; git stash pop -q
```

Identical failure on the clean baseline = not yours; record it and move on.
Used this session to clear `test_package_metadata.py` (collection error,
missing `tools.verify_wheel_metadata`) and `test_startup.py`
(`test_android_startup_orders_unlock_rotation_then_recents`) as pre-existing,
then reported 499 passed / 2 baseline failures accurately.
