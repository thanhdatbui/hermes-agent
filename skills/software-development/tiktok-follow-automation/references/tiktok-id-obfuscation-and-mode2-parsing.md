# TikTok ID Obfuscation & Mode 2 Following List Parsing

## 1. Profile Action Button vs Stat Counter IDs
- **Action Buttons (`Follow` / `Nhắn tin` / `Đã follow`)**:
  - TikTok obfuscates IDs per build: `id/fds` (m1), `id/ff8` (m2), `id/fij` (m6), `id/fi6` (m16), or general regex `id/f[a-z0-9]{2,3}$`.
  - Position: sits in the action button band (y: 750..1000, height: 90..180px).
- **Stat Counter IDs (`Đã follow`, `Follower`, `Thích`)**:
  - IDs: `id/sdn`, `id/shq`, `id/svt`, `id/svs`, `id/suu`, `id/sut`.
  - Position: sits above action band (y: 700..760, height: 40..50px).
  - CRITICAL: Must be excluded from action button classification to prevent confusing profile follow counts with active follow relationship state.

## 2. Mode 2 Following List Username Extraction & Farm Internal Filtering
- **Username vs Subtitle in List**:
  - When user has no bio/mutual, `id/txt_user_name` carries the username, and `id/txt_desc` carries subtext (`"Được follow bởi..."`).
  - When user has separate display name and @username, `id/txt_desc` carries `@username`.
  - Resolution: Strip `@` from `txt_desc` if prefixed, otherwise fallback to `txt_user_name`. Do NOT pass raw subtext to `internal_uids` matching.
- **Empty Following List Detection**:
  - Titles across builds: `id/yby`, `id/yhj`, `id/yxo`.
  - Selected count: `"0"` and message: `id/message_tv`.
