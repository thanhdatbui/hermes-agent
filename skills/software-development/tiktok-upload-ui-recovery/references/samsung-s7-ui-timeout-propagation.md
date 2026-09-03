# Samsung S7 UI-timeout propagation

## Core distinction

A Samsung S7 can legitimately need tens of seconds to render a picker, editor, profile surface, or post composer. Use a bounded 60-second budget for UI XML capture and semantic UI polling. Do not convert every timeout in the system: atomic ADB commands and transport/lock/process operations retain their operation-specific budgets.

## Evidence classification

| Evidence | Interpretation | Action |
|---|---|---|
| Fresh screenshot/XML shows a valid TikTok surface still rendering or missing its expected control | UI render/read wait may be too short | Repeat bounded UI polling up to 60s; recapture after each state-changing action |
| `non_xml_ui_dump`, invalid XML, or UiAutomator/ATX returns early | UI service/transport health failure, not a normal wait timeout | Run the configured ATX-kill → force-stop/relaunch → reboot ladder; do not just sleep longer |
| Fresh XML/screenshot proves Profile/video detail, packageinstaller permission popup, or another overlay is foreground | Wrong surface/overlay, not insufficient wait | Handle the recognized popup or navigate only with evidence; preserve foreground safety gate; never tap blindly |

## Cross-repo propagation checklist

1. Snapshot `git status`, branch/upstream, target-file mtimes and EOL before writing.
2. Change shared `automation-core` UI defaults first, then affected consumers; exclude `.runtime`, build/dist, generated artifacts, and unrelated dirty files.
3. Target: UI XML capture, element/predicate polling, picker/editor readiness, startup app-focus verification, and post-recovery UI recapture. Leave `tap`, `swipe`, `back`, `wm size`, force-stop, transfer, lock/database, network, reboot, and process command budgets unchanged unless their own contract explicitly says otherwise.
4. Add a focused regression assertion for each changed default/call-site. Run focused tests, `py_compile`, and `git diff --check`; run the canonical suite when possible.
5. Stage only allowlisted production/test files. Independently verify commit file list, SHA, upstream, remote head, and remaining unrelated dirty files. A worker summary or exit code is not completion proof.
6. If a repository is dirty from another workstream, do not revert or absorb it. Commit only the timeout files if safe; otherwise report the exact blocker and keep the unrelated work intact.

## Known session patterns

- The m5 `non_xml_ui_dump` reproduced after roughly 16 seconds despite a 60-second configured UI budget; the fix was B1 ATX-kill routing at startup, not more waiting.
- The m34 picker failure was a `packageinstaller/GrantPermissionsActivity` media permission popup covering TikTok; the safe fix was to recognize/allow the popup before rechecking foreground, not to bypass the gate.
- The m74 failure showed a valid but wrong Profile/video-detail surface with no create button; waiting longer could not navigate it. Because that machine is historically fragile, the shared navigation flow was not changed without a separate evidence-backed test.

This file is a condensed reference, not a substitute for the live run artifacts or current repository rules.
