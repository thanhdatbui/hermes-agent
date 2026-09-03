# Render interpreter and worker semantics

## Target-machine Python provenance

For TikTok build/render/test commands, execute with the target machine's installed Python and capture real terminal output. Do not use Hermes `execute_code` Python as the build/runtime interpreter and do not fabricate a result.

Before handing out a command, verify interpreter resolution:

```powershell
where.exe python
py.exe -0p
py -3.12 -c "import sys; print(sys.executable); print(sys.version)"
```

Do not assume bare `python` is the machine interpreter. On the Kibe Windows host it can resolve to the Hermes venv first. Prefer `py -3.12 -u ...` or the absolute machine path (after confirming it and its dependencies):

```text
C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe
```

When a process is already running, inspect its full command line and parent/child chain before restarting. A Hermes-v-env parent may launch a uv-managed child; that is not two render workers, but it violates the target-interpreter provenance rule for a new run.

## `--parallel` versus CPU threads

`--parallel 1` means one FFmpeg job/process at a time; it does not cap FFmpeg or libx264 threads. Confirm the generated command/log and look for the libx264 line (`threads=N`, `lookahead_threads=N`). CPU can remain high with one worker when the filter graph and x264 encoder use many threads.

## Continuing an interrupted render

1. Check for an existing `ffmpeg.exe`/runner for the same run before launching another copy.
2. Reuse the original run-id, source file list, source/output mapping, slot, machine-id, and seed offset so already-rendered outputs are skipped and remaining tasks keep deterministic seeds.
3. Do not add `--overwrite` for continuation; use existing-output verification/skip semantics.
4. Verify progress from the run metadata and output count after the process exits.

## Evidence pattern

A Task Manager screenshot is only a point-in-time view and may omit a process from the visible top rows. Cross-check with `tasklist`, full process command lines, run metadata, and (when needed) a short CPU counter sample. Treat the live process query as authoritative for whether FFmpeg is still rendering.
