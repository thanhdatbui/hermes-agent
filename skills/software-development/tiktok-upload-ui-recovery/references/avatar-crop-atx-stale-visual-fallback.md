# Avatar crop visual fallback — session detail

## Reproduction

The avatar-only flow resolved the correct workbook row and pushed the correct avatar, then reached TikTok's crop screen. The screen visibly showed the crop UI with the two red bottom actions (`Hủy` and `Lưu`), but the ATX/UI XML remained stale or incomplete. `_save_avatar_without_story()` waited for semantic crop nodes and eventually raised `AVATAR_CROP_OPEN_FAILED` even though the crop surface was already open.

## Durable fix pattern

1. Keep workbook-driven resolution authoritative: read the selected `TikN.xlsx` row by machine/device/account ID and resolve `Folder Video` from that row. Do not derive the folder from the screenshot or from a guessed slot.
2. Resolve the avatar through the normal resolver, including the generated-output fallback when the primary source root lacks `avatar.jpg`.
3. After the semantic/ATX crop checks and before raising `AVATAR_CROP_OPEN_FAILED`, capture one bounded screenshot.
4. Classify the crop surface visually using the existing save-surface classifier: both left and right bottom action regions must contain the red action buttons. This distinguishes crop (`Hủy` + `Lưu`) from picker (`Tiếp (1)` only on the right).
5. If the visual classifier passes, mark the crop surface confirmed and continue through the existing checkbox/story guard and save path. Do not tap based on an unverified generic coordinate.
6. Preserve the visual guard that rejects the Diary preview and preserves the no-Story policy unless explicitly enabled.

## Verification gate

- Run `py_compile` for the modified state-machine module.
- Run the focused avatar diagnostics tests.
- Run one explicitly authorized, single-machine avatar canary with the correct assignment manifest and device lock.
- Require the run report plus an independent post-action screenshot/profile check before calling it successful. A launcher exit code alone is insufficient.
- Release both machine and serial locks after the run; retain the lock on failure until the workflow is safely returned to Home or handed off for manual review.

This reference is intentionally session-specific; keep reusable behavior in `SKILL.md` and use this file for the reproduction/evidence pattern.