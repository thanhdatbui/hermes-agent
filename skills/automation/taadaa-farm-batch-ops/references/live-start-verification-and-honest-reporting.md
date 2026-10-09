# Live-start verification and honest reporting

## Why this matters
A launcher success, WMIC `ReturnValue = 0`, a PID creation response, or an old stats JSON proves only that a process was requested or that a prior run completed. It does not prove a current worker is alive or making progress.

## Restart checklist
1. Use the canonical remote wrapper (`D:/Taadaa/tools/run_canary_266.py`) when direct coordinator SSH/SCP is blocked by the allowlist. Capture its WMIC PID/result.
2. Immediately inspect a fresh Admin log and live worker evidence. Confirm a current `ffmpeg.exe`/render worker PID or a fresh output-file/log delta. Admin WMIC jobs may run in Session 0 and remain invisible in the interactive desktop; that is expected, but it requires remote process/log evidence.
3. Scope every log result: `DONE`, `All requested render chain steps completed successfully`, and `SKIP` refer only to the specific run/Tik step that emitted them. A completed Tik8 chain does not prove Tik1–Tik7 are running.
4. Keep local and remote evidence separate. A local ffmpeg PID proves Kibe only; Admin needs a fresh Admin-side check.
5. For supplementary downloads, require strict niche/source matching and measurable progress. `exit_code=0` with `folders_repaired=0` means no folders were repaired; report that plainly. Investigate 0/30/44-source MP4 cases before claiming render completion.
6. Never ask the user to run a command that the coordinator can run. If execution is genuinely blocked by a guard or credential boundary, report `BLOCKED` with the exact error and do not turn launcher output into a false “running” claim.

## Evidence language
Use explicit labels: `RUNNING` only with a live process plus fresh log/output evidence; `DONE` only with the scoped run and output verification; `BLOCKED` with the exact blocker; `NO_PROGRESS` when repeated rounds leave the folder count unchanged. Avoid “đang cày” based on cached stats alone.
