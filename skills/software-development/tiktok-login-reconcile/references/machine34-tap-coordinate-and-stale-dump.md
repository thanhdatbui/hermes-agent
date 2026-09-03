# Machine 34 final root cause — tap-coordinate miss + stale uiautomator dump (2026-08-07)

## The rabbit hole (how misdiagnosis happened)
A whole session was spent thinking machine 34's TikTok just wouldn't render the
profile tab (`profile tab tap → splash → feed`, classifier False, `SWITCHER_ANCHOR_AMBIGUOUS`
on every run, even after reboot). This team trusted the uiautomator dump line-by-line and
concluded "máy yếu / app bug" for hours. The user pushed back — correctly — that all machines
are the same model + resolution, so a per-machine software fault made no sense.

## Real root cause #1 — hardcoded tap coordinate is ABOVE the tab
The runner's `go_to_profile` taps the "Hồ sơ" (profile) bottom-nav tab at the **hardcoded
`(972, 1857)`** (defined in `social_reg_v1.py` as `"profile_tab": (972, 1857)`).

Actual tab bounds from the live dump:
```
Hồ sơ: [864,1864][1080,1903]  center = (972, 1883)
```
`y=1857` is **26 px ABOVE** the tab's top edge (1864) → the tap lands on the frame above the
tab bar → **nothing happens** → device stays on feed → profile never opens → dump stays feed →
`SWITCHER_ANCHOR_AMBIGUOUS`.

**Fix verification:** tapping the correct center `(972, 1883)` opened the real profile (`yobi`,
`@yobi1965`, 0 follow / 1 follower) confirmed by `screencap` + vision. This is a *hardcoded
coordinate* bug, not a device fault.

Lesson: when **one** machine in an identical fleet fails navigation while siblings pass,
suspect **hardcoded tap coordinates / UI offset drift** FIRST (verify against live bounds),
before blaming the ROM/API/network. Do not reason about a tap that you have not confirmed
lands on the target element by its actual `bounds`.

## Root cause #2 — stale uiautomator dump
`uiautomator dump` on this device returns **E=137 (killed)** (atx-agent wedged on
`futex_wait_queue_me`) AND `adb shell cat /sdcard/wd.xml` then returns **stale feed content**
("Tây Ninh", "Bạn bè") — NOT the real on-screen profile. The dump is stale, not the screen.

**Consequence:** any classifier/`expected_marker`/switcher logic that reads the XML sees FEED
even when the real screen is PROFILE. The screen is fine; the XML lies.

**Do NOT trust stale XML.** To learn what is actually on-screen, capture and inspect the real frame:
```
adb shell screencap -p /sdcard/scr.png
adb pull /sdcard/scr.png <local>.png
# then vision_analyze the png
```
`uiautomator dump` repair recipe (live-proven): `pkill -9 -f atx-agent` +
`am force-stop com.github.uiautomator` + retry dump. A reboot alone does NOT fix a wedged
atx-agent if the app foreground is busy / a popup is covering.

## Necessary boot normalization before any TikTok flow
After reboot, until the device is clean, uiautomator stays wedged / dump won't idle. Sequence:
1. Wait `sys.boot_completed = 1`.
2. **Dismiss the LSPosed banner** — "No LSPosed access !!!" (package `vn.vichanger.app`) with
   an `OK` button (`bounds [1308,655][1500,799]` → tap ~(1404, 727)). It covers the screen and
   wedges dump.
3. Ensure `tun0` (VPN/proxy watcher) is up and kicking.
4. Unlock + launch TikTok, WAIT for splash → feed to go idle before dumping.
Only then `uiautomator dump` yields `E=0` and real content. Use `dumpsys activity activities`.