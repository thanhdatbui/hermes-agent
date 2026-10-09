---
name: android-wifi-profile-cleanup
description: "Use when cleaning rogue Wi-Fi profiles on Android farms."
version: 1.0.0
author: Hermes Agent
tags: [android, wifi, farm, adb, cleanup, evidence]
---

# Android Wi-Fi Profile Cleanup

Use this class-level workflow when Android farm phones auto-connect to a non-farm SSID and must be returned to their fixed Aruba SSID. The goal is to remove only the confirmed rogue profile, preserve the farm profile, and leave a machine-level audit trail.

## Safety contract

- Never use a rogue SSID as a fallback or recovery network.
- **Saved Network Roam Trap**: Removing fallback logic from host Python scripts is NOT enough. If phones previously joined a rogue SSID, Android OS stores the profile in `WifiConfigStore.xml` (priority 100) and will auto-roam to it during radio toggles or AP load spikes. Cleanup MUST actively verify and re-bind all devices.
- Never remove a network by guessing an ID, by iterating through all IDs, or by trusting stale `dumpsys wifi` event history.
- Every device mutation runs under `D:/Taadaa/tools/with_device_lock.py --machine <N> -- ...` with the correct cluster/serial.
- Do not use `adb shell input tap`, `input keyevent`, or `input swipe` as a substitute for fixing network state.
- Do not read or expose Wi-Fi passwords in reports; use placeholders such as `<FARM_WIFI_PASSWORD>`.
- A device with no current rogue-SSID evidence is `NO_DAT_EVIDENCE` (or equivalent) and is not modified.

## Fixed target mapping

Resolve the machine number from the canonical workbook/mapping before changing anything:

- M01–M40 → `kibe 1`
- M41–M80 → `kibe 2`
- M201–M240 → `admin 1`
- M241–M280 → `admin 2`

Do not infer a target from the currently connected SSID. Do not move a phone between AP groups.

## Canary-first procedure

1. **Inspect one affected device.** Use the canonical O(1) inspection command where applicable, then obtain `dumpsys wifi` under the device lock.
2. **Require current-state proof.** Match the current `mWifiInfo` record for the rogue SSID and its current `Net ID`. A line in the historical `rec[...]` event list is not sufficient: the same ID may have been reused or the event may be stale.
3. **Remove exactly that ID.** On older Android builds where `cmd wifi` is unavailable, the validated low-level operation is:
   ```text
   adb shell service call wifi 14 i32 <CURRENT_ROGUE_NET_ID>
   ```
   Treat `Result: Parcel(... 00000001 ...)` as the service returning success, but still verify state afterward.
4. **Rejoin the fixed farm SSID.** Clean-kill any existing loop (`am force-stop com.steinwurf.adbjoinwifi && pkill -f steinwurf`). Use `adb-join-wifi` with explicit quotes around SSIDs with spaces (e.g. `am start ... -e ssid 'admin 1'` or `--es ssid "admin 1"`). Never send unquoted spaces (which truncates `admin 1` to `admin` in the Android shell) and never send the rogue SSID.
5. **Read back immediately.** Confirm `Supplicant state: COMPLETED`, the current SSID is the mapped farm SSID, and the address is in `192.168.110.x`. Read configured networks through Wi-Fi service output and confirm the rogue profile is absent where the platform exposes it.
6. **Only after canary verification, batch.** Run a background launcher with completion notification, one locked operation per machine, bounded concurrency (`max_workers=20` for 80–160 machines to finish in ~1–2 minutes, avoiding slow 30–60 min serial runs), and a separate JSON result per machine. Do not poll the background process with `ps`, `pgrep`, or sleep loops; wait for the completion event, then inspect the result artifacts.

## Batch result contract

Each machine result should include:

- machine number, cluster, serial
- `rogue_active_id` or an explicit no-evidence status
- removal transaction result
- mapped target SSID
- post-action current Wi-Fi summary
- `ip_ok` for `192.168.110.x`
- whether the rogue profile is still present in the configured-network readback
- lock/wrapper errors separately from device-operation errors

Use status values such as `NO_DAT_EVIDENCE`, `CLEAN_AND_ONLINE`, `CLEAN_BUT_VERIFY`, and `ERROR`. Do not report the batch as complete until the artifacts have been read and summarized.

## Failure handling

- If the current-state Net ID cannot be identified unambiguously, stop mutation for that device and mark it blocked with the raw evidence.
- If removal succeeds but the mapped farm SSID does not complete with a farm-subnet IP, preserve the evidence and mark `CLEAN_BUT_VERIFY`; do not try another SSID.
- If a device lock cannot be acquired, leave the device untouched and report the lock owner/timeout.
- If a batch is interrupted, distinguish completed per-device artifacts from unprocessed machines; never infer success from the launcher exit code alone.

## Reference

See `references/validated-rogue-ssid-canary.md` for the Android 8 binder transaction and read-back evidence pattern from the validated canary. This reference deliberately omits credentials and machine-specific secrets.
