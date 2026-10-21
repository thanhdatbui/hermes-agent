# Account-bound avatar evidence and runner contradiction

## Trigger
Use when a TikTok avatar-only runner reports success/verified but the coordinator still needs to prove the exact account and final on-device avatar.

## Required acceptance chain

1. Bind the target before any live action with all three identifiers: machine/serial, workbook row/slot, and exact username (for this class of task, e.g. `@lethanh14375`).
2. Validate the upload candidate independently: exact source/render path, SHA-256, and visual inspection. A source path or workbook `Avatar = OK` is metadata evidence only.
3. Require upload telemetry showing the real replacement path, not only a save tap: push -> edit profile -> gallery selection -> crop -> save -> network settle.
4. Treat runner `exit=0`, `verified=True`, `FORCED_REPLACED_VERIFIED`, `Avatar upload thành công`, and workbook updates as intermediate evidence. They do not prove the final profile surface.
5. Re-open TikTok and capture a fresh screenshot from the *same target account*. The screenshot must visibly bind the username/display identity and show the new avatar; reject screenshots from another account, Launcher/Home, Splash, sleep/dozing, black/blank, or stale timestamps.
6. OCR/vision the exact screenshot before delivery. If the username is not the requested target, classify `ACCOUNT_MISMATCH` and do not claim success even if the runner report says verified.
7. Only then publish `VERIFIED_SUCCESS` and update the user. If the final screenshot cannot be obtained or is mismatched, report `UNPROVEN`/`FINAL_BLOCKED` with the exact evidence gap.

## Common contradiction pattern

A canonical run can correctly read the target workbook row and upload from the target folder, yet a later ad-hoc screenshot can land on another account or Launcher. Keep these claims separate:

- `UPLOAD_ACTION_CONFIRMED`: the canonical workflow performed the replacement on the bound device/account path.
- `PROFILE_VISUAL_VERIFIED`: a fresh screenshot proves the requested account and avatar.
- `TASK_DONE`: valid only when both are true.

Never turn the first claim into the third. A report field such as `post_verified: false` is an explicit blocker, even when another field says `avatar_status: FORCED_REPLACED_VERIFIED`.

## Reporting style

Lead with one direct status line: `DONE`, `UNPROVEN`, or `BLOCKED`. Then give at most three bullets: what is proven, what is not proven, and the next bounded action. Do not send a long progress narrative or ask repetitive confirmation after the user already selected the avatar.
