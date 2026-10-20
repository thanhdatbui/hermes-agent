# Session reference: live profile mutation and ATX recovery

## Validated observations

- `python D:/Taadaa/tools/inspect_machine.py 34` mapped Machine 34 to serial `ce031603b3158b0b02`; the app focus initially reported `com.ss.android.ugc.trill/...SplashActivity`.
- Direct device-local `/data/local/tmp/atx-agent curl ... /dumpUI` returned 404 on atx-agent 0.10.1. The automation-core persistent ATX session API (`capture_atx_session_ui`) returned a healthy `VERIFIED_XML` capture, confirming the session API as the primary route.
- The initial live pin attempt failed with `AccountSwitcherError: UI_DUMP_INVALID: adapter returned non-XML UI state` during `open_profile_root` because `ProfileAdapter.dump_ui()` called `dump_profile_ui_atx` only once without settling retries while the app was transitioning from Splash/Feed to Profile root.
- A fresh screenshot captured after the initial failure showed TikTok on a different public profile/surface rather than `@lethanh14375`; mutation was stopped and preserved as failure evidence.

## Validated resolution & completion proof

1. **Adapter Settling Retry:**
   Updated `ProfileAdapter.dump_ui()` to retry up to 3 times with 1.0s sleep, accepting only non-empty strings starting with `<` or `<?xml`. This allows the UI tree to settle during activity transitions without failing closed prematurely:
   ```python
   def dump_ui(self):
       for _ in range(3):
           xml = dump_profile_ui_atx(self.s)
           if xml and xml.lstrip().startswith(("<", "<?xml")):
               return xml
           time.sleep(1.0)
       return ""
   ```
2. **Device Lock Preemption:**
   When previous attempts timed out or aborted, orphaned lock files blocked subsequent runs. In operator CLI tools (`pin_top_videos.py`), wrapping execution with `operator_device_lock(machine=args.machine, serial=serial, force_preempt=True, timeout=30.0)` safely claimed the lease via `TAKEOVER_SCOPE_OPERATOR_PREEMPT`.
3. **Execution & Read-Back Verification:**
   - Ran live pin on Machine 34: `status: PINNED`, `pinned_before: 0, pinned_after: 1`.
   - Verified target account `@lethanh14375` (Bảo Thịnh).
   - Captured post-action screenshot `D:/Taadaa/reports/m34_standardized_profile.png`.
   - Inspected via WinRT OCR and native browser_vision: confirmed the 1,142-view video tile ("Đi Fansipan lạnh 9 độ") gained the red/white "Đã ghim" badge at top-left with no popups or layout distortions.
4. **Communication Invariant:**
   Before launching long-running background tasks (>30s) such as worker dispatch or ADB execution, send an explicit status message stating the active action and background session ID so the user is never left wondering whether the agent is frozen.
