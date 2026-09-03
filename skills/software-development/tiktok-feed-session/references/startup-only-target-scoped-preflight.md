# Startup-only verified Feed: target-scoped preflight

## Why this exists

A startup-only run is a bounded live check that prepares TikTok and verifies the Feed surface, then stops. It is not a follow session. The success contract is artifact-backed: exact target binding, TikTok foreground/package proof, semantic Feed proof, and all three outputs (PNG screenshot, XML UI dump, JSON evidence). `SKIPPED_LOCKED` is not Feed verification; it is a terminal skip for that invocation.

## Canonical workflow

1. Read the repository's startup-only contract and identify the canonical CLI. Do not invent a runner or substitute a full follow flow.
2. Bind the target with both machine number and serial. Print a redacted plan that makes `startup_only=true` visible.
3. Before any device action, check both shared-lock aliases: `machine_<N>.lock.json` and `serial_<SERIAL>.lock.json`. An active, foreign, blocked, or unverifiable owner is a skip; never force-unlock.
4. Scan live process metadata for competing consumers. Parse WMIC records independently, and accept only a real `python.exe`/`pythonw.exe` record whose own command line contains the upload module and the exact machine argument.
5. Run the canonical startup-only command once. It may prepare/unlock the device and launch TikTok according to its documented startup contract, but it must not load business-account state, switch accounts, navigate follower lists, scroll for candidates, or invoke Follow.
6. Verify the result from the emitted `FOLLOW_RESULT` plus the run directory. Success requires a verified Feed result and PNG/XML/JSON paths that exist and are readable. Exit code alone is not proof.
7. Recheck exact locks and target process state. Report skipped/blocked separately from verified success. Do not rerun merely because a detector skipped the target.

## Critical false-positive guard

Do not implement busy detection as:

```python
return f"--machine {machine}" in all_wmic_stdout and "tiktok_workflow" in all_wmic_stdout
```

That is unsafe in two independent ways:

- substring collision: machine `1` matches `--machine 10`, `--machine 11`, etc.;
- cross-record contamination: the machine token may be present in one process record while `tiktok_workflow` is present in another.

Instead, parse records and tokenize the command line (or use a Windows-safe argument parser). Require the same record to satisfy all predicates: executable name, module, exact machine value, and—when available—serial/config identity. A raw shell/diagnostic wrapper containing the query text is not ownership evidence.

## Evidence/reporting template

Record:

- canonical script and config path (no secrets);
- machine target and redacted serial tag;
- preflight lock aliases and exact process-match result;
- command exit code and elapsed time;
- `FOLLOW_PLAN` with `startup_only=true`;
- `FOLLOW_RESULT.status` and reason;
- PNG/XML/JSON paths plus existence/readability checks;
- final lock aliases and any competing target process.

Use explicit verdicts: `VERIFIED_FEED`, `SKIPPED_LOCKED`, `MANUAL_REVIEW`, or `LIVE_BLOCKED`. Never label a skip as “verified,” and never claim “no Follow” from inference alone when the runner can emit a follow count—report `followed=[]`/equivalent evidence and the startup-only mode flag.

## Session-derived reproduction pattern

When a machine-1 startup-only run is skipped while only other machines are visibly running video workflows, inspect the detector before touching locks. If exact machine/serial lock aliases are absent and no same-target process exists, the likely issue is a target-matching bug, not a stale lock. Preserve the skipped result and fix the guard with tests before attempting another live run.
