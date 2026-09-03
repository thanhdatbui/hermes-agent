# Tik3 render resume — reference detail

## Exact prior command (verified 2026-08-11, resumed 2026-08-13)
```
cd /d/Taadaa/Tiktok-video && powershell.exe -NoProfile -ExecutionPolicy Bypass -File run_tik3_random_render.ps1 -StartMachine 1 -EndMachine 80 -Parallel 1 -AutoRun [-ResumeVerifyExisting]
```
- `-Parallel 1` was chosen after user said CPU was at 92% (single worker, slower but safe).
- `-ResumeVerifyExisting` added on resume to ffprobe-verify and skip valid existing outputs.

## Launcher behavior
- `run_tik3_random_render.ps1` reads `D:\OneDrive\Tiktok\tik3.xlsx` sheet `TaiKhoan`,
  columns by INDEX: `[0]=machine`, `[3]=output folder`, `[4]=source folder`.
  Builds a per-source file-list, then calls `scripts/random_batch_render.py`.
- `scripts/random_batch_render.py` SKIPS outputs that already exist; with
  `-ResumeVerifyExisting` it additionally ffprobe-confirms validity before skipping.
- Resume log lines (safe):
  `skipped: 3.mp4 -> 3.mp4 (output da ton tai)`
  `skipped: 29.mp4 -> 29.mp4 (output da duoc ffprobe xac nhan)`

## Wrong entrypoint that FAILED (do not use)
```
python scripts/tik3_multi_batch.py --start-output 323 --start-source 258 --count 40 ...
```
-> `ERROR: Workbook thieu cot bat buoc: sttvideo`
Cause: `tik3_multi_batch.py` requires a `sttvideo` column; the Tik3 workbook uses
machine/output/source columns instead. The launcher `run_tik3_random_render.ps1` is the
canonical entrypoint — use it, not this module.

## Resume scope 2026-08-13
- Already complete (skip): folders 329,330,337,338,345,346,353,354,361,362 (43-45 valid MP4).
- Empty/incomplete (render): 323-328, 331-336, 339-344, 347-352, 355-360.
- Source root `D:\video goc`; output root `D:\TIKTOK-videonuoinick`.
- LOCAL render only — never upload/login/network from the render launcher.
