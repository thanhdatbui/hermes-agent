# Mode 2 flow order and verification reference

## Scope

This reference records the canonical, read-only-audited Mode 2' sequence for the TikTok Follow consumer. It distinguishes the anchor navigation path from the target-row follow path. It is a flow contract, not permission to run live automation or change code.

## Canonical sequence

1. Start from a proven Feed.
2. Search for the selected anchor UID.
3. Open the anchor's profile and verify exact identity before relationship or tab actions.
4. Inspect the anchor relationship action on the profile.
   - If already followed: do not tap Follow again.
   - If not followed: tap Follow on the anchor profile.
5. Pull-to-refresh the anchor profile and re-check the relationship action.
   - Still followed: persist the anchor follow and charge one budget unit.
   - Back to Follow: classify `FOLLOW_FAILED` and stop the session; do not recover into Module 1 or continue to another anchor.
6. Open the anchor's `Đã follow` / `Following` tab and prove the Following surface.
7. For each eligible internal target visible in that list, bind the action to that target row and tap Follow **on the row**. Do not describe this as tapping Follow on the search screen; search is only used to reach the anchor profile.
8. Freshly dump and verify the same row changed to the followed state.
9. For every successful target-row follow, open that target's profile and verify exact identity plus the relationship action in the immediately rendered profile. Do **not** pull-to-refresh or swipe the target profile: if TikTok has released the follow, the opened profile is expected to show `Follow`/`Follow lại`; if it is retained, it shows `Đã follow`/`Nhắn tin`.
   - `Đã follow`/`Nhắn tin`: accept the target.
   - `Follow`/`Follow lại`: `FOLLOW_FAILED` and stop.
   - Unknown identity/action or inability to restore the list: `MANUAL_REVIEW`; never silently record success.
10. Return to the Following list and continue within budget. Before a later anchor search, re-prove Feed.

## Review checklist

- Anchor follow happens on the anchor profile, before opening its Following list.
- Target follow happens on the Following-list row, not on the search result/profile screen.
- Target profile entry is post-follow verification, not the place where the target follow tap occurs.
- Pull-to-refresh is required only for a newly followed anchor before opening its Following list.
- For a newly followed target, trust the immediately rendered target profile action after opening it; do not add a refresh/swipe. `Follow`/`Follow lại` there is terminal `FOLLOW_FAILED`, not a reason to call recovery or Module 1.
- Report the three distinct surfaces separately: search result/navigation, anchor profile, and Following list/target profile.

## Fixture-queue pitfall

When target Path B loses its refresh/swipe recheck, remove the obsolete second target-profile XML from each fake-adapter queue. Otherwise the restore-list dump consumes the stale profile fixture and the test reports a misleading `MANUAL_REVIEW`. Keep the anchor's separate refresh fixture intact.

## Offline evidence pattern

The focused Mode 2 tests should cover at least:

- unfollowed anchor -> profile Follow -> refresh -> followed -> Following tab;
- target row Follow -> row-state verification -> target profile -> immediate action check shows followed, with no refresh/swipe;
- target row Follow -> immediate target-profile action shows Follow -> `FOLLOW_FAILED`;
- anchor refresh shows Follow -> immediate session stop without recovery.

A static flow audit must not run a real device, touch an account, or revert code.
