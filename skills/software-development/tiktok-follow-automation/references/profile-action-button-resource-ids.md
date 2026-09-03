# TikTok Profile Action Button & Stat Counter Resource IDs

## 1. Action Button Resource IDs (`_ACTION_BUTTON_IDS`)
When classifying profile relationship status (`classify_button` in `verify_follow.py`), the primary truth is the exact action button:
- `id/fds` (Legacy / Machine 1 variant)
- `id/ff8` (Machine 2 variant)
- `id/fij` (Machine 6 / TikTok 46.x multi-machine variant)

These buttons represent the actionable state on a target profile:
- **Unfollowed**: `Follow` / `Follow lại` / `Theo dõi`
- **Followed**: `Nhắn tin` / `Đã follow` / `Bạn bè` / `Message`

## 2. Stat Counter Resource IDs (Must Exclude from Action Classifiers)
TikTok profile headers render stat count labels that include matching text (e.g., `Đã follow`, `Follower`) which are NOT actionable buttons. If not excluded in fallback label scanners, they collide with action button texts and produce ambiguous `unknown` classifications.
Known stat counter IDs:
- `id/sdn`
- `id/shq`
- `id/svt`
- `id/svs`
- `id/suu`
- `id/sut`
- `id/text1` (Header tab bar in relation view)

## 3. Profile Header Handle Resource IDs (`@uid` Variations)
In TikTok 46.x builds across different devices, the profile `@handle` (username) renders under various obfuscated resource IDs:
- `id/sf5` (e.g. Machine 34 / standard 46.3.3)
- `id/sj8` (e.g. Machine 54)
- `id/ss2` (e.g. Machine 4, Machine 5)
- `id/sxa` (e.g. Machine 8, Machine 24, Machine 45)
- `id/swb` (e.g. Machine 60, Machine 67)

**Rule**: Never hardcode a single handle resource ID (like `id/sf5`).
To prevent false-positive rejection ("hồ sơ thiếu handle (@uid) ở header — từ chối tap Following"):
1. Scan for `@`-prefixed text or `content-desc` in the upper header band (`y < 650`).
2. Verify exact normalized handle equality (`_normalize_handle(val) == target_norm`).
3. Enforce that exactly ONE matching header node exists (rejects ambiguous suggestion cards).
4. Standardize coordinate representation when comparing `UIElement.bounds` `(l, t, r, b)` with `parse_nodes` `(x, y, w, h)` via `_bounds_rect(..., size_form=True)`.

## 4. Common Failure Modes & Diagnostics
### `MANUAL_REVIEW: không thấy đúng một nút Follow trên exact profile`
Occurs when `classify_button` returns `unknown`.
- **Cause 1 (New Action Button ID)**: The device's TikTok build renders action buttons under an unregistered resource ID (e.g. `id/fij`), causing primary action resolution to find 0 matches.
- **Cause 2 (Already-Followed Collision)**: If a target is already followed, its action button is `Nhắn tin` (`id/fij`), while the profile header displays `Đã follow` (`id/svt`). Because `id/fij` is missing and `id/svt` was not excluded, the fallback classifier sees both `followed` and `not_followed` labels, failing closed to `unknown` instead of returning `followed` (to be skipped as `đã follow sẵn`).
