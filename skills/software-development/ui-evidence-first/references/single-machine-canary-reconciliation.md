# Single-machine canary reconciliation

Reusable evidence recipe for a strict, one-machine live canary.

## Scope gate

- Normalize the target to a numeric machine ID.
- Do not inspect, lock, launch, or report on excluded machines.
- Keep one fresh artifact namespace for the run.

## Preflight binding

1. Run `python D:/Taadaa/tools/inspect_machine.py <N>` and save the exact output.
2. Read only the current target manifest entries and resolve `machine`, `serial`, `account_row`, scheduled account, and slot time.
3. Query SQLite `farm_account_info` for the target machine and slot; record username and machine/slot fields.
4. Read the safe workbook's authoritative sheet and record the physical row, machine, device ID, and account ID. Workbook row numbering and runner row/index flags are not interchangeable: prove the conversion from the actual runner command.
5. Check both `machine_<N>.lock.json` and `serial_<SERIAL>.lock.json` in every canonical lock directory. Preserve any active or retained lock; never delete or override it.

## One-shot launch

Use the official runner, with only the target machine and proven row/slot, and bounded flags appropriate to the task. Capture the literal command, exit code, stdout, stderr, run ID, and artifact root. A launcher exit of zero is not by itself a PASS. Do not retry a failed or ambiguous canary in the same scope.

## Artifact closeout

Read the target machine's fresh `run_manifest.json`, `summary.txt`, and `log.jsonl`. Confirm:

- final status and stop reason;
- target machine and serial/device artifact identity;
- expected row/account binding, including `source_row` when present;
- requested versus completed actions;
- blocker taxonomy and any manual-needed events;
- matching screenshot and UI XML under the same attempt directory.

Validate that XML parses and screenshots are real, fresh, machine-scoped artifacts with valid file signatures. Treat missing, stale, ambiguous, or mismatched evidence as `UNPROVEN`, even if the runner claims success.

## Lock closeout

Read both lock aliases again after the runner exits. Prefer a fresh `recovery_lock_handoff.json` showing `finish_succeeded: true` and `lock_status: released`, but corroborate it with direct absence checks. Report each alias and each lock directory explicitly. `released` is not established merely because a process exited.

## Common reconciliation pitfall

The inspector/manifest may expose a physical serial while the runner emits opaque internal identifiers such as `device:<hash>` or `account:<hash>`. Do not call this a mismatch without checking the manifest's `source_row`, workbook binding, and target-scoped artifact path. Conversely, never silently merge opaque IDs from another machine or run.
