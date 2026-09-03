# Batch avatar regeneration — workbook mapping + parallel workers (2026-08-15)

Context: regenerating `avatar.jpg` for all remaining TikTok folders (275 in
`D:\video goc` + 60 only in `D:\TIKTOK-videonuoinick`), after the 55-machine
avatar sweep. Two hard-won lessons: (1) machine→folder mapping MUST come from
the workbook `video gốc` column, not `Folder Video`; (2) sequential generation
is slow (~15-25s/folder) so split across 4 background workers.

## Mapping: workbook `video gốc` is the source of truth

`Tik2.xlsx` columns: `Máy | device ID | ID | Folder Video | video gốc | ...`
- For machines 40-74, `Folder Video` = RENDER ID (314/322/330...586) which does
  NOT exist under `D:\video goc` (verified `D:\video goc\314` missing).
- The real source folder is `video gốc` (120..154), which exists and holds the
  mp4 pool.
- The folder logged in `execution.log` ("Avatar source resolved: avatar.jpg for
  folder N") is ALSO unreliable — a machine's most recent run may be a Tik1 run,
  off-by-one from the Tik2 mapping.

Read mapping with openpyxl `data_only=True`, filter machines, run
`scripts/_make_avatar.py <video_gốc>` per machine → 55/55 OK in one pass.

## Both-roots rule (machines 40-74)

`avatar.jpg` must exist in BOTH:
- `D:\TIKTOK-videonuoinick\<Folder Video>\` (video source — has the dirs)
- `D:\video goc\<Folder Video>\` (what `resolve_avatar_path` reads via
  `avatar_source_root` in config)

A file only in the video root is invisible to the workflow → `AVATAR_SOURCE_MISSING`.
Copy/generate into both, verify both `stat` sizes > 0 BEFORE launching a batch.
Run-directory timing matters: a batch launched while copies are still in flight
fails `AVATAR_SOURCE_MISSING` for machines whose folder wasn't done yet.

## Parallel worker pattern (4x speedup)

```python
# build folder list once
parts = [folders[i::4] for i in range(4)]
```

Launch `python avatar_worker.py <i>` ×4 as background processes (worker script
writes its own log under `D:/CodexRuntime/tiktok-video/avatar-worker-logs/`;
`subprocess.run` timeout 300s/folder; `ok = rc==0 and "AVATAR OK" in stdout`),
then `process(action=wait)` on all four.

Bash gotcha: `bash: no job control in this shell` appears in the output preview
but does NOT break the run. Poll with `process(action=wait)` until
`status: exited`; read per-worker logs for the `DONE ... FAILED:` summary
instead of the interleaved preview.

## Red flags after regeneration

- Suspiciously tiny avatars (4-8 KB, e.g. folders 104/126/136) = blank/flat
  frame won — `vision_analyze` before uploading.
- Exclude machine 38 (user rule) from any manifest.

## Old avatar-generation scripts

`_make_avatar.py`, `_make_avatar_bright.py`, `make_avatar_yolo.py` = frame-derive
scripts (person/animal detect + naive first-frame fallback). They can produce
bad avatars (screenshot-with-text, back-of-head frames). The download pipeline
now uses `make_avatar_for_folder()` (3-tier: channel → person/animal frame →
bright frame), which is the user-requested integration: "tạo ava có hình người,
k có người thì ưu tiên động vật".
