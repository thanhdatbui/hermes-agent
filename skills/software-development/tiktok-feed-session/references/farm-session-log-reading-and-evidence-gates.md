# Farm session log reading and evidence gates

## Trigger
Use this procedure when the user asks to read logs, check whether a ca/phiên ran, or asks for the result of a specific feed/upload/follow session. The requested output is an evidence lookup, not a strategy explanation.

## Procedure
1. Lock the target: date/logical day, ca, session index (for example `Phiên 3 ca sáng`), machine scope, and requested signals (feed, upload, follow, or combined).
2. Read the newest watchdog/cron completion output first. Then correlate it with actual artifacts: `summary.txt`, `run_manifest.json`, per-machine `log.jsonl`, `upload_result.json`, and `follow_result.json`.
3. Require explicit session identity. Do not infer `Phiên 3` from clock time alone. If the artifacts do not record the session index, report that the requested session is not identifiable from available evidence.
4. Exclude canary, recovery, debug, and single-machine test runs from farm totals. A nearby test run is not evidence for the farm session.
5. Keep plan and runtime separate. A plan can specify upload in session 3, but only upload evidence plus post verification proves upload success. A silent watchdog tick means no report was emitted; it does not prove failure.
6. Check process state only after reading artifacts. No process now means the run is no longer active, not that it never ran.

## Report format
- **Mục đích:** exact session/signal requested.
- **Kết quả:** only proven status, machine/account/video/upload details.
- **Blocker / giới hạn bằng chứng:** missing completion output, ambiguous metadata, or actual blocker.

Never replace a missing log result with the intended workflow or a guessed session number.
