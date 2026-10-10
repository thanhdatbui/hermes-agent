# Avatar normalization candidate gate

Use this checklist for a single TikTok profile where niche/hashtag metadata and avatar are being normalized together.

## Evidence classes

1. **Identity binding:** username, machine, Tik slot, workbook row, Folder Video, and source/state DB rows agree.
2. **Content check:** inspect representative render-folder videos, not only `video goc`; confirm the actual recurring subject/niche before choosing an avatar.
3. **Metadata write:** update only the bound workbook row, state DB mirror(s), and tracker queue row. Preserve posted-video count and unrelated columns.
4. **Candidate QA:** exact upload file is square and visually inspected. Reject clipped eyes/head/chin, UI overlays/view counts, props/hands covering the face, severe blur/vignette, synthetic mirrored/padded borders, and wrong subject.
5. **Queue/device split:** after source preparation, keep `avatar_replace_queue.status='PENDING'` until a real runner report and fresh Profile screenshot prove replacement. `PENDING` is not device success.

## Safe fallback

If all candidate frames fail QA, restore the previous canonical avatar from a timestamped backup, leave the queue pending, and report `BLOCKED/UNPROVEN` for the avatar only. It is valid to finish metadata normalization independently, but do not claim the profile avatar was changed.

## Reproducibility record

Record source file, crop coordinates, output dimensions, and MD5/SHA-256. For a screenshot-derived candidate, record the screenshot path and exact pixel box. For a video-derived candidate, record render-folder video filename and timestamp. Never silently substitute a crop from another folder or from the raw-video numbering space.
