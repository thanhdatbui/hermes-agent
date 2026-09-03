# Outlook 4.2325.1 farm rollout — 2026-08-13/14

Goal: get a Hotmail-login-capable mail app on the Android-8 farm S7s, since the
Gmail app's basic-auth path is dead (Microsoft disabled basic auth 2022).

## Build selection (user-confirmed)

- APKMirror variant page: **Microsoft Outlook `4.2325.1` (arm-v7a) (nodpi) (Android 8.0+)**, uploaded July 7, 2023.
- Why 4.23xx: farm S7 = Android 8.0.0; current 5.26xx need Android 10+.
- File: `com.microsoft.office.outlook_4.2325.1-32325818_minAPI26(armeabi-v7a)(nodpi)_apkmirror.com.apk` (103,815,815 bytes; md5 `d5b3178bad456359456670f5eaa2da67`).
- User downloads manually on their own PC Chrome (farm host IP is Cloudflare-blocked for APKMirror/APKPure; APKCombo only keeps 3 newest = Android 10+). APK dropped into `D:\OneDrive\apk-bank\com_microsoft_office_outlook\`.

## Install recipe (verified Success on 4 machines)

```bash
ADB="/c/Program Files (x86)/xiaowei/tools/adb.exe"
F="D:\\OneDrive\\apk-bank\\com_microsoft_office_outlook\\com.microsoft.office.outlook_4.2325.1-32325818_minAPI26(armeabi-v7a)(nodpi)_apkmirror.com.apk"
"$ADB" -s <serial> push "$F" /data/local/tmp/outlook.apk
"$ADB" -s <serial> shell pm install -r -d /data/local/tmp/outlook.apk   # -> Success
"$ADB" -s <serial> shell pm list packages | grep office.outlook
"$ADB" -s <serial> shell dumpsys package com.microsoft.office.outlook | grep -E "versionName|firstInstallTime"
"$ADB" -s <serial> shell rm -f /data/local/tmp/outlook.apk
```

- adb needs Windows `D:\...` dest path — MSYS `/d/...` fails (`cannot stat ... No such file or directory`).
- Prefer a machine whose `mResumedActivity` is the launcher (rảnh), not mid-batch.
- Sanity: `unzip -l <apk>` (zip container; a few-KB file = ad page) + `md5sum`.

## Machines done

| Panel | Serial | First install |
|---|---|---|
| máy 1 | 9885b64957334f5a46 | 2026-08-13 21:54 |
| máy 2 | 9885e6303951513337 | 2026-08-13 21:55 |
| máy 6 | 9885e64c484c544d32 | 2026-08-14 09:50 |
| máy 38 | ce06160685310f1c04 | 2026-08-14 10:01 (Android 8.0.0, launcher, 2 unreg hotmail) |

## Unregistered-hotmail discovery (user-corrected twice)

- First pass read `taikhoan_dat_v2` `NGÀY TẠO` empty as "chưa reg" → WRONG (user: "máy 6 làm lol có hotmail chưa reg tiktok"). Empty NGÀY TẠO ≠ unregistered; ID column non-empty = registered.
- Correct method: cross-file diff — emails in `gmail_clean_v2.xlsx` (inventory) absent from `taikhoan_dat_v2_updated .xlsx` (GMAIL col). Found 44 unregistered, 5 hotmail → máy 38 (aug***, flo***), 54 (eul***), 57 (Der***), 66 (Dau***).
- Serial mapping: `taikhoan_run_safe.xlsx` sheet Accounts only covers máy 1-2; all others from `taikhoan_dat_v2` `device ID` col.
- **Never call machines by serial suffix** — "máy 337" was meaningless (user: "Đéo có máy nào là máy 337 cả"); `9885e6303951513337` = máy 2. Always resolve panel number first.

## Pending

- Test Outlook login on máy 38 with one of the unreg hotmail accounts (email/pass live in gmail_clean_v2 — never printed).
- If OK: write UI-tap login script (same pattern as TikTok flows) + rollout to máy 54/57/66.
