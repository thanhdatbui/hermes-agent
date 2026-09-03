# Case UI-38: Search Card Avatar Touch Target & Follow Timeout Recovery

## Context & Problem
In TikTok Follow Mode 1 (`mode1_search_follow.py`), when searching for a target UID (e.g. `trieurdvg3z`), TikTok renders search results under the Top tab with an account card:
- Account Card RelativeLayout container: `id/v09` bounds `[0, 615][1080, 837]` (`clickable=True`).
- Child elements in TikTok 46.x:
  - `id/tv_username`: `Vy Gạo` (`clickable=False`)
  - `id/tv_aweme_id`: `trieurdvg3z` (`clickable=False`)
  - `id/tv_desc`: `0 follower` (`clickable=False`)
  - `id/tvn`: `Follow` button (`clickable=True`)
  - **No separate `ImageView` node** in the uiautomator accessibility hierarchy.

## Root Cause
1. `_exact_search_result_from_xml` traverses up to `target_element` (`id/v09`).
2. It looks for `avatar_targets` by searching for clickable descendant nodes containing an `ImageView` with matching bounds.
3. Because TikTok 46.x renders the avatar directly on canvas without an `ImageView` node, `avatar_targets` evaluates to `[]`.
4. The fallback `return nodes[element_index[target_element]]` returns the full card bounds `(0, 615, 1080, 222)`.
5. `tap_center` calculates center coordinates: `(540, 726)`.
6. On Android/TikTok, tapping the center of `id/v09` (at `x=540`) lands in inert whitespace or non-clickable text between the username and the Follow button. This tap is ignored and **fails to open the user profile**.
7. Because `_nav_search` assumes navigation succeeded, `follow_one_uid` evaluates the search results screen, returns `identity_mismatch`, and records `skipped`.
8. The screen remains on Search Results. The runner enters an endless loop of recovering Feed and searching the next UID until the parent runner's 1200s follow timeout expires (`Lý do: follow-timeout`).

## Resolution & Pattern
When `avatar_targets` is empty and `target_element` is a wide horizontal card (`w > h * 1.5`):
- Adjust the touch target bounds to the square avatar area on the left of the card:
  `bounds = (x, y, min(w, h), h)` and `bounds_size = (min(w, h), h)`.
- For `[0, 615][1080, 837]`, the target bounds become `(0, 615, 222, 222)`.
- `tap_center` then taps `(111, 726)` squarely in the avatar region, opening the profile immediately and reliably.

## Verification Checklist
1. Unit test `_exact_search_result_from_xml` on XML fixtures with `id/v09` without `ImageView` child -> proves bounds are adjusted to `(0, 615, 222, 222)`.
2. Unit test with explicit clickable `ImageView` avatar -> proves existing behavior is preserved.
3. Test assertion synchronization: Update mock tap coordinate assertions in Mode 1 tests (e.g. `test_mode1_search_user_tab.py`) from center card `(540, y)` to avatar center `(111, y)` to match normalized bounds `(0, y, 222, 222)`.
4. Live device canary on machine hitting follow-timeout -> verifies search navigates to profile, classifies relationship action, and completes follow without timeout.
