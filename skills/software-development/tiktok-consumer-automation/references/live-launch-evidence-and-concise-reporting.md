# Live canonical launcher: evidence and concise reporting

## Contract

For a user-authorized TikTok live upload that specifies the canonical launcher and exact arguments:

1. Run the exact launcher from the requested repo/workdir; do not create a wrapper, ad-hoc launcher, `xargs`, Bash loop, or outside worker.
2. Before launch, scan only actual `python.exe`/`pythonw.exe` processes and reject a command line containing `-m tiktok_workflow`. Do not treat the diagnostic shell/PowerShell wrapper as a worker.
3. Use a durable background process and wait for the launcher itself to exit. A tool polling timeout is not batch completion; keep polling.
4. Treat launcher preflight output as evidence: record target list, lock skips, runtime/core version, and any inventory/account/video gates the launcher reports.
5. Never infer upload success from launcher exit code, per-machine `exit=0`, or process disappearance. Parse `summary.csv` and, for claimed successes, independently require the workflow's report evidence (`status`, `post_verified`, and accepted/verified post state according to the consumer contract).
6. If the worker remains alive when the bounded wait/tool budget ends, report `INCOMPLETE_PENDING_WORKER` with PID and log path. Do not kill or retry.
7. Final response should be short Vietnamese when the operator requested that style: exact launcher/batch directory, stdout/stderr location pattern or paths, exit code, summary.csv path, and an evidence-based status summary. Explicitly say when there are zero verified successes or only `MANUAL_REVIEW`/`UNKNOWN` evidence.

## Observed batch pattern

A completed canonical batch can exit nonzero while still producing a valid `summary.csv`. In the 2026-08-13 Tik2 run, the launcher printed `0/80 target verified-success`, and the summary contained 37 `SKIPPED_LOCKED` plus 43 `LỖI`; therefore the correct result was not success, despite the process having exited and report files existing for some machines. Reports showing `post_submission_state=UNKNOWN` and `MANUAL_REVIEW` are not upload proof. A missing-video `VIDEO_PATH_ERROR` and watcher proxy-readiness timeout are failure/manual-review evidence, not reasons to retry inside the same live task.

## Path/evidence checklist

- Batch directory: `D:\CodexRuntime\tiktok-video\batch-runs\<batch-id>\`
- Summary: `<batch-dir>\summary.csv`
- Per-machine logs: `<batch-dir>\machine-<N>.out.log` and `.err.log`
- Per-machine report when present: path from the `Report` column in `summary.csv`
- After completion, rescan for live actual Python workflow processes; no live process means the batch has ended, not that it succeeded.
