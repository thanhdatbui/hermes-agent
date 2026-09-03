# Focus-loss preflight recovery: nested capture metadata

## Session lesson

In `multi-machine-feed-session`, a profile-navigation focus failure can be emitted by a capture/safety row whose authoritative foreground package is nested under `extra`, not at the row top level. A helper that only reads `row["focus_package"]` / `row["focused_package"]` can miss a real `com.sec.android.app.launcher` or `com.android.systemui` state and return the original `TikTok focus lost` failure without entering the bounded recovery handler.

## Evidence pattern

Forensic confirmation requires the same run-scoped chain:

```text
log.jsonl event
  -> exact capture attempt
  -> ui.xml root package + matching screen.png
  -> summary/manifest stop reason
  -> caller seam + recovery handler
```

A Telegram alert or a directory name is not enough. Redact account identifiers in reports.

## Correct implementation pattern

When classifying launcher/SystemUI focus loss, normalize both metadata shapes:

```python
extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
focus_package = str(
    row.get("focus_package")
    or row.get("focused_package")
    or extra.get("focus_package")
    or extra.get("focused_package")
    or ""
)
```

Then keep the predicate narrow: the package must be non-empty, differ from the configured TikTok package, and match an allowlisted launcher/SystemUI signature. Do not classify arbitrary third-party packages as launcher recovery without evidence.

The profile-navigation caller must route this signature through the existing bounded handler, not through a generic popup dismiss path:

1. capture the navigation blocker;
2. classify Launcher/SystemUI focus from normalized metadata and exact artifact;
3. reserve/recover with the existing one force-stop/relaunch policy;
4. retry navigation once;
5. require a fresh TikTok focus/navigation result before continuing;
6. otherwise preserve the blocker and finish fail-closed.

## Required regressions

- A row with top-level `focus_package=com.sec.android.app.launcher` enters recovery.
- A capture row with `extra.focused_package=com.sec.android.app.launcher` enters recovery.
- A capture row with `extra.focus_package=com.android.systemui` enters recovery.
- The profile-navigation seam calls the bounded relaunch/retry handler and does not fall through to generic popup handling.
- Existing post-swipe launcher recovery remains green.
- A non-allowlisted package still fails closed and does not relaunch.

Run focused tests first, then the feed-session and feed-swipe suites. No live device/ADB run is implied by offline regression success.

## Pitfall

Do not conclude that a newer post-swipe auto-relaunch commit caused the incident merely because counters changed. Map the exact failing event (`dismiss_notification_shade -> tap_profile`) to the changed caller before attributing regression. A fix in the post-swipe seam does not cover profile-preflight navigation.
