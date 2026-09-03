# Profile Navigation Recovery: Camera/Overlay State

## Scope

Reusable recovery pattern for TikTok feed-session and multi-machine feed flows when Profile navigation reports that the target is missing from UI XML.

## Root-cause pattern

A missing bottom-navigation node is often a state problem, not a selector problem: TikTok is still on the Camera/Creation screen, a modal overlay, or another transient page. Two implementation defects commonly compound the symptom:

1. The overlay detector is case-sensitive while UIAutomator labels vary in case (`CAMERA` vs `camera`, `Photo` vs `photo`).
2. Recovery code references the first capture variable after a capture exception without initializing it, masking the original state and making the final error look like a navigation-selector failure.

## Correct recovery sequence

1. Keep navigation XML-first: never tap a coordinate unless a valid target node with bounds/center was found in the current XML.
2. Initialize the capture payload before entering the capture `try` block (`xml_text = ""`).
3. When the target is absent, inspect the captured XML for an allowlisted benign overlay.
4. For Camera/Creation, send BACK through the canonical adapter path:
   `ctx.adb.shell(["input", "keyevent", "4"])`.
5. Recapture XML after dismissal and resolve the Profile node again.
6. Only then tap Profile. If the node is still absent, return a blocker with the original capture/recovery evidence; do not blind-tap or claim success.

## Detector rule

Normalize combined XML/OCR text with `casefold()` before matching camera markers. Keep the existing marker threshold and allowlist; case normalization is the minimal fix and avoids widening detection into unrelated screens.

## Regression tests

The focused regression should assert all of the following:

- lower/mixed-case Camera XML is detected;
- recovery sends `input keyevent 4`;
- a second XML capture containing a valid bottom Profile node produces a successful navigation result whose selector source identifies post-dismiss recovery;
- no coordinate tap occurs before a valid XML node is found.

Run the focused camera/calibration/feed-navigation tests first. A broader feed suite may contain unrelated dirty-worktree failures (for example, stale fast-swipe expectations or mocks that do not provide the current ATX capture seam); report those separately rather than weakening this regression.

## Safety boundaries

Do not run a live farm batch as a substitute for the regression test. Do not force-stop TikTok, clear app data, restart ADB, or modify automation-core for this class of bug. Preserve dirty files outside the exact fix scope.
