# Pause/resume and resource checks

## Verified workflow

1. Poll the managed sessions first. In this class of farm run, the download session is identified by `download_by_niche.py`; Tik4 render is identified by `run_tik4_random_render.ps1` or its child render command.
2. Kill only the requested session(s). A background wrapper can leave child Python/ffmpeg processes alive, so run a fresh process query matching the command names after killing.
3. Resume download from the same state database and output root with the global ledger flags preserved. This makes resume idempotent and avoids duplicate downloads.
4. Resume Tik4 with the project launcher and `-Parallel 1` when the user requests one worker. Do not use a different workbook/source-map command merely because it starts successfully.
5. Poll after launch and use output evidence such as `PLAN`, `RUN`, `PROGRESS`, or a current download message. A created wrapper process alone is not proof of active work.

## Important incidents and lessons

- A PowerShell multiline invocation embedded in a bash command failed because PowerShell continuation backticks were not preserved. Prefer a single-line bash launch or invoke the `.ps1` launcher directly; verify with `poll` afterward.
- An earlier generic `tik3_multi_batch.py` command used a source mapping that included a source folder with only one video and stopped on the minimum-source guard. The project-specific Tik4 launcher uses the correct workbook/mapping and should be preferred.
- Render progress may leave partial output when stopped. Resume flags should skip valid existing MP4s rather than restart the completed portion.
- Download logs can contain ordinary per-video `403`, unavailable, or sign-in errors while the batch remains alive. Classify these separately from a process-level exception or state DB failure.
- When the machine has recently experienced memory or power instability, keep render worker count explicit and avoid increasing concurrency without fresh resource evidence.
