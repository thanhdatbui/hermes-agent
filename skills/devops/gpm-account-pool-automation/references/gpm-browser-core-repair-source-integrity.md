# GPMLogin Browser-Core Repair Source Integrity

Use this reference when `GET /api/v3/profiles/start/{id}` reports `Yêu cầu cập trình duyệt [Chromium] [N]` again after reboot or app restart.

## Durable diagnostic sequence

1. Inspect the exact core and the repair source separately; do not assume that a present `chrome.exe` means the repair source is healthy.
2. Test the updater archive with the shipped 7-Zip binary, not only by checking that the ZIP exists:

```powershell
& 'C:\Users\<user>\AppData\Local\Programs\GPMLogin\7za.exe' t `
  'C:\Users\<user>\AppData\Local\Programs\GPMLogin\gpm_browser\default\update.zip'
```

Acceptance is `Everything is Ok`. `Unexpected end of archive`, `Data Error`, or a physical size smaller than the archive's declared size means the repair source is truncated/corrupt.

3. Compare the archive's declared/physical size and record SHA-256 before changing anything. In one verified incident, the archive was 105,660,416 bytes while 7-Zip reported a 119,469,577-byte physical archive and a missing 13,809,161 bytes in `142.0.7444.163\chrome.dll`.
4. Compare `default` and `gpm_browser_chromium_core_<N>` by file size/hash for `chrome.dll`, `chrome.exe`, `chrome_elf.dll`, `chrome_proxy.exe`, `gpmdriver.exe`, `version`, and `data-variations.gpm`. A manually repaired live core can pass `/profiles/start` while the default repair source remains bad.
5. Treat post-reboot recurrence as an updater/resource-repair overwrite hypothesis until disproved. Preserve evidence from the archive and file mtimes; do not keep copying a single DLL as the final fix.
6. Check Application/.NET event logs around the archive's modification time for updater/restart failures. A `RestarterV2.exe` `Process.StartWithShellExecuteEx` failure near the same timestamp is evidence of an incomplete update/restart path, not proof of a profile or proxy problem.
7. Verify with a fresh API canary after the source is repaired: call one known active profile's `/api/v3/profiles/start/{id}`, require `success: true`, then close it. Re-test after the next planned GPM restart/reboot. Do not claim durability from a single successful start before the repair source is valid.

## Safe remediation boundary

- Back up `gpm_browser` before replacing any resource archive or core.
- Replace the whole verified Chromium package from an authoritative complete download/installer, or use GPM's official resource update path; do not invent a ZIP or patch only one binary.
- Do not delete profiles, alter `Profiles.JsonData`, convert profiles to 64-bit, or change proxies while diagnosing a browser-resource integrity failure.
- If the archive cannot be replaced and no authoritative package is available, report the live core as temporarily working but the system as not reboot-safe.

## Evidence interpretation

- `profiles/start` success proves the currently selected core can launch now; it does not prove the `default\update.zip` repair source is valid.
- A missing `data-variations.gpm`, invalid `version` (e.g. `1.0` instead of `1.1`), missing `chrome_elf.dll`, or an incomplete archive can all produce the same generic GPM message `Yêu cầu cập trình duyệt [Chromium] [N]`.
  * *Quick live-core fix*: If all binaries (`chrome.exe`, `chrome.dll`, `142.0.x`) are intact but GPMLogin still blocks start, check `data-variations.gpm` and `version`. Copy `data-variations.gpm` from `default/` and ensure `version` contains `1.1`. This instantly unblocks `/api/v3/profiles/start`.
- Record which prerequisite actually failed instead of treating the message as a unique cause.
- Keep user-facing reports concise: state the observed bad source, the current live-core result, and whether reboot durability is verified.
