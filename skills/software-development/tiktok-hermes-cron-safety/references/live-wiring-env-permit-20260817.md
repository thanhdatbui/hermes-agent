# Live-wiring Hermes cron for Taadaa feed (2026-08-17)

Root facts verified this session:
- `hermes cron create/edit` has NO env field. no_agent scripts run with the **gateway process env**
  (`cron/scheduler.py` → `_run_job_script` → `_sanitize_subprocess_env(os.environ.copy())`),
  cwd = job `workdir`.
- The gateway itself is launched by `~/AppData/Local/hermes/gateway-service/Hermes_Gateway.vbs`
  which sets ONLY `HERMES_HOME`, `PYTHONIOENCODING`, `HERMES_GATEWAY_DETACHED`, `VIRTUAL_ENV`,
  `PYTHONPATH`. No provider keys live there → agent-mode cron jobs 401
  ("No active credentials for provider: codex"). Script-only (no_agent) jobs don't care.

## Activation + config contract (repo-anchored, no env)

Three wrapper files (`scripts/hermes_cron/tiktok_{picker,runner,watcher}.py`) now support:

1. `is_activated(env)`: `HERMES_CRON_<KIND>_ENABLED=1` → `HERMES_CRON_PERMIT_FILE` env → fallback
   `repo_root()/runtime/hermes-cron/permits/<kind>.permit` (regular non-symlink; missing = inert).
2. `repo_env_overrides()`: reads `repo_root()/runtime/hermes-cron/env.json` (regular non-symlink,
   dict[str,str|int]). `merged_env(os.environ)` = process env with file values via `setdefault`
   (process env wins). Missing key after merge → wrapper exit 3 (fail-closed, no child).
3. `hermes_cron_runner.py` `_runner_live_permit()`: `--execute/--repo/--feed-workbook` accepted
   ONLY when `runtime/hermes-cron/permits/tiktok_runner.permit` exists; then
   `ProductionFeedLauncherAdapter(enabled=True)` + `run_entry(execute=True)`.
4. `target_python()` converts MSYS `/d/...` default to `D:\...` (env override untouched).

## env.json schema used (kibe host example)

```json
{
  "HERMES_CRON_STATE_ROOT": "D:/Taadaa/runtime/kibe/cron-state",
  "HERMES_CRON_SOURCE_CONFIG": "D:/Taadaa/runtime/kibe/cron-source/hermes_cron_source_config.json",
  "HERMES_CRON_OFFLINE_ROOT": "D:/Taadaa/runtime/kibe/cron-offline",
  "HERMES_CRON_OWNER_ID": "hermes-cron-kibe",
  "HERMES_CRON_WORKER_ID": "picker-worker",
  "HERMES_CRON_FEED_STATE_JSON": "D:/Taadaa/runtime/kibe/cron-state/feed_state.json",
  "HERMES_CRON_POST_STATE_JSON": "D:/Taadaa/runtime/kibe/cron-state/post_state.json",
  "HERMES_CRON_REPORT_JSONL": "D:/Taadaa/runtime/kibe/cron-state/report.jsonl",
  "HERMES_CRON_REPO": "D:/Taadaa/tiktok-luot nuoi acc",
  "HERMES_CRON_FEED_WORKBOOK": "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx"
}
```

Operator creates env.json + the 3 permit files only when the user approves live; the files are
runtime state, never committed.

## E2E probe (mô phỏng cron thật, NOT live device)

```bash
# 1. permit + env.json present → wrapper must spawn the business child (fail at missing
#    source config = correct fail-closed, NOT a wrapper bug)
echo test-activation > runtime/hermes-cron/permits/tiktok_picker.permit
# create env.json (above) ...
PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo' \
  /d/Taadaa/python-envs/automation/Scripts/python.exe -B scripts/hermes_cron/tiktok_picker.py
# expected: CalledProcessError from hermes_cron_picker.py (source config file absent) — wrapper OK

# 2. CLEANUP — MUST remove before running the wrapper test suite
rm -f runtime/hermes-cron/env.json runtime/hermes-cron/permits/*.permit
```

## Test suite that must stay green

```
PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo' \
  /d/Taadaa/python-envs/automation/Scripts/python.exe -B -m pytest \
  python_runner/tests/test_hermes_cron_wrappers.py \
  python_runner/tests/test_hermes_cron_contract.py \
  python_runner/tests/test_hermes_cron_integration.py \
  python_runner/tests/test_hermes_cron_p1_r2.py \
  python_runner/tests/test_hermes_cron_staging.py -q
# 2026-08-17 state: 216 passed, 1 skipped
```

## Gate to live (only after user approval)

1. Generate `hermes_cron_source_config.json` from the real workbook
   (`scripts/generate_cron_source_config.py`).
2. Create `runtime/hermes-cron/env.json` + 3 permit files.
3. `hermes cron resume <picker|runner|watcher id>` (jobs stay paused until then).

## Pitfalls

- Leftover `env.json`/permit in the repo breaks `test_wrapper_default_off_*` — cleanup after probes.
- Fuzzy `patch` on CRLF wrapper files can mis-indent `return` INSIDE an `if` → `target_python()`
  returns None → `TypeError: os.fsdecode ... not NoneType` from subprocess. Debug: print `repr(argv)`.
- Convert any custom `reap-dead-owner-locks`-style watchdog to `no_agent=true` script (empty stdout =
  silent; nonzero = alert) instead of an agent job — 0 tokens and immune to gateway-key 401s.