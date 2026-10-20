# TikTok Galaxy S7 Profile Edit Entrypoint Invariant (2026-10-20)

## Problem & Root Cause

During rolling TikTok profile mutations (nickname / bio updates) on Samsung Galaxy S7 (1080x1920, Android 7/8):
- Multiple devices (M32, M18, M15, M7, M36) repeatedly aborted with `exit_2`: `ABORT: ket o trang thai PROFILE 5 lan lien tiep`.
- Trace inspection and visual inspection (`browser_vision`) of real captures (`m32_hoang96379_s05.png`, `m11_hatien15118_s09.png`, `m8_haisa_s05.png`) revealed:
  1. The Profile screen in newer TikTok versions on S7 **does not display a text button** `Sửa hồ sơ` / `Edit profile` in the body (OCR only finds username, stats, and `+ Thêm tiểu sử`).
  2. The actual entrypoint to enter `EDIT_PROFILE` is an **icon of a pencil located at the top-left toolbar header**: `(X ≈ 72, Y ≈ 148)`.
  3. The runner had `XY_EDIT_PENCIL` erroneously assigned to `(870, 558)` (empty space on the right edge). When text OCR failed, it repeatedly tapped `(870, 558)`, producing no UI state transition, looping in `PROFILE` until hitting `MAX_SAME_STATE = 4` and aborting.

## Canonical Rule & Coordinates

On Samsung Galaxy S7 (1080x1920) TikTok Profile screens:
- Header Pencil Icon: `XY_EDIT_PENCIL = (72, 148)` (x: 50–90, y: 130–170).
- Fallback logic: If OCR does not find a bounding box matching `r"(sua|chinh sua|edit)\s*(h[o0]|profile)"`, the fallback MUST tap `XY_EDIT_PENCIL = (72, 148)` instead of aborting or tapping arbitrary right-side coordinates.
- Validated proof: Scripts using `(72, 148)` (`do_rename_m8.py`, `do_rename_m44.py`, `do_rename_m46.py`) consistently transition from `s05 (PROFILE)` to `s06 (EDIT_PROFILE)` in exactly 1 tap.
