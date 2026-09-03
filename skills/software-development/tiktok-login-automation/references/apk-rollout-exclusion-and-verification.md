## Farm APK rollout: exclusion and verification

## Full-farm scope and parity audit

Use `taikhoan_run_safe.xlsx` (`May` + `Device ID`) as the complete scope, not only the current ADB snapshot. Confirm the expected machine range and preserve exactly one status row per mapped machine. For “đủ app như Máy 1”, compare only the agreed required set—Gmail `com.google.android.gm`, Outlook `com.microsoft.office.outlook`, Chrome `com.android.chrome`, WhatsApp `com.whatsapp`, TikTok `com.ss.android.ugc.trill`, and ViChanger `vn.vichanger.app`—because carrier/Samsung/Facebook/optional packages can legitimately differ from the reference device.

Windows/Git Bash verification pitfalls: strip CRLF from serials before ADB calls; redirect `adb` stdin from `/dev/null` inside mapping loops so it cannot consume the mapping file; avoid fragile `xargs` positional-variable assumptions. The final gate is a row-count-preserving status file with `OK`, `MISSING`, `OFFLINE`, or `WRONG_VERSION` for every mapped machine.

## Safety contract

`adb install -r -d` adds or updates the target package; it does not intentionally stop TikTok, ViChanger, scheduler, gateway, or proxy-watcher. It still uses USB/ADB bandwidth and Android Package Manager, so a large farm rollout can slow live work. Do not restart the gateway or proxy watcher as a workaround.

## Procedure

1. Confirm the APK path and package/version from a known-good source device.
2. Snapshot online serials with `adb devices`.
3. Query each serial with `adb -s <serial> shell pm path <package>`.
4. Split the inventory into `HAVE` and `MISS`; **never** blindly install on all devices when some are already done.
5. Install only the `MISS` list, with bounded concurrency (8 is a conservative starting point for a 100MB APK).
6. Record one `OK` or `FAIL` line per serial in a durable log.
7. Verify each success with `pm list packages` and `dumpsys package <package>` / `versionName`.

## Interruption recovery

If an installer launched by the agent is interrupted, first identify its own parent/child PIDs and stop only those installer processes. Verify no `adb install` process for that APK remains. Do not kill scheduler, gateway, proxy-watcher, or other farm workers merely because they also use ADB.

Then re-run the inventory step. Devices where `pm path <package>` now succeeds belong to `HAVE` and are excluded automatically; only the remaining `MISS` devices are eligible for retry.

## Path pitfall

The xiaowei ADB build may reject an MSYS path such as `/d/OneDrive/...` even though Git Bash can read it. Pass a Windows path such as `D:\OneDrive\...` to `adb push/install`.

## Evidence and reporting

Report online count, already-installed count, attempted count, OK/FAIL counts, package version, and log path. Do not claim completion from a launched background process; wait for its terminal status and verify package state afterward.
