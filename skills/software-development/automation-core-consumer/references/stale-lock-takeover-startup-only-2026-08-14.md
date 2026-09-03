# Guarded stale-lock takeover + startup-only verify — session detail (2026-08-14, tiktok-follow máy 1)

Goal: user said "Guarded takeover stale lock máy 1 rồi chạy đúng một production
startup-only tới Feed; không Follow." End-to-end recipe that worked, with the
exact script shape and the proof points to assert.

## Preconditions verified (must match parent's stated lock identity)

- Lock files: `C:/Users/Kibe/.codex/device-locks/{machine_1.lock.json,
  serial_9885b64957334f5a46.lock.json}` — BOTH aliases, identical content:
  host `DESKTOP-3PFPGQC`, pid 15008, run_id `follow-1-90018de25f09`,
  lock_id `ed4322a2bdba464395d8a1805dc8a9e9`, status `running`, owner_active true.
- PID dead proof — use CORE detector, not own tasklist parsing:
  ```python
  import automation_core.device_lock as dl
  dl._pid_alive_windows(15008)   # False
  dl._pid_alive(15008)           # False
  ```
  (The skill's older `tasklist /FI "PID eq X" /NH` recipe still works, but the
  core detector is the same logic the lock store itself uses — prefer it.)
- Exact-machine process scan: follow_runner AND `tiktok_workflow` (video-upload
  consumer writes NO lock store — PITFALL 2026-08-09) → 0 hits for machine 1.
- ADB: `get-state` = `device`; `ro.product.model` = SM-G930F.
- Repo dirty pre-existing (HANDOFF, docs/ui-compatibility, follow_runner/*,
  NUL, uids.txt) — snapshot, never touch.

## Signature probe from the PINNED WHEEL (no install needed)

Python's zipimport reads a `.whl` directly on `sys.path`:

```
env -u PYTHONPATH PYTHONPATH='D:/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl' \
  'D:/Taadaa/python-envs/automation/Scripts/python.exe' -B -c "import inspect; import automation_core.device_lock as dl; print(inspect.signature(dl.acquire_device_lock))"
```

- `automation_core.__file__` → `...whl\automation_core\__init__.py` (proof it
  resolved from the wheel, not a site-packages copy).
- 0.4.44 signature (verified): `acquire_device_lock(*, machine=None, serial=None,
  project=..., command=..., lock_root=None, status='running', run_id=None,
  allow_takeover=False, takeover_scope=None, takeover_authorized=False,
  takeover_reason=None, takeover_mode=None, takeover_proof=None,
  bypass_proxy_readiness=False, readiness_timeout=180, readiness_root=None,
  live_vpn_verifier=None) -> DeviceLockLease`.
- **`DeviceLockLease` and `DeviceLockReleaseAudit` live in
  `automation_core.device_lock` — there is NO `automation_core.lease` module**
  (my first probe hit `ModuleNotFoundError: No module named 'automation_core.lease'`).
- Lease methods: `finish, release, release_with_audit, set_status`.
- `release_with_audit(self, *, reason='') -> DeviceLockReleaseAudit`; audit
  fields: host, run_id, machine, serial, reason, released_paths, timestamp.

## The takeover script (write OUTSIDE the repo; delete after)

Key points:
- Run with the wheel PYTHONPATH and the consumer venv python.
- Acquire with takeover args + `bypass_proxy_readiness=True` (stale-lock recovery
  must not require live proxy state).
- After acquire, assert BOTH alias files were rewritten: `run_id` = new,
  `lock_id` != old, `pid` == lease.pid, plus the provenance keys:
  ```json
  "takeover_from": {"pid": 15008, "project": "tiktok-follow", "run_id": "follow-1-90018de25f09", "status": "running", "lock_id": "ed4322a2..."},
  "takeover_authorization": {"scope": "FULL_SCOPE_TAKEOVER", "reason": "user authorized stale lock recovery for machine 1"}
  ```
- Release proof:
  ```python
  audit = lease.release_with_audit(reason="stale lock recovered; startup-only verification run complete")
  # audit.released_paths == [serial_....lock.json, machine_1.lock.json]  (2 paths)
  ```
- Post-release: both aliases `None` (absent) — no leftover file.

Observed run output (shape): `LEASE_PID` = new python pid (37476), new
run_id `follow-1-46bfe0a9f921`, new lock_id `0205ff...`; `TAKEOVER_OK`.

## Production startup-only run (exactly once)

```
cd /d/taadaa/tiktok-follow && \
env -u PYTHONPATH PYTHONPATH='D:/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl' \
  'D:/Taadaa/python-envs/automation/Scripts/python.exe' -B -m follow_runner.run_follow \
  --machine 1 --serial 9885b64957334f5a46 --config follow_runner/config.example.yaml --startup-only
```

- CLI facts: `--startup-only` REQUIRES `--serial` (workbook is NOT read);
  result `details.lock.workbook=false`; zero business actions (`followed=[]`).
- Result: `{"machine": 1, "status": "OK", "followed": [], "skipped": [],
  "blocked": false, ...}` + `lock_release.device.released_paths` = both aliases.

## Artifact verification (do not trust exit code alone)

Artifacts under `runs/startup-only/<run_id>/`:
- `evidence.json` → `final_feed_verification.passed=true`, foreground
  `com.ss.android.ugc.trill`, capture backend `persistent`, `VERIFIED_XML`.
- `screenshot.png` → PNG decode OK, 1080×1920 RGBA.
- `ui.xml` → parse OK, 184 nodes; semantic feed marker: `đề xuất` present.
  NOTE: "for you"/"following"/"home_tab" were ABSENT on this device — the VN
  marker `đề xuất` is the legitimate feed proof; absence of the English markers
  is not a failure.

## Post-run state

- Both lock aliases absent; no machine-1 python process; ADB device.
- `git status --short` identical to baseline (only pre-existing dirty files +
  untracked NUL/uids.txt; `runs/` not tracked).
- Temp probe script deleted after use.
