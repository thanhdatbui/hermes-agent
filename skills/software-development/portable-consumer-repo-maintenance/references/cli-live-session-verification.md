# CLI live-session verification recipe

Use this for a consumer CLI with a read-only plan and a fake-only live session.

## Probe contract

Create the verifier with:

```python
f = tempfile.NamedTemporaryFile(
    prefix="hermes-verify-", suffix=".py",
    dir=tempfile.gettempdir(), delete=False,
)
```

The verifier must add the repository root to `sys.path` before importing the CLI and must delete the file in a `finally` block (or the launcher must delete it immediately after the child exits and prove deletion).

## Focused assertions

1. Build a temporary safe workbook containing only machine, serial, and TikTok ID, plus a temporary config/state directory.
2. Replace `FollowAdapter`, `FollowState`, `FollowEngine`, and `subprocess.run` with failure sentinels. Run `--dry-run`; assert exit `0`, no sentinel fires, and the state directory is absent.
3. Replace the three constructors with fakes that capture calls. Return a fake engine result with `SKIPPED_LOCKED` (or `OK`), then assert:
   - adapter receives `(cfg.adb_path, row.serial, cfg.tiktok_package)`;
   - state receives `(machine, cfg)`;
   - engine receives exactly `(adapter, cfg, mapping, state)` with no `locks_enabled=False` override;
   - `run_session(machine, cfg.mode)` is called;
   - stdout contains exactly one `FOLLOW_RESULT` JSON line with the allowlisted fields.
4. Add a fake `CONFIG_ERROR` result and assert exit `1`; separately make mapping/config loading raise `ConfigError` and assert stderr plus exit `2` before any runtime constructor.
5. Keep the probe offline: do not invoke ADB, devices, TikTok, workbook writes, or live lock acquisition.

Report the categories independently: `Ad-hoc verification: PASS`, focused pytest count, `py_compile`, `git diff --check`, and any unrelated dirty files. A passing probe is not a substitute for the canonical suite count.
