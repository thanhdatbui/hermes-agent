# Session reference: live profile mutation and ATX recovery

## Validated observations

- `python D:/Taadaa/tools/inspect_machine.py 34` mapped Machine 34 to serial `ce031603b3158b0b02`; the app focus initially reported `com.ss.android.ugc.trill/...SplashActivity`.
- A pin dry-run succeeded only after the tool constructed `AdbClient(adb_path=ADB_BIN, serial=serial)` and used `capture_atx_session_ui`; it identified a 1,114-view tile. This was discovery evidence, not live mutation proof.
- Direct device-local `/data/local/tmp/atx-agent curl ... /dumpUI` returned 404. The automation-core persistent ATX session API returned a healthy `VERIFIED_XML` capture, so the session API is the primary route.
- The live pin attempt failed closed with `AccountSwitcherError: UI_DUMP_INVALID: adapter returned non-XML UI state` during `open_profile_root`.
- A fresh screenshot captured after the failure was inspected with vision and WinRT OCR. It showed TikTok feed content from a different public profile/surface rather than the intended `@lethanh14375`; no successful pin could be claimed.

## Evidence-first reproduction

1. Run the canonical machine inspection.
2. Acquire the device lock before capture or mutation.
3. Capture the current screen before recovery/teardown.
4. Inspect with WinRT OCR and vision.
5. Refuse mutation when identity or surface is wrong/unknown.
6. Use one bounded ATX session rediscovery/reset recovery in code, then re-verify the exact account.
7. After the live action, perform ATX read-back plus a fresh screenshot/vision inspection.

## What this reference does not claim

This session did not validate a successful live pin recovery. It documents the evidence requirements and the verified ATX capture distinction only; do not treat the failed worker attempt as a recommended fix.
