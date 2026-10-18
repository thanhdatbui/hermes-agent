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
  - `startup ad/splash marker detected`
  - `screen capture invalid; feed not confirmed`
  - `feed swipe command failed`
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
4. **Phiên 1 vs Phiên 2 Intra-shift Comparison:** Each shift (Ca) consists of 2 sessions (Phiên 1 & Phiên 2). Many Group 2 (focus lost / prepare timeout) and Group 1 (transient popup) errors in Phiên 1 self-recover automatically in Phiên 2 as Samsung S7 memory pressure settles. Always compare Phiên 1 vs Phiên 2 manifests before diagnosing a permanent fault.
5. **ADB Socket Transport Timeout vs Hardware Offline & Rapid Triage:**
   - Distinguish between actual USB/hardware disconnection (`device '...' not found`), hardware offline (`error: device offline`), and ADB daemon socket timeout (`adb command timed out: ... 'settings', 'get', 'global', 'http_proxy'`).
   - CẤM kill ADB server toàn cục thủ công vì sẽ làm sập các batch 2FA/nuôi acc khác đang chạy.
   - **Triage O(1) với `benny_farm_triage.py --machine <N> --json`:** Nếu `dumpsys_window_snippet` chứa `timed out after 5.0 seconds`, shell thiết bị đang bị kẹt do nghẽn I/O bus USB trong phiên chạy đồng thời.
   - **Cứu hộ phân tầng với `recover_stuck_s7.py --machine <N>`:** Lệnh Level 3 Reconnect (`adb [-H ...] -s <serial> reconnect`) giải phóng socket bị kẹt trong ~2s mà không cần reboot thiết bị hay reset PC.
   - **Rolling Healer cứu hộ hàng loạt giữa các phiên:** Dùng `python D:/Taadaa/tools/batch_recover_s7.py --cluster <kibe|admin> --machines <list> --max-workers 8` để giải phóng đồng loạt các máy lỗi trước phiên kế tiếp.
   - Đối với các thiết bị kẹt hardware transport ở trạng thái `offline` liên tục (như sau sụt áp micro-USB), duy trì fail-closed và chờ mốc auto-reboot định kỳ (`05:20, 11:20, 17:20`) để reset phần cứng controller EHCI qua BIOS.
6. **Transparent Communication:** Explain to the user the breakdown (Popup vs Focus vs ATX vs Switcher vs ADB Timeout) rather than accepting an ambiguous "script is broken" premise.

## Validated Example: Do Not Equate the Telegram Bucket With App Crashes

In the 2026-10-17 Ca 3 / Row 4 run, the Kibe Telegram report labelled 16 machines as `Lỗi App TikTok/Script`. Direct inspection of the active `run_manifest.json` showed that M33–38, M71–72, M75, M77–78, and M80 were actually `manual-needed:network-offline: Wi-Fi has no internet connection`; M68 was a TikTok-focus-after-launch failure; M74 was a swipe-command failure; M76 was a profile/account mismatch; and M48 was only degraded. The Admin bucket likewise mixed screen-capture invalid, swipe-command, focus/package, navigation, login, and profile-verification failures rather than proving crashes.

**Operational rule:** report the catch-all count as `app/script/UI-control bucket` until manifest reasons prove `app_crash`. State the evidence-backed subcounts, and if taxonomy is too coarse, recommend splitting at least into `network_offline`, `adb_offline`, `proxy`, `screen_capture`, `ui_focus`, `swipe_command`, `profile_mismatch`, `navigation/login`, `popup`, and `app_crash`.

## Specific Token Omissions in `classify_feed_failure` (2026-10-18 Incident)

In `D:/Taadaa/tiktok-luot nuoi acc/scripts/watchdog/formatters.py`, the function `classify_feed_failure(reason)` suffered from missing keyword tokens that caused batch Wi-Fi failures to collapse into `Lỗi App TikTok/Script`:
- **Wi-Fi False App Crash**: `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)` was not caught because the Wi-Fi matcher lacked `network-offline`, `no internet connection`, and `wifi_combo`.
- **Egress Network Unreachable**: Proxy errors like `dial tcp ... connect: network is unreachable` lacked `network is unreachable` and collapsed into App error.
- **Granular UI Sub-Buckets**:
  - `failed to focus tiktok`, `prepare-tiktok failed to focus`, `focused package unavailable` -> `Lỗi mở/focus App TikTok`
  - `swipe command failed` -> `Lỗi thao tác vuốt (Swipe)`
  - `screen capture invalid`, `feed not confirmed` -> `Lỗi chụp màn hình Feed`
  - `profile account mismatch`, `navigation target profile not found` -> `Lệch Profile/Nick TikTok`
  - `login/account screen detected` -> `Văng màn hình Đăng nhập`
  - `unknown tiktok state` -> `Trạng thái TikTok lạ/chưa hỗ trợ`
Ensuring these tokens exist in `classify_feed_failure` prevents artificial "app crash waves" on Telegram.
