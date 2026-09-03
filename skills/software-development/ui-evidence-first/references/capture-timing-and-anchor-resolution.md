# Capture timing and semantic anchor resolution

## Reusable investigation pattern

When a UI automation regression appears after screenshots/XML dumps were removed or moved:

1. Review Git history by path and by string-diff (`capture_screenshot`, `dump_hierarchy`, XML capture helpers, sleeps, retry loops), not only by commit subject.
2. Compare the exact pre/post call sequence around each swipe, navigation action, and selector resolution. A capture may have been serving as an implicit settle point.
3. Separate three claims:
   - **Capture timing hypothesis:** removing a dump may expose a transition race.
   - **Selector hazard:** a broad fallback may select an unrelated node.
   - **Live root cause:** requires the exact incident XML, matching screenshot, and log timeline.
4. If live artifacts are missing, do not operate the device to recreate the incident. Build a sanitized offline fixture and label the live conclusion `UNPROVEN`.

## Regression fixture shape

Use a minimal XML fixture with:

- the expected identity or canonical switcher control;
- a creator/public-profile node that looks valid and lies in the same header region;
- stale or mismatched identity data, if testing a transition race.

Assert that the resolver returns the semantic/resource-backed intended node or `None`; it must never return the creator/profile node. Also test that an old element is not reused after `BACK` or a layout-changing transition: recapture XML, resolve a fresh anchor, and assert the tap bounds come from the fresh node.

## Acceptance evidence

Run, as applicable:

- focused resolver regression;
- full consumer smoke suite;
- canonical account-switcher suite;
- syntax compilation and `git diff --check`.

Report exact pass/skip/fail counts. A successful command wrapper, ADB return code, or selector object alone is not proof that the intended UI state was reached.

## Pitfall

Do not “fix” a missing capture by blindly adding screenshots everywhere. First prove whether it was a synchronization gate, an evidence requirement, or neither; then add the smallest bounded capture/settle/verification change needed.
