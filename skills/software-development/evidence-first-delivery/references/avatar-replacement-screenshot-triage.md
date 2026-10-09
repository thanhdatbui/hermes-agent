# Avatar replacement triage from a single profile screenshot

This reference records a reusable, evidence-backed path for a request such as “đổi ava acc này” when the operator supplies a profile screenshot but not the machine/slot.

## Validated sequence

1. **Identify the account O(1), before mutating anything.** Extract the visible handle from the screenshot using OCR/vision, then query the tracker DB for `avatar_replace_queue` and `farm_account_info`. Resolve `may`, `tik`, `folder_video`, `video_goc`, and `host_id`. Cross-check the matching `Tik<N>.xlsx` row for `Keyword Video`/niche and device serial.
2. **Inspect the current source avatar, do not trust its filename or `Avatar=OK`.** Hash the existing files and inspect the actual image. In the observed case the render avatar was a text-heavy banner while the source avatar was a different image; the DB/workbook status alone did not reveal this.
3. **Choose a source frame from the account’s own source folder.** For a music niche, inspect several short source videos and timestamps, prefer a clean solo close/medium-close portrait, and reject subtitles, TV logos, social UI borders, black frames, and unrelated characters. Do not copy another account’s avatar.
4. **Crop and re-inspect the candidate.** Remove source-frame borders before the square crop; resize to 512×512 and inspect the final file, not only the uncropped frame. The first crop in the observed run still had white vertical borders and was correctly rejected; the second crop passed visual checks.
5. **Synchronize only the correct mapped paths.** Copy the accepted candidate to the source path for `video_goc` and the render/mirror path for `folder_video` according to the workbook mapping. Re-hash both files and confirm they match the new candidate and differ from the old hashes.
6. **Reset the queue only after source validation.** Set the target row to `status='PENDING'`, clear `last_error`, update its timestamp, and read the row back. `PENDING` means “awaiting device execution”; it is not upload success.
7. **Respect a live device lock.** Run the approved O(1) machine inspection and inspect the machine/serial lock. If the target machine is actively reserved by another workflow, do not force-run, kill, or launch a competing AvatarOnly runner. Leave the queue `PENDING` and report `SKIPPED_LOCKED` with the lock owner/PID and the exact reason. Resume only after the lock is released through the normal owner workflow.
8. **Separate four states in the report:** source files synchronized; queue state; device runner/report state; visual Profile verification. Never collapse them into “đã đổi” or infer success from a launcher banner, exit code, or queue update.

## Evidence rules

- A final upload claim requires the canonical per-target report plus a fresh Profile screenshot visibly showing the target handle and the new avatar. The screenshot must be inspected before native media delivery.
- If the operation stops at source/queue preparation because the machine is locked, report the precise blocker and do not fabricate a device result. The validated run that motivated this reference reached only source sync + `PENDING`; it did **not** validate a successful upload.
- Keep old/new hashes and the queue read-back in the run notes so a later operator can distinguish a real replacement from a path-only update.

## Reusable commands/patterns

- Machine field evidence: `python D:/Taadaa/tools/inspect_machine.py <N>`.
- Lock evidence: read `~/.codex/device-locks/machine_<N>.lock.json` and the matching serial lock; verify the recorded PID is alive before treating the lock as active.
- Tracker lookup: query the exact username in `avatar_replace_queue` and `farm_account_info`; avoid broad disk scans.

## Pitfalls captured

- A workbook row marked `Avatar=OK` can still point to a visually unsuitable or stale source image.
- A crop can pass “one face/no subtitles” but still contain visible white borders; inspect the post-crop artifact.
- Launching a runner while the machine is locked is not a safe form of queuing; queue-only is the correct fail-closed behavior.
- A generic launcher banner such as “LIVE ĐĂNG VIDEO” is not proof that AvatarOnly ran or that the target account was changed.
