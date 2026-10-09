# Targeted alert → workbook row reconciliation and lease gate

## Purpose

Use for a single-machine alert when the requested outcome is an official canary or a concrete blocker. The workflow is deliberately machine-scoped: it must not become a fleet scan or a manual UI recovery.

## Evidence chain

1. **Native machine identity**
   - Run `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - Record serial, model, focus, and sleep/launcher status.
   - Treat launcher/sleep as current-state evidence only; it does not identify the account.

2. **Original alert/run artifacts**
   - Inspect the known current artifact root and the alert/run manifest or log.
   - Bind evidence by exact serial, not substring matches such as `machine_7` matching `machine_70`.
   - Read the exact log window around the alert/stop event. A folder name or a claimed `artifact_path` is not proof that the artifact exists.
   - If the current run has no target-machine artifact yet, state that explicitly.

3. **Workbook + DB reconciliation**
   - Query the authoritative DB directly, narrowly: `farm_account_info WHERE may = ?`.
   - Read the authoritative workbook with physical Excel row numbers.
   - Reconcile all available keys: machine number, serial/device ID, `tik`/slot, username, and runner row/slot index.
   - Do not confuse a runner option such as `--account-row-index 4` with physical Excel row 4. Prove the mapping from the runner command/assignment metadata and then report both values.
   - Example shape: runner slot 4 → fourth M7 record → physical workbook row 53 → `luongbong055`; DB must independently return `may=7, tik=4, username=luongbong055`.
   - A historical artifact for another account on the same serial is useful history but is not proof of the current account.

4. **M<N>-only lock/lease inspection**
   - Inspect only `C:/Users/<user>/.codex/device-locks/machine_<N>.lock.json` and a known machine-scoped busy/pending marker.
   - Verify the JSON fields: `pid`, `serial`, `command`, `run_id`, `lock_id`, `owner_active`, `pinned`, `user_authorized`, `started_at`, `last_heartbeat`, and `ttl_seconds`.
   - Check that the owner PID is alive and capture its exact command line. Compute heartbeat/lease age; do not call a live owner stale merely because the timestamp is old relative to the alert.
   - A root-level `.canary_pending` with `reason: fleet_busy` is a blocker signal, not permission to override the owner.

## Canary decision

Run the official target-scoped canary only if both conditions hold:

- workbook/DB/artifact reconciliation uniquely proves the target row/account; and
- the M<N> owner lease is absent or has been released through the canonical cooperative handoff/reap mechanism.

Never delete a lock JSON, force-kill the owner, pass a parent-lock flag as a user override, or use manual ADB taps to create a false canary window.

## Blocker report contract

If blocked, report:

- `MACHINE_SCOPED_BLOCKER`;
- exact machine and serial;
- exact workbook physical row, runner slot/index, account, and DB result if mapping is proven;
- lock path, PID, owner command, run/lock ID, owner-active/pinned/authorization state, heartbeat/TTL evidence;
- exact missing current artifact (for example, no `machines/machine_7/<run>/log.jsonl`, XML, or screenshot yet);
- no changes made, no manual taps, no lock override.

If mapping is not unique, identify the exact conflicting/missing key and stop. Do not substitute a historical account or summarize the whole fleet.

## Session-derived pitfall

A live 80-machine runner can have a valid M7 lock and no M7 artifact directory yet because machine scheduling is staggered. That combination means “owner active, target artifact not emitted yet,” not “stale lock” and not “canary may start.”
