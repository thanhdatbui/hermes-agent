# TikTok Account Tracker & Dashboard: Trending Rules and Default Avatar Detection

## 1. Trending Threshold Rule (Follower Delta >= 20 OR Heart Delta >= 50)

### Background & Pitfall:
- In `D:/Taadaa/tools/tiktok_dashboard.py`, the initial trending check was set too loose:
  `is_trending = (delta_f > 0) or (delta_h > 0) or (f_val >= 1000 and is_live)`
- Across a farm of 600 accounts, normal random fluctuations (+1 like or +1 follow) marked over 120 accounts (20.2%) as trending, causing massive false positives and conflicting with cronjob reports.
- In `D:/Taadaa/tools/tiktok_account_tracker.py`, the original check was `follower_delta >= 10 or heart_delta >= 50`.

### Canonical Standard:
- **Rule:** `follower_delta >= 20 or heart_delta >= 50` (or `follower >= 1000 and is_live`).
- **Sync Requirement:** Both `tiktok_account_tracker.py` (CLI/Cronjob/Excel export) and `tiktok_dashboard.py` (Web UI port 1905) must share identical threshold constants to prevent cross-channel discrepancy.
- **Boundaries:**
  - `delta_f = 19, delta_h = 0` -> False
  - `delta_f = 20, delta_h = 0` -> True
  - `delta_f = 0, delta_h = 49` -> False
  - `delta_f = 0, delta_h = 50` -> True

---

## 2. Default Avatar Detection via Web Profile HTML

### Detection Signature:
When scraping TikTok web profile (`https://www.tiktok.com/@username`) via `__UNIVERSAL_DATA_FOR_REHYDRATION__`:
- Account object: `user = data['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']['user']`.
- Avatar fields: `user.get('avatarThumb')` and `user.get('avatarLarger')`.
- **Default Avatar Signatures (Uncustomized Accounts):**
  1. URL path contains `musically-maliva-obj` or CDN asset ID `1594805258216454` (TikTok standard gray default placeholder).
  2. `avatarThumb` is null or empty string `""`.
- **Custom Avatar Signatures:**
  URL path contains `tos-alisg-avt-0068/...` or `tos-maliva-avt-0068/...` followed by a user-uploaded image hash.

### Helper Implementation:
```python
def is_default_avatar(avatar_url: str) -> bool:
    if not avatar_url:
        return True
    u = avatar_url.lower()
    return 'musically-maliva-obj' in u or '1594805258216454' in u
```

---

## 3. Storage and Reporting Schema:
- **SQLite Database (`snapshots` table in `D:/Taadaa/data/tiktok_tracker.db`):**
  - Added columns: `avatar_thumb TEXT`, `has_avatar INTEGER DEFAULT 1`.
- **Excel Report (`export_excel_report`):**
  - Added header column: `Avatar` (`CÓ` / `CHƯA CÓ`).
- **Telegram Summary Message (`generate_summary_message`):**
  - Includes line: `• Số nick chưa có avatar: X`.
- **Web Dashboard (port 1905):**
  - KPI card `⚠️ Chưa Avatar` highlighting accounts requiring avatar upload.
  - Filter button `⚠️ Chưa Avatar` to isolate pending accounts.
  - Badge `⚠️ NO AVATAR` in username cell.
