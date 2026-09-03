# TikTok Follow Action Buttons & Following List Extraction (TikTok 46.x+)

## 1. Action Button IDs & Stat Counters on Profile
On various Samsung S7 devices and TikTok versions (46.x+), resource IDs are obfuscated:
- **Action Button IDs (Follow / Nhắn tin / Bạn bè):**
  - Machine 1: `id/fds`
  - Machine 2: `id/ff8`
  - Machine 6+: `id/fij`
  - Machine 16+: `id/fi6`
  - Generic pattern: `re.search(r"id/f[a-z0-9]{2,3}$", rid)` or within action button Y-band (`750 <= y <= 1000` and `90 <= h <= 180`).
- **Stat Counter IDs (Đã follow, Follower, Thích counts):**
  - `id/sdn`, `id/shq`, `id/svt`, `id/svs`, `id/suu`, `id/sut` (must be strictly filtered out to avoid false positive classification).

## 2. Following List Extraction (Module 2)
In the TikTok Following list (`Đã follow N`):
- **Display Name vs Username:**
  - Case 1 (Has custom display name): `txt_user_name` contains Display Name (`laphuong1308`), while `txt_desc` contains `@username` (`@laphufkc18d`). Must extract username by stripping `@`.
  - Case 2 (No custom display name): `txt_user_name` contains the username (`allisononels67`), while `txt_desc` contains subtext (*"Được follow bởi..."*, *"Follow ... +5"*, or empty). Must fallback to `txt_user_name` when `txt_desc` starts with subtext indicators.
- **Empty Following List Detection:**
  - Headers: `android:id/text1` selected with text `"Đã follow 0"`.
  - Title IDs: `id/yby`, `id/yhj`, `id/yxo`.
  - Message ID: `id/message_tv`.
