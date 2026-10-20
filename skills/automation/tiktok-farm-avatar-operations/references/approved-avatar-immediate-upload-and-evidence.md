# Approved avatar: immediate upload and evidence

## Rule
An operator-approved avatar is an execution request, not a request to stage metadata. Copying `avatar.jpg`, adding `.manual_avatar_locked`, setting `PENDING`, or editing Excel/DB only prepares the source and queue. The canonical avatar-only launcher must upload to the exact device; `OK` is allowed only after device-side verification.

## Runbook

1. Resolve the authoritative Tik workbook/manifest mapping for the exact account, machine, Tik number, and folder. Do not infer machine identity from a folder alone.
2. Run the O(1) machine inspection first. If offline, record the inspect output as `BLOCKED/OFFLINE`; never claim completion and never use manual ADB taps as a workaround.
3. Run the canonical launcher with the exact `--tik` and `--machine` (and approved host config/lock handling):
   - For Kibe local machines (1–80): `python D:/Taadaa/tools/run_upload_avatar.py --tik <N> --machine <M> --wait-lock`.
   - For Admin remote machines (>= 200): Launcher must use `D:/Taadaa/machine-config/admin.yaml` (dynamic selection in `run_upload_avatar.py` when `machine >= 200`). Because Admin USB devices are physically attached to Admin-PC (`192.168.110.119`), Kibe local ADB will report `[DEVICE_OFFLINE] device not found`. The runner MUST be invoked directly on Admin-PC via `admin_ssh.py --powershell --timeout 1200` (`Set-Location D:\Taadaa\Tiktok-video; echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_tiktok_upload_avatar.ps1 -Tik <slot> -MaxParallel 1 -ForceAvatarMachineList <M> -HostConfigPath D:\Taadaa\machine-config\admin.yaml`). Before invoking, push `avatar.jpg` to `D:/TIKTOK-videonuoinick-admin/<folder>/avatar.jpg` in <=1200-char Base64 chunks (avoiding the Windows 8191 CLI buffer limit) and prefix remote PowerShell commands with `Set-Location` to pass the `admin_ssh.py` allowlist. Pull the confirmation screenshot back to Kibe in <=15KB chunks for vision inspection.
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
- Stopping at staging: NEVER stop after setting `PENDING` in Excel/DB and claim completion. When an avatar is approved, immediately invoke the upload runner on all online devices. Staging without immediate execution on online machines is a severe operational failure.
- Treating `exit=0` without a confirmation artifact as success.
- Claiming all targets are complete when some devices are offline.
- `[AVATAR_PICKER_NO_MATCH]` MediaStore indexing race: On Samsung devices (e.g., S7 Android 8), an `adb push` + media scan intent can take 3–5 seconds to asynchronously index into the MediaStore. If TikTok's picker opens before indexing completes, it displays "Không có ảnh hoặc video nào" and fails with `[AVATAR_PICKER_NO_MATCH]`. Do NOT assume broken UI or resort to manual taps; a prompt re-dispatch succeeds because the media scanner finishes indexing the pushed image in the background.
