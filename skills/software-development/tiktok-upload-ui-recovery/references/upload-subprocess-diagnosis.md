# Upload subprocess diagnosis

## Trigger
Use when a final-session upload hook reports `failed`, `timeout`, or zero verified uploads.

## Required evidence
- Identify the exact runtime source used by the child process: commit, checkout, file mtime, and command.
- Preserve machine, workbook, video path, start/end timestamps, timeout budget, PID, and process-tree cleanup result.
- For nonzero exit: retain stdout/stderr tails and traceback. `EOFError` at `input()` proves an interactive confirmation prompt was reached from a non-interactive worker.
- For timeout: retain partial stdout/stderr, latest workflow checkpoint/state, and a timeout-time screenshot/log artifact. `upload-timeout` is a wrapper symptom, not a root cause.

## Important classification pitfall
A single root cause can produce different outer statuses. With a stdin prompt, one child may receive EOF and fail immediately while another remains blocked waiting for input until the 900-second deadline. Do not classify `failed` and `timeout` as separate root causes until their child output is compared.

## Fix and verification sequence
1. Fix the non-interactive execution path (no live prompt in a worker; explicit safe confirmation policy).
2. Improve timeout handling so partial output and state are persisted and the child process tree is cleaned up.
3. Run one target-scoped upload canary using the exact runtime source that will run in batch.
4. Require real post verification, matching machine/video/workbook mapping, and no process leak before widening to a batch.

## Prohibited conclusions
Do not claim concurrency, proxy, ADB, UI, or TikTok post failure without corresponding state/log evidence. If evidence is missing, report `root cause unconfirmed` and remain in detection.
