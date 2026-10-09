# Farm App Provisioning Watchdog Architecture & Operational Patterns

## 1. Multi-Cluster Topology
- **Local Cluster (Kibe M1-M80)**: Default ADB daemon (`localhost:5037`).
- **Remote Cluster (Admin M201-M280)**: `adb -H 192.168.110.119 -P 5037`.
- When querying or executing ADB commands across clusters, always parameterize the host/port via base command:
  `adb [-H <host> -P <port>] -s <serial> <subcommand>`

## 2. Flexible Provisioning Matrix & Full Split APK Invariant
Do not verify packages superficially with only `pm list packages`. A package can exist while missing critical dynamic feature modules (Play Feature Delivery), which causes the Google Play Store (`com.android.vending`) PlayCore dialog (*"TikTok cần tải các tệp bổ sung xuống để thêm tính năng vào ứng dụng..."*) to pop up continuously during feeds.

### TikTok (`com.ss.android.ugc.trill` / `com.zhiliaoapp.musically`):
- **Split Count Verification**: Query `pm path com.ss.android.ugc.trill` and count installed split APKs.
  - A device with `< 50 split APKs` is DEFICIENT and missing dynamic features (`split_df_*`).
  - A healthy, fully-provisioned install contains **55 - 65 split APKs**.
- **Installation Command**:
  MUST install ALL split APKs from the source bank folder (base.apk + config splits + all 50+ dynamic feature `split_df_*.apk`), NEVER just 5 hardcoded base splits:
  ```bash
  adb -s <serial> install-multiple -r -d base.apk split_config.*.apk split_df_*.apk
  ```
  - Bank path: `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\v47.0.3` (65 APK files)
  - Data safety: `install-multiple -r -d` preserves 100% of user data, cookies, and login sessions. **NEVER run `pm clear`**.

### Supporting Apps:
- **Microsoft Outlook**: `com.microsoft.office.outlook`
  - `adb install -r -d <apk>`
  - Bank path: `D:\OneDrive\apk-bank\com_microsoft_office_outlook\...apk`
- **Xiaowei Keyboard**: `com.android.xwkeyboard`
  - `adb install -r -d "C:\Program Files (x86)\xiaowei\tools\XWKeyboard.apk"`
- **ATX-Agent Stubs**: `com.github.uiautomator`
  - `adb install -r -t app-uiautomator.apk` and `app-uiautomator-test.apk`
  - Bank path: `C:\Users\Kibe\.GemPhoneFarm\app\`

## 3. Concurrency Safety, USB Bandwidth & Process Locks
1. **USB Bus Throttling (Max Concurrency = 5)**:
   - Transferring ~280MB of split APKs to phones across shared USB Hubs causes severe USB bus saturation if run with high concurrency (e.g. 20-25 workers).
   - High concurrency causes packet loss, socket deadlock, ADB timeouts, and forces devices into `offline` state.
   - Limit concurrent split-install jobs to **at most 5 devices simultaneously**.
2. **Lock Directories**:
   - Check: `Path.home() / ".codex" / "device-locks"`, `C:\Users\Kibe\.farm_locks`, `D:\Taadaa\locks`, `%TEMP%`.
   - Match both `*<serial>*.lock` and `*<serial>*.lock.json`.
3. **Lock Verification Pitfall (JSON Parsing)**:
   - For `.lock.json` files, **NEVER** use broad regex `\b(\d+)\b` to find PID. It will mistakenly match `"machine": 73` as PID 73, think the holder process is dead, and mutate a busy phone during an active shift.
   - Parse JSON properly: extract `data.get("pid")` or `data.get("holder_pid")`.
   - If PID is alive (`is_pid_alive(pid)`), **SKIP** the device immediately.

## 4. Post-Install Device Optimization & Screen Power Off
After provisioning missing packages, enforce standard display and power settings and turn off the screen immediately to save battery and prevent AMOLED burn-in:
```bash
adb -s <serial> shell settings put system screen_off_timeout 600000
adb -s <serial> shell settings put global stay_on_while_plugged_in 0
adb -s <serial> shell svc power stayon false
adb -s <serial> shell settings put system accelerometer_rotation 0
# Immediately sleep screen after provisioning
adb -s <serial> shell input keyevent 223
```

## 5. False Alarm Triage: Google Play PlayCore vs Account Lost
- Watchdog classification trap: When Google Play Store (`com.android.vending`) displays a download prompt for TikTok dynamic features, window dump reports `mCurrentFocus=...com.android.vending...`.
- Automated log analyzers may classify this as `Google/GMS/account screen focused` and trigger a false-positive P0 "Session Lost / Account Logged Out" alarm.
- Verification procedure: Check `dumpsys window` or screencap. If the dialog text contains *"TikTok cần tải các tệp bổ sung xuống..."* / *"Play Store"*, the TikTok account is 100% intact. The root cause is missing split APKs, resolved by provisioning the full 65 splits.

## 6. Silent Watchdog Rule & Cron Schedule
- **Schedule**: Run every 5 minutes (`*/5 * * * *`) to catch newly idle or replacement devices.
- **Silent Rule**: When all online devices have >= 50 split APKs and all required apps, exit cleanly with code `0` and empty stdout.
- Support `--dry-run` flag for fast inspection without writing to devices.
