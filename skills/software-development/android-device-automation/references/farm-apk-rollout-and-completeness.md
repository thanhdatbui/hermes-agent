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

## Preflight APK Bank Version Inspection (Zero-Dependency)
Before spending 20–30 minutes transferring large bundles, verify the exact version in `apk-bank`. On hosts where `aapt` or `pyaxmlparser` is missing from PATH, parse the binary `AndroidManifest.xml` string pool and header directly via Python `struct` from `base.apk`:
```python
import zipfile, struct
with zipfile.ZipFile(apk_path) as z:
    data = z.read("AndroidManifest.xml")
# Chunk 0x0001 (String Pool) -> extract string table
# Chunk 0x0102 (RES_XML_START_ELEMENT_TYPE) -> manifest attributes (versionCode, versionName)
```
Always confirm whether the bank version matches the requested version (e.g. 46.4.3 vs 46.7.3) before deploying.

## USB Hub Bandwidth Bottleneck & Install Timeout Guard (2026-09-07)
On high-density phone farms (~80 devices connected via USB hubs), per-device ADB bandwidth can drop to **0.1 MB/s (~100 KB/s)** under concurrent load:
- **Heavy Apps (TikTok ~200MB split bundle)**: Transferring `base.apk` (140MB) + `split_config.arm64_v8a.apk` (57MB) + language splits over `install-multiple` takes **25 to 35 minutes**.
- **Standard ADB Timeouts Will Fail**: Subprocess / CLI timeouts set to standard 180s or 600s will prematurely terminate the transfer with `timed out after 600s`.
- **Safe Execution Rules**:
  1. For direct `adb install-multiple -r`, allocate a timeout of **at least 2000s–2400s (35–40 minutes)** or run as a background task.
  2. Do NOT interrupt an in-flight transfer with `pm clear` or hard reboot — this can corrupt Package Manager staging or reset app credentials.
  3. Where possible, run bulk updates during farm idle windows or stage splits to `/data/local/tmp` sequentially.

## Canonical installer tool: `install_farm_apks.py`
Use `D:/Taadaa/tools/install_farm_apks.py` (synced at `D:/Taadaa/AI-Tools/tools/install_farm_apks.py`) for automated installation of Outlook, ViChanger, and TikTok across the farm:
- **APK Bank Root**: `D:\OneDrive\apk-bank`
  - Outlook: `com_microsoft_office_outlook\com.microsoft.office.outlook_4.2325.1-32325818_minAPI26(armeabi-v7a)(nodpi)_apkmirror.com.apk`
  - ViChanger: `vn_vichanger_app\base.apk`
  - TikTok: `com_ss_android_ugc_trill` (50 split APKs installed via `install-multiple -r`)
- **ADB Auto-Discovery**: Prioritizes `C:\Program Files (x86)\xiaowei\tools\adb.exe` if present, with system PATH fallback.
- **Preflight Package Check**: Runs `pm path <package>` for each requested app; automatically marks and skips already-installed packages (`[SKIP_INSTALLED]`) to save USB bandwidth and Package Manager locks, unless `--force` is provided.
- **CLI Options**:
  - `--device <serial>`: Install for a specific device serial.
  - `--stt <N>`: Resolve machine number `N` from `taikhoan_run_safe.xlsx` (`kibe` or `admin` inventory).
  - `--all`: Concurrently install across all connected devices using `ThreadPoolExecutor` (`max_workers=6..8`).
  - `--apps <trill,outlook,vichanger>`: Install only specified apps (default: all 3).
  - `--force`: Force reinstall (`-r`) even if app exists.
- **Reporting**: Clear per-device and per-app tags (`[OK]`, `[SKIP_INSTALLED]`, `[FAIL]`) with a structured summary table.

## Evidence from the August 2026 rollout
The first 70-device pass reported 68/70; one device needed a retry after `ECONNRESET`, and one disconnected. A later full audit initially produced false `OFFLINE` results because mapping serials retained CRLF and ADB consumed the loop's stdin. After stripping `\r`, redirecting stdin, and requiring 80 status rows, the correct result was 79/80, then the missing machine was installed and the final result was 80/80.
