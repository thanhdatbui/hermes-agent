# Avatar-change correction loop (2026-10-20)

## Trigger
Use when the operator rejects the current avatar, says “đổi ava khác”, or a prior avatar proof shows the wrong semantic image.

## Incident lesson
A canonical filename such as `avatar.jpg`, a successful ADB push, `verified=True`, or an upload log line does not prove that the image depicts the intended niche. In this incident the source file was a roof/awning image even though the channel niche was cats; the profile proof exposed the mismatch.

## Procedure
1. Treat “đổi ava khác” as an execution request. Do not stall with a menu of options unless there is an unresolved business choice.
2. Choose one candidate from a known source artifact or verified representative frame. Keep the candidate path and target account bound together.
3. Open the exact candidate with vision before copying or uploading. Confirm subject, crop, face/mascot visibility, and absence of UI, black borders, unrelated people, water, bowls, or scenery. Never infer content from filenames, proposal captions, or worker summaries.
4. If a device/feed lock is actively owned, do not kill, remove, or bypass it. Finish the offline candidate preparation and report `BLOCKED: active device owner`; do not claim the device was updated.
5. After upload, capture a fresh screenshot of the exact target Profile. It must show the exact handle and the rendered avatar. Inspect that screenshot with vision; picker, crop, save, runner exit code, and workbook state are intermediate evidence only.
6. If the rendered avatar differs from the candidate, mark the avatar step failed/blocked and state the mismatch plainly. Do not send the misleading screenshot as success evidence.

## Reporting
Use four short fields:
- `Kết quả`: what is actually complete.
- `Bằng chứng`: exact candidate/profile artifact and what vision saw.
- `Blocker`: lock, missing proof, or semantic mismatch.
- `Bước tiếp theo`: one concrete action.

## Anti-patterns
- Do not reuse a stale `avatar.jpg` because its name looks canonical.
- Do not ask the user to choose among candidates when the niche makes the choice obvious.
- Do not copy a candidate into production roots before its semantic vision gate passes.
- Do not report “xong” from local file copies or `exit=0` without exact-account Profile proof.
