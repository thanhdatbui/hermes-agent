# Cross-host Admin upload: controller vs storage owner

## Trigger
Use when a Kibe controller reports `video_not_rendered`, `missing_video_folder`, or “Hết video/Cần cào” for Admin machines 201–280.

## Provenance and invariant
The Admin render store is owned by `admin-farm` (`192.168.110.119`), not by the Kibe controller:

- Kibe machines 1–80: local `D:\TIKTOK-videonuoinick`.
- Admin machines 201–280: remote `D:\TIKTOK-videonuoinick-admin` on `admin-farm`.
- A `Path.is_file()` or `stat()` executed by the Kibe controller against the Admin path is not a valid storage check.

## Evidence-first reproduction
1. Read the exact per-machine `upload_result.json`; distinguish a local preflight false negative from an actual workflow failure.
2. Run a read-only preflight on the owning host, bound to one representative machine/serial and exact video number. The validated Admin shape is:

```text
ssh admin-farm "powershell -Command \"cd D:/Taadaa/Tiktok-video; & 'D:/Taadaa/python-envs/automation/Scripts/python.exe' -m scripts.tiktok_workflow --config config-admin.yaml --workflow-workbook D:/OneDrive/TaadaaData/admin/Tik1.xlsx --single-device <SERIAL> --video-number <N> --video-source-root D:/TIKTOK-videonuoinick-admin --preflight\""
```

Expected evidence includes `[HOST] host=admin`, the Admin source path, `OK next video`, and `PREFLIGHT PASSED`. Do not treat a Telegram label or controller-local missing path as proof that rendering is empty.

## Correct implementation contract
Patch only the upload-hook seam:

- Admin (`machine >= 200`): skip controller-local file existence checks and dispatch the workflow through `ssh admin-farm`.
- Remote runtime: `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
- Remote repo/cwd: `D:/Taadaa/Tiktok-video`.
- Remote config: `config-admin.yaml`.
- Remote workbook: the resolved Admin `Tik<slot>.xlsx` for the upload row.
- Bind exact `account.serial`, `next_video`, and source root `D:/TIKTOK-videonuoinick-admin`.
- Include `--allow-device-reboot-recovery` and `--no-dry-run`; do not pass Kibe `ADB_SERVER_SOCKET`.
- Kibe (`machine < 200`) retains the existing local check and subprocess branch.
- Keep report/ledger validation fail-closed; `returncode == 0` alone is never success. Existing workflow markers and, where available, `report.json` must still verify device/account/video/post state.

Do not use SMB, drive mapping, or video copying as a workaround. The host owning the storage resolves the path and performs the upload.

## Worker and verification contract
For a production fix, use a bounded worker task with a unique Gate-5 anchor and a <=30-line operational delta where feasible. Preserve unrelated dirty hunks and line endings. Require:

```text
python -m py_compile D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py
PYTHONPATH=. pytest python_runner/tests/test_upload_hook.py -q -p no:cacheprovider
```

If a focused test fails, classify the failure before retrying; do not overwrite unrelated dirty work. Independently inspect `git diff --numstat` and command construction before canary.

## Canary acceptance
After offline verification, run one official Admin canary (M201 is the established representative). Accept only evidence with exact device/video binding and workflow report fields such as `status=SUCCESS`, `post_verified=true`, and `post_submission_state=ACCEPTED`. A clean exit code without report/artifact evidence is insufficient. A teardown screenshot showing only Launcher proves device liveness, not publication; inspect the runner's captured `post-published-surface.png` or profile verification artifact instead.

## Historical pitfall
A successful remote canary is not production remediation until the patch is actually present on the branch used by the cron/controller. Check the working-tree diff and deployed/active revision before attributing the next cron run to the fix.
