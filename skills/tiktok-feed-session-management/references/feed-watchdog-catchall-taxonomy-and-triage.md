# Feed Watchdog "Lỗi App TikTok/Script" Catch-all Taxonomy & Triage

## Overview & The Catch-all Illusion

In `feed_session_watchdog.py`, the classification function `classify_feed_failure(reason)` groups machine failures into:
1. `Mất kết nối ADB/USB` (device offline, transport error, unauthorized)
2. `Mất kết nối Wi-Fi (AP)` (wifi not connected, no-carrier, wlan0 down)
3. `Chưa gán Proxy / Proxy :0`
4. `Nghẽn đường truyền Proxy / 4G`
5. `Lỗi cấu hình Proxy`
6. `Lỗi App TikTok/Script` (FALLTHROUGH DEFAULT CATCH-ALL)

Because #6 is the default return statement for **any reason not matching ADB, Wi-Fi, or Proxy**, any failure occurring during profile navigation, feed swiping, popup handling, or account switching is labelled as `Lỗi App TikTok/Script` on Telegram. This frequently misleads users into believing the runner script itself crashed or contains a bug.

---

## Field Breakdown from Telemetry (`run_manifest.json`)

When triaging `Lỗi App TikTok/Script`, inspect `multi_machine_summary` inside the run manifest:
`D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>/<subrun>/run_manifest.json`

The failures in this catch-all category consistently decompose into 4 distinct field groups:

### Group 1: UI Popups & Overlays (~40% of occurrences)
* **Markers & Reasons in Manifest:**
  - `unexpected popup/dialog marker detected; swipe recovery (2 swipes) still stuck`
  - `Add phone popup remained after allowed close X attempt`
  - `fullscreen Shop ad swipe recapture is not a valid feed: manual-needed:popup`
  - `sponsored/ad feedback overlay requires manual review`
  - `startup ad/splash marker detected; swipe recovery (2 swipes) still stuck`
* **Root Cause:** TikTok pushes dialogs (TikTok Shop coupons, phone binding prompts, ad surveys) that cover the video surface. Fail-closed safety terminates the session with `manual-needed` to avoid unintended clicks.
* **Remediation:** Enhance `benign_popup.py` or `feed_swipe_smoke.py` with dismiss bounds / close selectors for the newly observed popup marker.

### Group 2: TikTok Launch Timeout / Focus Lost (~30% of occurrences)
* **Markers & Reasons in Manifest:**
  - `prepare-tiktok failed to focus TikTok after launch`
  - `TikTok focus lost after navigation tap: unknown`
  - `TikTok focus lost`
  - `focused package unavailable`
* **Root Cause:** Hardware resource exhaustion on Samsung Galaxy S7 (3GB RAM). Under continuous multi-machine batch operations, the Android Low Memory Killer (LMK) drops TikTok, or app launch takes longer than the 15-second focus timeout.
* **Remediation:** Inspect RAM/process state with `python D:/Taadaa/tools/inspect_machine.py <N>`; consider elevating preflight memory cleanup or restarting the app package before launch.

### Group 3: ATX-Agent Hang / UI XML Unavailable (~15% of occurrences)
* **Markers & Reasons in Manifest:**
  - `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset`
* **Root Cause:** The `atx-agent` daemon listening on port 7912 on the device hung, was killed by Android, or failed to dump the UI hierarchy.
* **Remediation:** Verify port 7912 health and ensure ATX-Agent auto-restart fallback triggers before falling back to uiautomator.

### Group 4: Account Switcher & Profile UI Stagnation (~15% of occurrences)
* **Markers & Reasons in Manifest:**
  - `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`
  - `profile username still mismatched after switch`
  - `navigation target profile not found in XML`
* **Root Cause:** Drawer animation failed to open the bottom sheet switcher within timeout, or Profile tab failed to load network metadata.
* **Remediation:** Check switcher bounds and verify network/proxy latency on the device.

---

## Triage Protocol for Coordinator

1. **Do Not Blame Python Code Immediately:** When Telegram reports high `Lỗi App TikTok/Script`, check whether failures are cluster-wide (script crash) or scattered across machines with diverse `manual-needed` reasons.
2. **Zero-Scan Rule (Invariant):** NEVER run broad disk scans (`os.walk`, `glob(recursive=True)`, `find`). Read the specific `run_manifest.json` under the active session live directory directly.
3. **Inspect Representative Devices:** Use `python D:/Taadaa/tools/inspect_machine.py <N>` for 1-2 machines from each distinct failure sub-group.
4. **Transparent Communication:** Explain to the user the breakdown (Popup vs Focus vs ATX vs Switcher) rather than accepting an ambiguous "script is broken" premise.
