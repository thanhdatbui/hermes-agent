# Approved avatar: immediate upload and evidence

## Rule
An operator-approved avatar is an execution request, not a request to stage metadata. Copying `avatar.jpg`, adding `.manual_avatar_locked`, setting `PENDING`, or editing Excel/DB only prepares the source and queue. The canonical avatar-only launcher must upload to the exact device; `OK` is allowed only after device-side verification.

## Runbook

1. Resolve the authoritative Tik workbook/manifest mapping for the exact account, machine, Tik number, and folder. Do not infer machine identity from a folder alone.
2. Run the O(1) machine inspection first. If offline, record the inspect output as `BLOCKED/OFFLINE`; never claim completion and never use manual ADB taps as a workaround.
3. Run the canonical launcher with the exact `--tik` and `--machine` (and approved host config/lock handling), e.g. `python D:/Taadaa/tools/run_upload_avatar.py --tik <N> --machine <M> --wait-lock` when lock waiting is appropriate.
4. Validate more than exit code: require `verified=True`, the device-side upload confirmation, and the run report/checkpoint. A workbook write or `exit=0` alone is not proof.
5. Inspect the generated confirmation screenshot with vision before attaching it. Confirm the intended TikTok Profile/Edit screen, the new avatar is visible, and no black screen, popup, clipping, or stale image is present.
6. Reconcile Excel/DB to `OK` only after steps 3–5. `PENDING` means queued/staged, never uploaded.
7. Process targets independently. Report online verified targets as DONE and leave offline/unverified targets explicitly BLOCKED; do not call a mixed batch complete.

## Evidence checklist

- Exact target mapping and machine inspection output.
- Launcher output showing target and `verified=True`.
- Run report/checkpoint path.
- Vision-checked confirmation screenshot.
- Final workbook/DB status only as postcondition.

## Failure modes to avoid

- Treating a source image plus a lock marker as a device upload.
- Treating Excel/DB `PENDING` or `OK` as device evidence.
- Treating `exit=0` without a confirmation artifact as success.
- Claiming all targets are complete when some devices are offline.
