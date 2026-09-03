# Code Audit: `_install_multi_split` in automation-core

## Session Context

- **Repo:** `D:\Taadaa\automation-core` (commit `ec94ba3`)
- **File:** `src/automation_core/device.py`
- **Function:** `_install_multi_split` (private, called from `install_package` when `len(apk_paths) > 1`)
- **Purpose:** Install split APKs on Samsung Android devices via `pm install-create` → `install-write` → `install-commit`
- **Concerns raised:** total_bytes calculation, split_name mapping, cleanup on crash, type safety, edge case file paths with spaces

## How `adb.shell` and `adb.run` work (key to understanding the bugs)

```python
# adb.py — both use subprocess.run(..., shell=False)
# Each list element = one argument to the adb binary
def run(self, args, ...):
    command = [self.adb_path] + (["-s", self.serial] if self.serial else []) + list(args)
    subprocess.run(command, shell=False, ...)

def shell(self, args, ...):
    return self.run(["shell", *args], ...)
```

⚠️ **Critical detail:** `adb shell` joins *everything after `shell`* with spaces and sends the result as a single command string to the **device's shell**. This means:
- Host-side: `subprocess.run(..., shell=False)` → arguments are separate → ✅ spaces in paths are fine
- Device-side: the device shell receives a space-joined string → ❌ spaces in arguments cause word-splitting

## Bugs Found & Fixed

### Bug 1 (Critical): Fabricated split names

**Original code (line 257):**
```python
for i, f in enumerate(remote_files):
    split_name = "base" if i == 0 else f"split_{i:02d}"
    ...
    ["pm", "install-write", session_id, split_name, f"{remote_dir}/{f}"]
```

**Problem:** The first file is always called "base" and subsequent files get fake names "split_01", "split_02", etc. Android's `pm install-write` expects the actual split name from the APK manifest (e.g., "base", "config.armeabi_v7a", "config.en"). Fabricated names cause `install-commit` to fail with split name mismatch.

**Fix:** Use `os.path.splitext(f)[0]` (filename without extension) — matching what ADB's own `install-multiple` implementation does:
```python
split_name = os.path.splitext(f)[0]  # "base.apk" → "base", "config.arm64.apk" → "config.arm64"
```

### Bug 2 (High): Silently skipped stat failures

**Original code (lines 234-240):**
```python
if size_result and size_result.ok:
    total_bytes += int(size_result.stdout.strip())
```

**Problem:** If `stat -c %s` fails for any file (permission, race condition, unsupported format), that file's size is silently dropped from `total_bytes`. `pm install-create -S` uses the wrong total, causing `install-commit` to fail with a size mismatch error that's hard to diagnose.

**Fix:** Hard-fail with clear `ADBError`:
```python
if not size_result or not size_result.ok:
    raise ADBError(f"install_package: could not stat remote file {f} ...")
raw = size_result.stdout.strip()
if not raw or not raw.isdigit():
    raise ADBError(f"install_package: unexpected stat output for {f}: {raw!r}")
total_bytes += int(raw)
```

### Bug 3 (High): No cleanup on early failure

**Original code:** Lines 216-243 used `check=True` on `push`, `ls`, `install-create`. If any raised, the `rm -rf remote_dir` on line 275 was never reached. Temp files accumulated on the device across retries.

**Fix:** Wrap the entire body in `try/finally`:
```python
session_id: str | None = None
try:
    # ... all the work ...
finally:
    adb.shell(["rm", "-rf", remote_dir], timeout=15, check=False)
    if session_id is not None:
        adb.shell(["pm", "install-abandon", session_id], timeout=30, check=False)
```

### Bug 4 (High): Commit failure doesn't abandon session

**Original code (lines 277-281):**
```python
if not commit_result or not commit_result.ok:
    raise ADBError(...)  # ← no install-abandon before raising
```

**Problem:** Stale install session remains active, blocking subsequent installs.

**Fix:** The `finally` block now always calls `install-abandon` if a session was created. (A committed session ignores `abandon` — safe no-op.)

### Bug 5 (Medium): `int()` crash on non-numeric stat output

**Original code (line 240):**
```python
total_bytes += int(size_result.stdout.strip())
```

**Problem:** On some Android implementations (older toybox), `stat -c %s` may return empty string or error text. `int("")` raises an unhandled `ValueError`.

**Fix:** Validate with `isdigit()` before `int()` conversion (see Bug 2 fix above).

### Bug 6 (Medium): Device-side paths break with spaces

**Problem:** If an APK file has a space in its filename (e.g., `my app.apk`), the device-side shell command becomes:
```
stat -c %s /data/local/tmp/_install_splits/my app.apk
```
The shell splits this into: `stat`, `-c`, `%s`, `/data/local/tmp/_install_splits/my`, `app.apk` → stat gets the wrong path.

**Fix:** Add a `_quote()` helper that wraps remote paths in double quotes:
```python
def _quote(path: str) -> str:
    return f'"{path}"'
```
Used for all `stat` and `install-write` paths on the device:
```python
qpath = _quote(f"{remote_dir}/{f}")
adb.shell(["stat", "-c", "%s", qpath], ...)
```

## Verification

- `pytest`: **66/66 passed**
- `python -c "from automation_core.device import install_package, _install_multi_split, _install_single, _quote"`: **OK**
- Test coverage gap: No tests exist for `install_package`, `_install_multi_split`, `_install_single`, or `abandon_stale_install_sessions`.

## Key Takeaways for Future Audits

1. **`adb shell` is NOT the same as direct `subprocess.run`** — arguments are concatenated with spaces for the device shell → always quote remote paths.
2. **Silent `if ok:` without `else` is a code smell** — failures hidden from the user are bugs waiting to happen.
3. **`try/finally` is the only reliable cleanup pattern** — especially when `check=True` raises on any step.
4. **Split APK knowledge:** The `pm install-write` split_name parameter should match the APK filename (without extension), not fabricated index-based names.
5. **`int()` on `"".strip()` is always a crash waiting to happen** — validate non-empty and `isdigit()` first.
