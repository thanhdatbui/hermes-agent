# Admin Remote-Media Canary Evidence & Cross-Host Upload (2026-10-06)

## 1. Remote Admin Media Check
- **Context:** Controller runs on Kibe; Admin machines (201–280) use media located at `D:\TIKTOK-videonuoinick-admin` on the `admin-farm` host (192.168.110.119).
- **Anti-pattern:** Do not validate file existence on Kibe's local filesystem or rely on network shares/SMB.
- **Rule:** For Admin machines (`machine >= 200`), skip local `Path.is_file()` checks on Kibe and invoke the upload workflow remotely over SSH using the Admin runtime, config, workbook, and media root:
  ```bash
  ssh admin-farm "powershell -Command \"cd D:/Taadaa/Tiktok-video; & 'D:/Taadaa/python-envs/automation/Scripts/python.exe' -m scripts.tiktok_workflow --config D:/Taadaa/Tiktok-video/config-admin.yaml --workflow-workbook D:/OneDrive/TaadaaData/admin/Tik<slot>.xlsx --single-device <serial> --video-number <N> --video-source-root D:/TIKTOK-videonuoinick-admin --allow-device-reboot-recovery --no-dry-run\""
  ```

## 2. Canary Wake Discipline
- **Anti-pattern:** Do not treat an idle device in `Sleep/Dozing` state as a reason to block or refuse a canary run.
- **Rule:** Differentiate between forbidden ad-hoc UI tapping and valid automated device wake. Use the runner's standard wake sequence (`svc power wakeup` / `KEYCODE_WAKEUP`), confirm `Display Power: state=ON`, and proceed with the canary run.

## 3. Post-Canary Verification Artifacts
- **Anti-pattern:** Do not use a post-teardown Launcher screenshot as proof that a video was or was not uploaded.
- **Rule:** Inspect the remote run directory (`D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\`):
  - Read `execution.log` for `State: VERIFY_POST` and `Workflow completed successfully`.
  - Read `report.json` for `"status": "SUCCESS"`, `"post_verified": true`, and `"post_submission_state": "ACCEPTED"`.
  - Fetch pre-teardown screenshots (`post-published-surface.png`, `profile-grid-verify_post-*.png`) to provide visual evidence.
  - Reconcile the workbook tracking (`Tik<slot>.xlsx` and `taikhoan_run_safe.xlsx`) to reflect the updated posted count.

## 4. Dual-Namespace Mock Seam
- If production code supports alternate import paths (e.g. `python_runner.flows.upload_preflight` vs `flows.upload_preflight`), resolve the function dynamically through `sys.modules` in the production caller to ensure unit test patches target the active module instance.
