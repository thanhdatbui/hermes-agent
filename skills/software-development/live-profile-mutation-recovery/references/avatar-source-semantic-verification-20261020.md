# Avatar Source Semantic Verification (2026-10-20)

## Incident pattern

A live TikTok avatar runner can report a successful forced replacement and update the workbook while the selected source image is semantically wrong. In the observed run, the runner correctly resolved `D:\TIKTOK-videonuoinick\117\avatar.jpg`, pushed it, selected the newest picker tile, saved the crop, and recorded `FORCED_REPLACED_VERIFIED`. The source file itself was an outdoor beige canopy/fabric image, not the proposed cat avatar. A later profile screenshot showed the same non-cat image in the avatar circle.

Separately, the profile bio mutation did succeed: the fresh profile/edit-profile evidence showed the requested Vietnamese bio. This demonstrates that mutation success must be judged per field, not as one all-or-nothing profile result.

## Durable rules

1. **Validate the target asset before touching the device.** Open the exact source file resolved by the runner, inspect it with vision/OCR as appropriate, and record the semantic result (for example, `cat`, `canopy`, `placeholder`, or `unknown`). Do not trust a proposal canvas label, filename, folder number, or earlier description.
2. **Do not equate transport success with semantic correctness.** `exit=0`, `verified=True`, `AVATAR_SMOKE_SUCCESS`, `FORCED_REPLACED_VERIFIED`, a successful push, a crop-save screen, or `Avatar = OK` proves at most that the runner completed its mechanical flow. It does not prove that the intended visual asset was selected.
3. **Verify both sides of the mapping.** Before upload, bind `target account -> source folder -> exact avatar path`; after upload, bind `target account -> fresh Profile screenshot -> avatar content`. The source and post-action image must be semantically compatible. If they differ, report `BLOCKED`/`UNPROVEN` and do not overwrite workbook state as final.
4. **Treat the picker selection index as a transport detail, not identity proof.** “Newest tile after push” only proves recency in the picker. It does not prove that the file is the intended asset. Keep the source-image semantic check independent of picker logs.
5. **Verify each profile field independently.** A fresh screenshot can prove the bio while leaving the avatar wrong. Report `Bio: confirmed` and `Avatar: unproven/incorrect` separately, with exact evidence paths and timestamps.
6. **When correcting a false success, state the precise correction.** Say which claim was unsupported, what the fresh artifact actually showed, and what remains to be done. Do not silently revise the prior report or invent a new avatar identity.

## Minimal evidence matrix

| Stage | Required evidence | Acceptable conclusion |
|---|---|---|
| Source preflight | Exact resolved avatar file opened and semantically inspected | Source is the requested asset / source is wrong / source is unknown |
| Runner | Target-scoped log and artifact report | Mechanical flow completed or failed |
| Post-action | Fresh exact-account Profile screenshot inspected visually | Avatar content confirmed, mismatched, or unproven |
| Workbook | Row update read back after visual proof | Tracking state may be finalized only after semantic proof |

Do not describe an avatar as “cat”, “white cat”, or any other class unless the exact source and/or fresh profile screenshot was actually inspected and supports that claim.
