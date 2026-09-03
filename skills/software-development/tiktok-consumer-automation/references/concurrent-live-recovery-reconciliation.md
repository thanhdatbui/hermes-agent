# Concurrent live recovery reconciliation

Use this reference for a named TikTok upload-recovery subset when stale locks may race with another launcher, scheduler, or worker.

## Guard before archive

1. Read the current exact aliases for each named machine: `machine_N.lock.json` and `serial_<serial>.lock.json`.
2. Require both aliases to agree on machine, serial, project, `lock_id`, PID, `status=handoff`, and `owner_active=false`.
3. Check PID liveness independently on Windows with:

```bash
tasklist /FI "PID eq <PID>" /NH
```

Treat the PID as alive only when its numeric token appears in the tasklist output. Do not use `os.kill(pid, 0)` as the Windows liveness oracle.

4. Scan process metadata and accept a competitor only when it is an actual `python.exe`/`pythonw.exe` command line containing `-m tiktok_workflow --machine N`. A shell wrapper containing the same text is not sufficient.
5. If any alias disappears, becomes `running`, is recreated, or has a live competitor after the earlier preflight, stop that target and reconcile. Never archive based on the stale snapshot.

## Archive contract

Archive exactly two aliases per authorized target into a timestamped directory. Record a redacted evidence object containing scope, aliases, prior PID/status/project, matching-field checks, PID result, and foreign-preservation checks. Verify the archive contains exactly the expected aliases and no foreign or registration alias before removing the live stale aliases. Never use a broad `*.lock.json` glob.

## Artifact overlap rule

If newer `recovery-*` logs, run directories, or `idempotency/post-attempts/machine_N_video_*.json` receipts appear, pause before launching another worker. A durable `post_submission_state=ACCEPTED` is not permission for a blind upload retry. Let the state machine's receipt barrier verify/finalize the accepted post; a completed accepted receipt is already success evidence.

## Final proof

Wait until no named-target `tiktok_workflow` process remains. Resolve the report path from each worker's own log and read the report. Count success only when:

```text
status=SUCCESS
post_verified=true
post_submission_state=ACCEPTED
```

A `WORKER_EXIT=0` marker is not a success proof. If the marker is absent, record exit as unknown rather than inferring it. Final locks must satisfy:

- verified success: both aliases released;
- manual/blocked: both aliases retained as inactive `handoff` locks;
- excluded/foreign/registration machines: untouched and still accounted for.

Useful final summary fields per machine: `status`, `reason`, `post_submission_state`, `post_verified`, log path, report path, and final lock state.
