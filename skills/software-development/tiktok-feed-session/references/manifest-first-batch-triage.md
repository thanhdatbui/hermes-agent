# Manifest-first batch triage

Use this reference after a feed-session watchdog report identifies failed machines.

## Evidence order

1. Run `python D:/Taadaa/tools/inspect_machine.py <N>` for every named machine. A timeout is current transport/hardware evidence; do not infer the live UI from historical artifacts.
2. Read the run's `run_manifest.json` and use `multi_machine_summary` as the machine-level source of truth.
3. Open only the machine-scoped `log.jsonl` and artifact paths supplied by each manifest record.
4. Reconcile `summary.txt` against the manifest and report any mismatch.

## Classification

- `config-error` caused by an empty account row: capacity/data state, not a runner failure.
- `blocked-proxy-vpn`, offline, Wi-Fi disconnected, ADB/USB errors, ATX unavailable, screencap/ADB timeout: transient or infrastructure evidence; do not dispatch a global code patch solely from these.
- SystemUI/FOTA/launcher or other non-TikTok focus: OS/system-dialog focus issue; capture evidence before teardown.
- `manual-needed` with deterministic detector, switcher, or profile mismatch reason: candidate for a narrowly scoped flow/detector fix after reading the exact failing step.

## Reporting

Report both cluster totals and the reconciliation equation: `success + non-success = expected machines`. If the human-readable summary and manifest disagree, name both values and state which source was authoritative. Keep empty slots separate from runtime failures.

## Incident example pattern

A feed run can have summary text claiming one success total while the manifest has a different count. The correct response is not to rerun the batch blindly: extract the per-machine list from `multi_machine_summary`, classify each non-success, and only escalate deterministic switcher/detector failures to code work. Preserve capture/OCR evidence before any teardown and never use manual ADB input as the fix.
