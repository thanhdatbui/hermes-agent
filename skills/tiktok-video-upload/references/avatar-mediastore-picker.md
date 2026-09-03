# Avatar MediaStore / Photo Picker Triage

Use this reference for avatar-only canaries, especially Samsung/Android 8 devices such as machine 4. It records a layer-by-layer verification model; do not collapse a picker symptom into a source-image diagnosis.

## The six independent gates

Verify in this order:

1. **Source image** — the folder source exists and is a valid image. Record size, MD5, format, dimensions, and `PIL.Image.verify()` (or equivalent).
2. **Remote file** — the pushed path exists on the phone and its MD5 matches the source. A successful `adb push` log alone is not evidence.
3. **MediaStore row** — query both the image collection and the broader file collection. On the affected Samsung build, an orphan row was visible through `content://media/external/file` even when the image-specific query did not show it.
4. **Picker tile** — the gallery can show a thumbnail for a row whose backing file is gone. `Ảnh không tồn tại` means stale/orphan row until proven otherwise; it does not mean the new source is corrupt.
5. **Selection** — an indexed tile is not selected. After the tap, require the tile's selected marker/number and `Tiếp (1)` (or equivalent), not merely a visible thumbnail and a plain `Tiếp` button.
6. **Crop/save/profile** — only after selection is confirmed may the flow advance to crop/save. A worker report and, where practical, the live profile image are the completion evidence.

## Machine-4 evidence pattern (2026-08-15)

- Source `D:\video goc\26\avatar.jpg`: JPEG, RGB, 512x512, 51,904 bytes, MD5 `a7060db96d737f423d08dc4f88437e18`.
- New remote file `/sdcard/Pictures/av_26_1786756849.jpg` had the same MD5 and remained on-device.
- A previous row `/storage/emulated/0/Pictures/av_26_1786750911.jpg` remained in MediaStore with `_id=3634`, but the backing file no longer existed. Tapping its duplicate-looking tile produced `Ảnh không tồn tại`.
- The current row was `_id=3635`. Deleting the orphan by numeric ID through `content://media/external/file` left the valid current row and file intact.
- The failed canary's screenshot still showed a hollow selection circle and plain `Tiếp`; therefore the failure was not just “save selector missing”—the tile had never been selected. The run stopped with `AVATAR_SAVE_SELECTOR_MISSING` after `AVATAR_SELECTION_FAILED`-adjacent UI evidence.

## Safe cleanup / verification recipe

Before pushing a new unique avatar:

1. Delete old avatar files in every previously used directory.
2. Purge MediaStore rows matching the avatar prefix from **both** relevant provider views where supported (`external/images/media` and `external/file`).
3. Query `external/file`, filter rows by the avatar filename prefix, and delete orphan rows by `_id` when wildcard deletion on the image URI did not remove them.
4. Push a fresh unique filename, touch it if the device preserves the source mtime, and rescan.
5. Query `external/file` again; assert exactly the intended current file has a backing file and valid image MIME/media type.
6. Open the picker and verify the UI state after the tap. If it remains a hollow circle + plain `Tiếp`, stop and capture evidence—do not call crop/save or claim success.

When using `adb shell content query --where`, quote string values correctly. Numeric `_id` deletion is safer for a known orphan; an unquoted path in `--where` causes a SQL syntax error rather than filtering the intended row.

## Reporting language

Use precise layer names:

- “source valid” ≠ “remote file valid”
- “remote file valid” ≠ “MediaStore indexed”
- “gallery tile visible” ≠ “tile selected”
- “tile selected” ≠ “avatar saved”
- “worker exited 0/1” ≠ “profile avatar verified”

If an earlier run was reported successful but the latest live run fails, prefer the latest report and live evidence; historical success is not proof for the current MediaStore state.
