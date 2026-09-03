# Machine 35 recovery — stale feed-scheduler lock reclaim + VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET (2026-08-09)

Session: user authorized "recover machine 35 safely and run its single-machine live upload
workflow to a terminal verified result" (covers cross-consumer stale lock cleanup per
"fix các máy này luôn").

## Reclaim recipe (verified live)

1. **Lock state read**: `machine_35.lock.json` + `serial_ce061606c3322c1603.lock.json`
   (identical sha256, same `lock_id`), `project=tiktok-luot nuoi acc` (feed scheduler),
   `status=blocked`, `owner_active=false`, pid=68180, started 10:05:35Z. Feed scheduler
   process was DEAD → lock stale (the "KHÔNG đụng" rule only covers LIVE sessions).
2. **PID-dead proof**: `wmic process where "ProcessId=68180" get Name,CommandLine,ProcessId /format:list`
   → no record. Full scan `wmic process get Name,CommandLine,ProcessId /format:list` →
   0 `tiktok_workflow` / `tiktok-luot` / `gan_proxy_fleet` processes (no replacement worker).
3. **Archive BOTH aliases** to `D:\CodexRuntime\tiktok-video\recovery-machine-35\lock-archive-<ts>\`
   + `evidence.json` (pre-hashes, alias consistency, pid-dead proof, device probes:
   boot_completed=1, battery 80/2/AC, tun0 inet, vichanger pid present, readiness
   `proxy_ready` + boot_id, authorization reason). Move originals, never delete.
4. **Post-archive recheck**: no lock file whose CONTENT `machine==35` remains. (Glob-prefix
   checks false-positive on other machines' serial locks — match by content or exact name.)
5. **Config**: byte-copy `config-machine-62.yaml` → `config-machine-35.yaml`, replace
   `machine: "62"` → `"35"` (assert exactly 1 occurrence), EOL/encoding preserved
   (LF, 862 bytes), `yaml.safe_load` → machine=35. Never print contents.
6. **Run exact command** as ONE background worker, output redirected + exit trailer:
   ```bash
   echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" \
     "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
     -m tiktok_workflow --config "D:/CodexRuntime/tiktok-video/config-machine-35.yaml" \
     --machine 35 --no-dry-run > /c/CodexRuntime/tiktok-video/manual-coord-35/worker-35-direct.log 2>&1
   echo "WORKER_EXIT_CODE=$?" >> .../worker-35-direct.log
   ```

## Result: FAILED (exit 2, MANUAL_REVIEW) — NEW signature

- **Signature**: `[VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET] Picker was not verified after the
  bounded create-entry recovery` — NOT in COMPAT registry yet (no handler, no retry).
- Precursor log chain: `[PROFILE_ACTION_SHEET_RECOVERY] Profile video action sheet dismissed
  with one Back` → `Tapped center create button via screenshot-verified fallback` →
  `Editor Next tapped but caption composer did not open` (attempt 1/3) → fail-closed
  MANUAL_REVIEW.
- Report `D:\CodexRuntime\tiktok-video\runs\run_ce061606c3322c1603_20260809_202535\report.json`:
  status=MANUAL_REVIEW, `post_submission_state=None`, `post_verified=false`,
  `post_tap_attempted=None`. Checkpoint `media_fingerprint_status=reserved` (retained).
- Worker retained its own handoff lock (machine_35 + serial alias, `project=tiktok-upload`,
  owner_active=false, pid=23460) — do NOT touch; only next bounded recovery.
- 18 artifacts preserved in run dir incl. `video-pick-profile-action-sheet-before/after.png`,
  `ui_capture_*`/`ui_recovery_*` jsons, `soft-reboot-video_pick-before.png`.
- No retry (2-attempt cap per signature; success requires VERIFIED_SUCCESS or the
  accepted-auto-finalized path).

## Pitfalls learned

- **Run dir prefix = raw serial**: `runs/run_<serial>_<timestamp>/` — derives serial from the
  serial lock filename (`serial_<serial>.lock.json`), glob `run_<serial>_*`. Do NOT
  sha256-hash the serial for this: hash prefix (18 hex) found 0 dirs, raw serial found 122.
- **WMIC `/format:csv` + comma-split false-positives**: CommandLine containing commas
  fragments into extra columns; CSV scan flagged a `feed_scheduler` token that the
  `/format:list` block scan disproved (0 real processes). Use `/format:list` for pid-dead
  proof and replacement-worker scans.
- **Post-archive recheck by content, not glob**: `any(...startswith('serial_'))` returns True
  when ANY machine has serial locks; match the lock JSON `machine` field (or exact name).
- **Dead feed-scheduler lock IS reclaimable**: `project=tiktok-luot nuoi acc` +
  `owner_active=false` + recorded pid dead (WMIC) + both aliases same lock_id → standard
  stale lock: add + archive + reclaim (user-authorized). The "feed scheduler — KHÔNG đụng"
  rule applies only to a live multi-machine session.