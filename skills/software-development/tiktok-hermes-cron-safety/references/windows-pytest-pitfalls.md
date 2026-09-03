# Windows / pytest / `tiktok-luot nuoi acc` pitfalls (durable)

Captured while remediating Phase 9A.5 live-entrypoint safety seams with strict TDD.

## 1. Symlink creation needs a privilege not in every shell
`Path.symlink_to()` raises `OSError(22, 'A required privilege is not held by the client')` on
Windows CI shells that lack SeCreateSymbolicLinkPrivilege.
**Fix:** wrap the symlink leg in try/except OSError; if it fails, skip that assertion (the symlink
fail-closed path is still covered by the present-file and takeover-guard legs):
```python
sym_created = False
try:
    (lock_root / "machine_1.lock.json").symlink_to(target)
    sym_created = True
except OSError:
    sym_created = False
if sym_created:
    ok, reason = le._production_lock_reader(1, "SERIAL_A", lock_root=lock_root)
    assert ok is False and reason == "device_lock_symlink"
```

## 2. monkeypatch.setattr lambda that calls the patched attribute → infinite recursion
```python
monkeypatch.setattr(le, "_production_lock_reader",
                    lambda m, s, **kw: le._production_lock_reader(m, s, lock_root=lock_root))  # RECURSES
```
**Fix:** capture the original first, then call `_orig`:
```python
_orig = le._production_lock_reader
monkeypatch.setattr(le, "_production_lock_reader",
                    lambda m, s, **kw: _orig(m, s, lock_root=lock_root))
```

## 3. `canonical_json` returns BYTES, not str
`models.canonical_json(obj)` → bytes (the canonical canonical form). `Path.write_text` then raises
`TypeError: data must be str, not bytes`.
**Fix:** use `write_bytes(canonical_json(obj))`. Same for any explicit JSON fixture write.

## 4. `sha256_file()` reads the file at CALL time
If you compute `observation["screenshot_sha256"] = le.sha256_file(png)` and then later overwrite `png`
with different bytes, the declared hash no longer matches the on-disk file → you get
`verifier_screenshot_sha_mismatch` instead of the intended `verifier_screenshot_not_png`.
**Fix:** compute declared hashes AFTER writing the FINAL bytes; for a fake-PNG leg, write the non-PNG
bytes, compute its hash, build the observation with that hash, THEN (if needed) overwrite with a valid
PNG for the next leg — but remember each leg recomputes `sha256_file` against current disk state.

## 5. `manifest.validate_manifest` rejects same-account multi-entry LEGACY (non-block) manifests
For a legacy assignment manifest, two entries sharing the same `account` raise
`MANIFEST_IDENTITY_MISMATCH` at `validate_manifest`/`load_snapshot` (line ~305), NOT at
`_select_manifest_entry`. So a `_live_fixture` that builds two `_entry(...)` for the same account and
then calls `load_snapshot` fails before your unit test runs.
**Fix:** for `_select_manifest_entry` unit tests, build the raw payload dict directly from
`build_manifest_payload(...)` and pass it to `_select_manifest_entry` WITHOUT calling `load_snapshot`;
for a full-fixture (run_once) test, use a single-entry manifest so `load_snapshot` passes, then test
duplicate-id rejection by constructing `dup = dict(payload); dup["entries"] = [dict(e1), dict(e1)]` and
calling `_select_manifest_entry` directly.

## 6. pytest on Windows must run from the worktree with the automation venv + tzdata
Always run from inside the authority worktree so `python_runner` is importable, with:
```
PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo' \
/d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest ... -p no:cacheprovider
```
Use `PYTHONPYCACHEPREFIX="${TEMP}/pcc_<rand>"` to avoid cross-session .pyc cache collisions.

## 7. The fixture-injected host stand-in must set DISTINCT workbook_root / runtime_root
If `_allow_host` returns `workbook_root == runtime_root`, the `artifact_root` (under runtime_root) would
trivially be "under workbook_root" and the containment check `not _is_within(artifact_root, workbook_root)`
fails. Make them distinct dirs (e.g. `tmp/wb` and `tmp/rt`) so the artifact is provably NOT under the
workbook root.

## 8. `load_snapshot` binds the filename, not only payload bytes
Even valid canonical bytes fail with `MANIFEST_IDENTITY_MISMATCH` when written as `manifest.json`.
`load_snapshot` requires `target.name == f"{payload['assignment_id']}.json"`.
**Fix:** build the payload first and write it under the assignment-derived filename:
```python
manifest = tmp_path / f"{payload['assignment_id']}.json"
manifest.write_bytes(canonical_manifest_bytes(payload))
```
Do not weaken production validation to make a fixture pass.

## 9. Isolate positive and negative fixture cases
A negative case may leave `wb/`, a consume marker, evidence files, or lock aliases behind. Reusing the same
`tmp_path` for a later canonical fixture can then fail with `FileExistsError` or exercise the wrong branch.
**Fix:** create a fresh child directory per case, especially when comparing reject and accept paths:
```python
bad_dir = tmp_path / "bad"; bad_dir.mkdir()
good_dir = tmp_path / "good"; good_dir.mkdir()
```

## 10. A green `-k` slice is not the gate
Broad keyword expressions can omit required named tests while still reporting green. Run explicit required
node IDs first, then the complete Phase suite. Any old happy-path failure remains blocking even when every new
adversarial test passes.

## 11. Testing a wrapper that spawns an explicit target Python (Phase 9B.1 technique)
Wrapper templates (`tiktok_picker.py` / `tiktok_runner.py` / `tiktok_watcher.py`) spawn an explicit target
Python with a strictly allowlisted env and `cwd=repo root`. To test the spawn without running business code
or a live subprocess:
- **Use a `.cmd` shim as the fake "target Python"** — a `.py` cannot be exec'd directly as `argv[0]` on
  Windows (`OSError: [WinError 193] %1 is not a valid Win32 application`). The shim re-execs the real
  `python` to record `argv`/`cwd`/`env_keys` to a JSON file, then exits 0. Tests assert on that record
  (exact argv index, `cwd == repo root`, no forbidden env keys), never by grepping stdout.
- **A stripped child env needs Windows infra vars.** `subprocess.run(..., env=stripped_env)` fails to launch
  `python.exe` (`WinError 193`) unless `SystemRoot` / `SystemDrive` / `ComSpec` / `PATHEXT` / `TEMP` / `TMP`
  are present. The production wrapper must forward those (when set in the parent) — and the test's
  allowlist check must use case-insensitive comparison, because the child sees `SYSTEMROOT`/`COMSPEC` even
  though the parent set `SystemRoot`/`ComSpec`.
- **Env-allowlist assertion should check for forbidden/secret keys, not exact equality.** A `.cmd` shim
  adds its own vars (`OUT`, `PROMPT`) and the OS adds infra vars, so `child_keys <= allowed` is too strict.
  Assert: no key containing `SECRET`/`TOKEN`/`PASSWORD`/`AGENT`/`CREDENTIAL`/`API_KEY`, plus `TZ` present,
  plus empty stdout.
- **Pass a fake clock via env** (`HERMES_CRON_NOW=<ISO>`) to test HCM logical-day boundaries (00:00-01:59 →
  previous day; 02:00-05:59 → silent exit 0 empty stdout; 06:00-23:59 → today) without touching the real clock.

## 12. Writing evidence files from a git-bash heredoc: use `C:/...`, not `/c/...`
A `python - <<'PY'` heredoc that writes `Path('/c/Users/...')` on Windows resolves under the current drive
(`D:\c\Users\...`) and the file lands in the wrong place — silent data loss (the worker-result JSON ended up
in the worktree instead of `C:\Users\Kibe\...`). Use the native Windows path `C:/Users/Kibe/...` in Python
`Path(...)`, or `C:\\Users\\...` in bash. Verify with `test -f` + `ls` after writing.

