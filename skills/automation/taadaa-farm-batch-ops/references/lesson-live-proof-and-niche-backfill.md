# Live proof and strict niche backfill

## User workflow correction
When the user says “chạy cho tao”, the Coordinator must execute the canonical runner itself. Never hand the user a shell command as the next action. If policy blocks execution, report `BLOCKED` with the exact guard/error evidence.

## Live-process proof
A successful WMIC/SSH spawn or `ReturnValue=0` is not proof of a live job. After spawning on the target host, verify all three:
1. spawned PID still exists;
2. target worker (`ffmpeg.exe` or render Python) is alive on the target host;
3. the target log contains a timestamp/progress line newer than the spawn time.
Cache stats and old logs are not live evidence. `tasklist` on Kibe cannot prove Admin state.

## Strict same-niche backfill
For every source folder below 45:
- resolve the folder's niche/source-channel/keyword from `state.db` and the correct Tik workbook;
- prefer unclaimed `state.db` candidates with the exact same niche/source mapping;
- only then use a keyword-matched YouTube Shorts fallback with valid cookies/proxy;
- preserve existing media and append numbering;
- render only after the source reaches 45.

## Progress gate
A downloader round is productive only when `folders_repaired > 0` or the actual MP4 count increases. Repeated rounds with `folders_repaired=0`, unchanged incomplete-folder list, or proxy timeout are a blocker, not success. Report the exact evidence and stop claiming progress until the source/proxy/candidate path is fixed.

## Incident pattern
A `ValueError` from a fixed niche-pool cardinality check can make the loop appear alive while every child exits. Fix the validation to accept the configured pool, then run one focused test and restart the loop; verify new files, not merely a new round number.
