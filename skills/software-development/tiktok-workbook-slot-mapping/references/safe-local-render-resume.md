# Safe local render resume — session-derived detail

## Proven mapping pattern

For `D:\OneDrive\Tiktok\tik3.xlsx`, sheet `TaiKhoan`, the live header was:

`Máy | device ID | ID | Folder Video | video gốc | Keyword Video | Hashtag Pool | ...`

The relevant anchor rows were:

- machine 41: output 323 -> source 201
- machine 42: output 331 -> source 202
- machine 43: output 339 -> source 203
- machine 44: output 347 -> source 204
- machine 45: output 355 -> source 205

With the verified eight-folder block rule, this yields:

- 323–330 -> source 201
- 331–338 -> source 202
- 339–346 -> source 203
- 347–354 -> source 204
- 355–362 -> source 205

Do not derive this by filtering only a split worker's rows: a worker covering 341–362 must still load the earlier anchors 323/331/339.

## Safe execution shape

Use the preferred launcher when its machine-range behavior matches the requested scope. If the launcher cannot express an output allowlist without touching protected folders, use a small audited wrapper that invokes the existing `scripts/random_batch_render.py` per output folder.

Required renderer flags:

```text
--randomize --slot 2 --machine-id <machine-1> --seed-offset 0
--parallel 1 --resume-verify-existing
```

Never pass `--overwrite` for a folder containing valid MP4s. A protected-complete folder must be skipped before the renderer is invoked, even if its count is below the nominal target, when the user explicitly declared it protected.

## Audit artifacts

Write to `D:\CodexRuntime\tiktok-video\batch-runs\<run-id>`:

- `launcher.log`: workbook/header/mapping snapshot, SKIP/RUN/DONE/ERROR lines
- `source-<N>.txt`: exact UTF-8 source file list used for each source batch
- `output-<N>.stdout.log` and `output-<N>.stderr.log`: renderer output
- optional JSON/CSV summary containing pre-count, post-count, valid-count, and new-valid-count

After the run, use `ffprobe -v error -show_entries format=duration` and require a numeric duration greater than zero for validity. Report every requested folder individually; do not infer completion from process exit code alone.

## Failure and recovery notes

- A custom wrapper can fail before rendering due to its own path/type bug; fix the wrapper, preserve existing valid outputs, and restart with the same allowlist.
- Sequential rendering of 30 folders can be very slow. Disjoint output ranges may run concurrently, but each process must retain `--parallel 1` and must load the full anchor mapping.
- Stop conflicting broad-range Tik3 renderers before starting a scoped run; otherwise they can write to folders outside the user's allowlist or protected folders.
- A timeout while the runner remains alive is not completion. Poll the process and inspect output counts, renderer logs, and ffprobe validity before declaring `done`.
