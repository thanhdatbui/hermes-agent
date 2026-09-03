# APK Harvest — clone installed apps to a backup bank

Goal: pull the exact APK(s) currently installed on a farm phone so they can be
reinstalled (`adb install-multiple`) onto other / reimaged phones. The source is
the device's own installed app — a bit-exact, "clean" copy (NOT downloaded from
the web).

## Setup

- ADB: `C:\Program Files (x86)\xiaowei\tools\adb.exe`
- Bank root: `D:\Taadaa\apk-bank\` — one subfolder per package, name = `pkg` with
  `.` → `_` (e.g. `com_ss_android_ugc_trill`, `vn_vichanger_app`)

## Two ADB pitfalls (both SILENT — cost ~30 min the first time)

1. **Directory pull to an EXISTING dest writes nothing.** `adb pull <dir> <existing_dir>`
   prints `N files pulled` but the folder stays empty. Fix: pull to a fresh path
   (`rmdir` the empty dir first, or use a new name). Single-file pull to an
   existing dir is fine.
2. **adb.exe is native Windows — pass Windows paths, not MSYS `/d/...`.**
   `/d/Taadaa/...` silently no-ops. Use `D:\Taadaa\...` (backslashes). Verify with
   `cmd /c "dir D:\Taadaa\apk-bank\..."` (MSYS `ls` and `cmd` both see `D:`, but
   only the Windows form works for adb).

## Harvest one app (split-aware)

```bash
ADB="/c/Program Files (x86)/xiaowei/tools/adb.exe"
S=9885b64957334f5a46            # source serial (machine 1)
BANK="/d/Taadaa/apk-bank"
BANKWIN="D:\\Taadaa\\apk-bank"  # adb needs the Windows form
pkg=com.ss.android.ugc.trill    # TikTok; use vn.vichanger.app for ViChanger
dir=$(echo "$pkg" | tr '.' '_')

# 1) resolve the app install dir from pm path (strip package: and /base.apk)
appdir=$("$ADB" -s $S shell pm path "$pkg" 2>/dev/null | sed 's/^package://; s/\r$//; s:/base\.apk$::' | head -1)

# 2) dest MUST NOT pre-exist (rmdir empty leftovers)
rmdir "$BANK/$dir" 2>/dev/null

# 3) pull whole app dir to a FRESH Windows-path dest
"$ADB" -s $S pull "$appdir" "$BANKWIN\\$dir"

# 4) verify (both MSYS and cmd see D:)
find "$BANK/$dir" -type f | wc -l
cmd /c "dir /s D:\\Taadaa\\apk-bank\\$dir"
```

## Reinstall onto another phone

- Split app (TikTok, 325 files): `adb install-multiple D:\Taadaa\apk-bank\com_ss_android_ugc_trill\*`
- Single APK (ViChanger): `adb install D:\Taadaa\apk-bank\vn_vichanger_app\base.apk`
- WhatsApp / Gmail (split): `adb install-multiple D:\Taadaa\apk-bank\com_whatsapp\*`
  and `...\com_google_android_gm\*`

## Farm package map (verified 2026-08-13, ~30 connected SM-G930* devices)

| App | Package | Notes |
|-----|---------|-------|
| TikTok | `com.ss.android.ugc.trill` | v46.3.3 on sampled machines; split APK (base + lib/oat + ~50 split_*.apk) |
| ViChanger (VPN proxy) | `vn.vichanger.app` | v25.01.01; single base.apk; cert hash `cfe10fa4` uniform across farm |
| WhatsApp | `com.whatsapp` | v2.26.30.97; split APK (base + split_config.arm64_v8a / xxhdpi / i18n_vi) |
| Gmail | `com.google.android.gm` | v2026.07.27.95…; split APK. **GOTCHA:** `com.google.android.gms` is Google Play Services, NOT Gmail — do not pull it. |
| AdbKeyboard | `com.github.uiautomator/.AdbKeyboard` | input IME |
| uiautomator agent | `com.github.uiautomator` | atx-agent device side |
| GemPhone | — | NOT a phone app on the connected farm (no `gem`/`farm` package on any device; scanning all devices only matched `com.android.storagemanager` as a false positive). Likely the Windows PC control software, not adb-pullable. Ask the user for the package name or plug in a machine that has it. |

## Verify app provenance (is the APK clean / fake / sideloaded?)

Before trusting a harvested app (e.g. "is ViChanger a fake proxy app?"), check on
a live device:

```bash
ADB="/c/Program Files (x86)/xiaowei/tools/adb.exe"; S=<serial>; pkg=vn.vichanger.app
# source of install — absent/empty => sideloaded via adb install (farm image), not Play Store
"$ADB" -s $S shell dumpsys package "$pkg" | grep -i installerPackageName
# cert signature hash — uniform across farm => one controlled APK, not rogue/mixed
"$ADB" -s $S shell dumpsys package "$pkg" | grep -oE "signatures=PackageSignatures\{[0-9a-f]+ \[[0-9a-f]+\]\}"
# version
"$ADB" -s $S shell dumpsys package "$pkg" | grep -oE "versionName=[0-9.]+"
```

- `installerPackageName=` absent/empty → app was `adb install`-ed (part of the
  farm image), not from Play Store. Expected for a controlled sideload.
- Compare the **cert hash** (the `[xxxx]` token) across many devices. If identical
  everywhere → a single controlled APK pushed farm-wide (not rogue/mixed).
  ViChanger = `cfe10fa4` uniform on all sampled machines.
- Functional proof of legitimacy (separate from supply-chain trust): the app
  creates a real `tun0` VPN interface (`VPN CONNECTED` + `GET_IP` returns the proxy
  IP) — a placebo/fake app cannot bring up a real tunnel. See
  `references/vichanger-vpn.md`.
- Residual supply-chain risk if sideloaded from an unknown source: a VPN app sees
  all device traffic. Mitigate by only installing the exact APK (matching cert
  hash) from the trusted GemPhoneFarm bundle, and comparing the cert against the
  vendor's original APK when available.

## Pitfall: bash `for` + `while read` + `tr` path mangling (SILENT — no files written)

When harvesting many apps in a loop, this pattern **reports success but writes
nothing**:

```bash
for pkg in com.whatsapp com.google.android.gm; do
  dir=$(echo "$pkg" | tr '.' '_')
  "$ADB" ... pm path "$pkg" | sed ... | while read -r p; do
    f=$(basename "$p")
    "$ADB" -s $S pull "$p" "D:\\Taadaa\\apk-bank\\${dir}_${f}"   # path gets mangled; file never lands
  done
done
```

Symptom: adb prints `1 file pulled` per file, but the destination folder stays
empty — and even the root bank dir has no trace. Root cause: variable/path
expansion inside the nested `while read` subshell + MSYS path conversion of the
`$BANKWIN`/`$dir`/`$f` concatenation silently produces a destination path adb
no-ops on. **Single direct pulls work fine** — only this loop shape fails.

**Reliable workaround (what actually worked):** pull each file with an explicit,
direct `adb pull` command (no loop, no `while read`, no `tr`), to the root bank
dir with a clear name, then `mv` (local filesystem op — always reliable) into the
per-app subfolder:

```bash
"$ADB" -s $S pull "/data/app/com.whatsapp-XXXX==/base.apk"                     "D:\\Taadaa\\apk-bank\\whatsapp_base.apk"
"$ADB" -s $S pull "/data/app/com.whatsapp-XXXX==/split_config.arm64_v8a.apk"   "D:\\Taadaa\\apk-bank\\whatsapp_split_config.arm64_v8a.apk"
# ... one line per file (source dir from `pm path`); then:
mv /d/Taadaa/apk-bank/whatsapp_*.apk /d/Taadaa/apk-bank/com_whatsapp/
mv /d/Taadaa/apk-bank/gmail_*.apk   /d/Taadaa/apk-bank/com_google_android_gm/
```

The source app dir (`/data/app/<pkg>-<hash>==`) is per-install and changes between
pulls — capture it fresh from `pm path` each run rather than hardcoding the hash.
(Above `XXXX` is illustrative; substitute the real hash from `pm path`.)

## Notes

- Apps are identical across the farm (same cert hash, same version), so harvesting
  from one machine is sufficient.
- `pm list packages -3` on feed/proxy machines shows only: uiautomator, ar.core,
  vichanger, tiktok, easyMover, xwkeyboard — no other 3rd-party app.
- ViChanger trust: it creates a real `tun0` VPN interface (proven by
  `VPN CONNECTED` + GET_IP returning the proxy IP) — NOT a fake/placebo app.
  See `references/vichanger-vpn.md`.
