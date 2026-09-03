# Live-entry run recipe (9C.2 pilot — machine 5 / row 2, 2026-08-15)

End-to-end recipe for running ONE live entry via `live_entrypoint.run_once` with a
canonical permit + full assignment manifest. All paths are the authority worktree
(`D:\Taadaa\context-worktrees\tiktok-luot-nuoi-acc-phase9-authority-<hash>`).

## 1. Preflight (read-only, no device action)

- `adb devices` → confirm target serial online: `9885e64b4a434a3037  device` (machine 5).
- Screenshot the device to confirm clean home state: `adb -s <serial> exec-out screencap -p > pre.png`
  (no popup/lock/login; TikTok icon present). Verify with vision.
- Host config `D:\Taadaa\machine-config\kibe.yaml`: `host_id: kibe`, `machine_range: [1,80]`,
  `workbook_root: D:/OneDrive/TaadaaData/kibe`, `runtime_root: D:/Taadaa/runtime/kibe`.
- Workbook `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` — scan column `May` for the
  machine; `account_row` is the slot on that machine (see workbook-mapping section in SKILL.md).

## 2. Build manifest + permit (Python, run with automation venv)

```python
import sys, tempfile, uuid, hashlib, json
from pathlib import Path
from datetime import datetime
REPO = Path(r"D:\Taadaa\context-worktrees\tiktok-luot-nuoi-acc-phase9-authority-<hash>")
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "python_runner"))
from python_runner.hermes_cron.live_entrypoint import _repo_root, sha256_file
from python_runner.hermes_cron.manifest import _entry, build_manifest_payload
from python_runner.hermes_cron.models import canonical_json
from python_runner.hermes_cron.source_config import SourceConfig

MACHINE, ROW, SERIAL = 5, 2, "9885e64b4a434a3037"
DAY, SEED, WORKER = "2026-08-15", 7, "worker-live"
WB = r"D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx"
ART = r"D:\Taadaa\runtime\kibe\artifacts\9c2-m5-row2"

source = SourceConfig.from_dict({
    "feed_source": {"revision": "live-9c2-v1", "headers": {},
                    "accounts": [{"account_id": "acct-m5-r2", "machine": MACHINE, "serial": SERIAL, "account_row": ROW}]},
    "post_source": {"revision": "live-9c2-v1", "headers": {},
                    "accounts": [{"account_id": "acct-m5-r2", "account_row": ROW, "machine": MACHINE,
                                  "serial": SERIAL, "target_count": None, "video_available": None}]},
    "feed_state_revisions": [{"account_id": "acct-m5-r2", "state_revision": "feed-v1"}],
    "post_state_revisions": [{"account_id": "acct-m5-r2", "state_revision": "post-v1"}],
})
entry = _entry(source.feed_accounts[0], DAY, f"provisional:{DAY}",
               datetime.fromisoformat(f"{DAY}T07:00:00+07:00"), "feed_only", SEED)
payload = build_manifest_payload(DAY, source, SEED, WORKER, WORKER, [entry], [])
staging = Path(tempfile.mkdtemp(prefix="9c2-live-"))
manifest_path = staging / f"{payload['assignment_id']}.json"   # filename MUST be <assignment_id>.json
manifest_path.write_bytes(canonical_json(payload))
manifest_id = f"{payload['assignment_id']}:{DAY}"

permit = {"schema_version": 1, "permit_id": f"pilot-{uuid.uuid4().hex[:8]}",
          "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
          "manifest_id": manifest_id, "entry_id": entry["entry_id"],
          "machine": MACHINE, "row": ROW, "serial": SERIAL, "host_id": "kibe",
          "worker_id": WORKER, "account_workbook": WB, "artifact_root": ART, "repo": str(REPO)}
permit_path = staging / "permit.json"
permit_path.write_bytes(canonical_json(permit))   # canonical_json returns BYTES
```

Key traps (all hit in the 9C.2 pilot):
- `python_runner` is a namespace package (no `__init__.py`); both `REPO` and `REPO/python_runner`
  on sys.path.
- Pass Windows paths as argv, never `/d/...` MSYS paths.
- Canonical permit only — `build_activation_permit` adds pilot keys that `run_once` rejects.
- `canonical_json()` returns bytes → `write_bytes`, not `write_text`.

## 3. Run the live entry

```python
from python_runner.hermes_cron.live_entrypoint import run_once
result = run_once({"permit_file": str(permit_path)})
print(json.dumps(result, ensure_ascii=False, indent=2))
```

Run with `PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo'` exported
(timezone workaround). Feed session runs several minutes; watch
`D:\Taadaa\runtime\kibe\artifacts\9c2-m5-row2\<run>\log.jsonl` and the
`feed-session-smoke/swipe_N_after/` screenshots.

## 4. Interpret the result

- `launcher_failed` + artifact dir EMPTY → spawn itself died. Re-run the exact argv manually
  (capture stdout+stderr) to see the PowerShell/python error. Known causes fixed in 9D.2:
  MSYS `PYTHON_EXE` (`CommandNotFoundException`) and leaked `PYTHONPATH` (`PIL._imaging`
  ImportError from the Hermes venv).
- `launcher_failed` + artifact dir populated → the feed session RAN but returned nonzero. Read
  `summary.txt` (`selected_total_videos`, `swipes_completed`, `final_status`) and the last
  `swipe_N_after` screenshot. See SKILL.md "feed not confirmed" section — success is
  `swipes_completed >= selected_total` on the verified account, NOT a fixed 30.
- Permit is consumed once even on failure — build a fresh permit (new staging dir) per retry.

## 5. Evidence required (plan 9C.2)

- `phase9-9c-human-gate.txt` (user row+machine approval record)
- artifact summary (real `summary.txt` in the run dir)
- independent profile screenshot (PNG under `feed-session-smoke/profile_preflight_identity_guard/`)
- verifier record with `ACCEPTED` (written by the script into the artifact root)
- permit consume marker (`permit.consumed.json`)
- Never treat process exit code / scheduler status / `report.json` alone as proof.
