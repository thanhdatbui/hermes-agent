# Gateway reset and session-hook recovery (2026-08-26)

## Evidence sequence

1. Read current scheduler job state, but treat `ok`, `enabled`, and `scheduled` as scheduler-only evidence.
2. Read the logical-day runner lease and probe every recorded PID. A lease is not proof of dispatch.
3. Inspect the exact child command line. Confirm the intended PowerShell launcher, Python interpreter, cohort artifact, assignment manifest, worker ID, and machine set.
4. Find the newest live run directory and verify `run_manifest.json`, `summary.txt`, `log.jsonl`, and per-machine artifacts. Count terminal machine publications, not account entries or follow actions.
5. If a detached child exits before machine artifacts, reproduce the same PowerShell bridge without `-Run`; compare the runner argv with PS1 parameters and the Python parser. Only after safe preflight passes should a live retry be considered.

## Bridge failures observed

- Passing `-CohortArtifact` to a PS1 that does not declare it causes PowerShell to exit before Python starts.
- Passing `ACTIVE.json` instead of the referenced full assignment manifest fails assignment preflight.
- Running the direct script without a repository-root `sys.path` bootstrap can fail on `No module named 'python_runner'`.
- An inherited Hermes `PYTHONPATH` can shadow the automation environment's Pillow and produce `_imaging` import errors. Remove it in the child environment and verify `run_tiktok.py --help` with the automation interpreter.

## Session-hook invariant

The cohort artifact is the authority for `session_index`. Copy it into child context before running hooks. Upload must be guarded by exact final-session identity (`session_index == 3`); a missing value, malformed value, or session 1/2 must skip and write an explicit result. Do not let generic defaults or live recovery flags turn session 2 into an upload session. A regression should patch the upload subprocess and assert it is not called for session 2.

## Reporting

Use concise Vietnamese reports. Separate scheduler tick, lease/PID, child process, fresh artifact, machine progress, and blocker. Say `chưa xác minh` when any proof is absent. A completed feed run can still be `failed` or `partial`; report success, manual-needed, VPN/config blockers, follow counts, and upload status separately. Never call a count of successful follow actions a count of machines.

## Scope safety

Run the repository bootstrap before edits. If it returns `DIRTY-ALLOWLIST-CONFLICT`, preserve the dirty work and stop writes to conflicting allowlist files. Do not reset or overwrite prior work merely to unblock a fix. Installed wrapper copies are runtime artifacts and must be synced only after the repository change passes its focused verification.
