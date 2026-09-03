# TikTok 46.x UI Selectors & Following List Row Parsing Reference

## 1. Profile Relationship Action Button vs Stat Counters
On TikTok 46.x profile pages:
- **Action Button IDs (`_ACTION_BUTTON_IDS`):**
  - `id/fds` (Machine 1 / older builds)
  - `id/ff8` (Machine 2 / intermediate builds)
  - `id/fij` (Machine 6+ / modern builds)
  - `id/fi6` (Machine 16 / S7 builds)
  - Generic fallback regex: `id/f[a-z0-9]{2,3}$` or action Y-band (`750 <= y <= 1000`, `90 <= h <= 180`).
- **Stat Counter IDs (`_STAT_COUNTER_IDS`):**
  - `id/sdn`, `id/shq`, `id/svt`, `id/svs`, `id/suu`, `id/sut`
  - Stat counters render text like "Đã follow" (count of followings) or "Follower" regardless of follow status — MUST be excluded from action classification.

## 2. Search Navigation & Back Selectors
- Top-left search back button: `id/bow`, `id/bqp`, `id/back_btn` or clickable node with bounds `x < 200, y < 250`.
- Tapping top-left icon is required to dismiss search history/autocomplete cleanly back to Feed.

## 3. Following / Follower Relation List (Mode 2)
- **RecyclerView Containers:** `id/u5r`, `id/u_q`, `id/uoc`.
- **Action Buttons in Row:** `id/tcj`, `id/thb`, `id/tvn` (Button class, bounds `w: ~264, h: ~84`).
- **Empty Surface Proof:**
  - ViewPager: `id/viewpager`
  - Empty Title IDs: `id/yby`, `id/yhj`, `id/yxo` (Button class, text `Đã follow` / `Follower`, non-clickable).
  - Empty Message: `id/message_tv` ("Khi người dùng này bắt đầu Follow...").

## 4. Username / Handle Extraction from List Rows
A follower row can present two patterns:
1. **With Custom Display Name:**
   - `id/txt_user_name` = display name (e.g. `laphuong1308`)
   - `id/txt_desc` = handle prefixed with `@` (e.g. `@laphufkc18d`)
   - -> Target handle is extracted from `@laphufkc18d` -> `laphufkc18d`.
2. **Without Custom Display Name:**
   - `id/txt_user_name` = username handle (e.g. `allisononels67`)
   - `id/txt_desc` = subtext (e.g. `Được follow bởi...` or `Follow ...`)
   - -> Subtext indicators detected, target handle extracted from `id/txt_user_name` -> `allisononels67`.

## 5. Row Deduplication Tolerance
- On 1080x1920 displays, `txt_user_name` (Y ~569) and `txt_desc` (Y ~632) are separated by ~63px vertically within the same row.
- Any Y-band overlap or deduplication check (`_row_y`, `seen_y`) must use `abs(y_top - sy) < 100` (not `< 40`) to avoid splitting the same row into two duplicate entries.
