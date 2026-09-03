# GPM WPF Mixed-Schema + Missing-Index Fix (2026-09-03, GPM 4.3.0)

## Symptom
- Page 1 (size 10) loads fine; page 2 lags/hangs even at size 10.
- Assumption "JsonData too big (2149→2394 chars)" was wrong: DB queries were all <2ms.
- Local API also showed the split: `page=1 per_page=10` ~470ms first-hit vs `page=2` ~31ms,
  but Admin rows returned `raw_proxy=""`, `browser_version=None`.

## Diagnosis (run before touching anything)
```python
import sqlite3, json
from collections import Counter
conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
cur = conn.cursor()
cur.execute('SELECT JsonData FROM Profiles WHERE GroupId=1')
print(Counter(len(json.loads(js)) for (js,) in cur.fetchall()))
# BAD: {130: 12, 124: 5, 6: 17} — mixed schema in one Group = WPF template fallback per row
# GOOD: {130: 34} — single bucket

cur.execute('EXPLAIN QUERY PLAN SELECT * FROM Profiles WHERE GroupId=1 ORDER BY CreatedAt LIMIT 10 OFFSET 10')
print(cur.fetchall())
# BAD: SCAN Profiles + USE TEMP B-TREE FOR ORDER BY (no index)
# GOOD: SEARCH Profiles USING INDEX idx_profiles_groupid_createdat (GroupId=?)
```
- API check: every row must have non-empty `raw_proxy`; `browser_version` must not be None.
- The 6-key Admin rows (`10008–10024`, only `raw_proxy/proxy_*`) lack `Proxy/UserAgent/AudioNoise/WebGLRenderer/MacAddress`
  → DataGrid icon/proxy bindings throw per row, exactly on page 2 (rows 11–20).
- The 124-key rows (`02/06/07/AMZ_Main/16-empty`) lack `raw_proxy/proxy_*` → API `raw_proxy=""`.

## Fix (DB-only, binary untouched, no fingerprint field removed)
1. Backup + row-count guard:
```python
import shutil, datetime
src = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db'
shutil.copy2(src, src.replace('profile_data.db', f'_backup\\profile_data_backup_{datetime.date.today():%Y%m%d}_uischema.db'))
# assert SELECT count(*) == 255 before AND after
```
2. Rebuild each 6-key Admin from a 124-key GroupId=0 donor whose `WebGLRenderer`
   is NOT already used in GroupId=1 (harvest ~53 candidates, need 17).
   Per-row overrides (never clone a full JsonData from one template):
   - `Name` = short id (`10008`), `Proxy`/`raw_proxy` = row's OWN proxy
     (`mirotik1.taadaa.click:10008..10024:admin@1:admin@1`), split into
     `proxy_type=http, proxy_host, proxy_port, proxy_user, proxy_pass`
   - `ProxyRegion=VN, Timezone=Asia/Bangkok, TimezoneMode=1, WinVersion=Windows 10`
   - `UserAgent` = Chrome 127 UA, `BrowseVersion=127.0.6533.73`
   - Fresh random `AudioNoise` (uniform 0–1, checked against used set) + fresh random `MacAddress`
   - Result: 130 keys each.
3. Proxy-complete the 124-key rows (02/06/07/AMZ_Main/16-empty): parse their own
   `Proxy` field into `raw_proxy/proxy_*` → 130 keys.
4. Add pagination index (the actual ORDER BY the UI uses):
```sql
CREATE INDEX IF NOT EXISTS idx_profiles_groupid_createdat ON Profiles(GroupId, CreatedAt);
```
5. Verify (all must pass):
   - `Counter` = `{130: 34}`; `PRAGMA quick_check=ok`; count still 255.
   - 34/34 unique `AudioNoise`, `WebGLRenderer`, `MacAddress` (clone = Google mass-logout).
   - API: `page=1 per_page=200` ~48ms, `empty_proxy=0`.

## Result on this session
- Before: `{130: 12, 124: 5, 6: 17}`, page-2 stall, Admin `browser_version=None`.
- After: `{130: 34}`, avg JsonData 4651 chars (full schema, fingerprints KEPT),
  page1/size200 ~48ms. Session file `profile_page_session.dat` left at `1,10,1`.

## Rules for next time
- Page 2 lags but page 1 is smooth → suspect mixed schema at the page boundary, not size.
- Never `UPDATE JsonData` from a single donor for >1 profile (fingerprint clone → mass logout).
- `WebGL_MAX_*/STENCIL/ALIALED_*` constants are NOT safe to strip — they vary per GPU
  (Intel vs NVIDIA vs AMD renderers observed) and are part of anti-detect surface.
- sqlite3 CLI is absent on this host — use python3 + sqlite3 module.
- tasklist is empty under git-bash — verify via Local API port 19995, not process list.
