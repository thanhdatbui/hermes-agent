# Farm APK rollout and completeness audit

## Scope
Use `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` as the complete machine-to-serial scope. Do not equate the current `adb devices` count with the farm total. Build one mapping row per machine, confirm the expected range (for this farm, 1–80), and verify every mapped serial.

## Safe rollout
1. Inventory `pm path <package>` per explicit serial.
2. Exclude devices that already have the package; never run an unconditional all-device reinstall after a partial pass.
3. Use the native ADB path and Windows-style APK path. Bound transfers (for example, 8 concurrent workers) and log one result per serial.
4. Installing an unrelated APK with `pm install -r -d` does not force-stop TikTok/ViChanger, reboot, clear data, or restart schedulers, but it consumes ADB bandwidth and Package Manager time. Do not restart gateway, proxy watcher, schedulers, or touch live locks.
5. If interrupted, stop only the rollout's own process tree, re-inventory, and retry only missing targets.

## Full verification
The status artifact must have exactly one row per mapped machine with one of `OK`, `MISSING`, `OFFLINE`, or `WRONG_VERSION`; compare the expected version, not just package presence. On Git Bash/Windows, strip CRLF from serials before ADB calls and redirect ADB stdin from `/dev/null` inside mapping loops so ADB cannot consume the mapping file. Avoid fragile `xargs` positional-variable assumptions.

## Required-app parity
Compare an explicit required set against the reference machine rather than the entire third-party/system package list. Current core set: Gmail `com.google.android.gm`, Outlook `com.microsoft.office.outlook`, Chrome `com.android.chrome`, WhatsApp `com.whatsapp`, TikTok `com.ss.android.ugc.trill`, and ViChanger `vn.vichanger.app`. Carrier, Samsung, Facebook, and optional packages may legitimately differ.

## Evidence from the August 2026 rollout
The first 70-device pass reported 68/70; one device needed a retry after `ECONNRESET`, and one disconnected. A later full audit initially produced false `OFFLINE` results because mapping serials retained CRLF and ADB consumed the loop's stdin. After stripping `\r`, redirecting stdin, and requiring 80 status rows, the correct result was 79/80, then the missing machine was installed and the final result was 80/80.
