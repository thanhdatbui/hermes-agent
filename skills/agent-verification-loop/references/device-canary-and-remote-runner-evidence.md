# Device Canary and Remote Runner Verification Evidence

## 1. Phone Sleep / Dozing State is NOT a Blocker for Device Canary
- **Anti-Pattern (Paralysis / Luna Behavior):** The agent reads device status via ADB inspection, sees `Display Power: state=OFF` or `mWakefulness=Dozing/Asleep`, and refuses to run canary: *"The phone is asleep so canary cannot be safely run"*.
- **Authoritative Rule:** Android phone farms intentionally keep screens turned off during idle to conserve battery and thermal life. Canonical test runners and workflows (e.g. `tiktok_workflow`) automatically execute standard wakeup sequences (`ANDROID_STARTUP` -> `wake_screen` / `wake_unlock_verify_wake`).
- **Safe Pre-check Wakeup:** If the coordinator needs to ensure the device is awake before launching a canary or inspection, run:
  `adb -s <serial> shell input keyevent KEYCODE_WAKEUP` or `adb -s <serial> shell svc power wakeup`
  This is a safe OS-level power broadcast, NOT an ad-hoc screen interaction. It must never be used as an excuse to avoid running canary.

## 2. Remote Host Execution: Never Rely on Stale Post-Teardown Local State
- **Anti-Pattern (Blind Verification):** Running a remote canary workflow on a separate host (e.g. via `ssh admin-farm`) and then only capturing a local screen snapshot after the runner has already executed its teardown (which brings the phone back to the launcher Home), reporting "Canary passed but no UI proof".
- **Authoritative Rule:** Remote runners produce authoritative artifacts in the remote runtime directory (e.g. `D:\CodexRuntime\tiktok-video\runs\run_<device>_<timestamp>\`):
  1. `execution.log`: Proves the exact execution trace and state machine transitions (e.g. `VERIFY_POST`, tile counts, success markers).
  2. `report.json`: Holds machine-readable structured results (`post_verified: true`, `status: SUCCESS`).
  3. Pre-teardown screenshots: Captured by the runner directly before closing the target app (e.g. `post-published-surface.png`, `profile-grid-verify_post-*.png`).
- **Evidence Obligation:** The coordinator MUST use `scp` to retrieve these authoritative artifacts from the remote host to the local environment and surface both the structured log timeline and native `MEDIA:` images to the user.

## 3. Data-Source Locality in Distributed Coordinator Setups
- When a central coordinator (e.g. Kibe) commands workflows on a satellite execution host (e.g. Admin), disk path existence checks (`Path.is_file()`, `stat()`, `glob()`) must never be executed on the coordinator's local filesystem against paths that reside strictly on the remote host's disks (e.g. `D:\TIKTOK-videonuoinick-admin`).
- Checking local files for remote hosts results in false `video_not_rendered` / missing asset alerts. Local checks must be gated by machine locality (`is_remote_admin`), delegating remote validation to the remote SSH execution step.
