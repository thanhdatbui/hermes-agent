# GPM Login UI Freeze / Infinite Loading Recovery

## Problem
GPM Login v4.3.6-stable WPF UI hangs with infinite loading spinner when opening Profiles tab.

## Root Causes (2026-09-03 session)

### Cause 1: Invalid Session State (`profile_page_session.dat`)
File format: `pageIndex,pageSize,groupId`
- **Bad value**: `2,500,1` → Page 2 with 500 profiles/page, but Group 1 only has ~33 profiles → UI queries non-existent page → infinite loop
- **Bad value**: `1,500,2` → Page 1, 500/page, Group 2 (doesn't exist) → same issue
- **Fix**: Reset to `1,10,1` (Page 1, 10 profiles/page, Group All)

```python
with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile_page_session.dat', 'w') as f:
    f.write('1,10,1')
```

### Cause 2: Profiles stuck in GroupId=0
- Profiles with `GroupId=0` don't appear in "All" group (GroupId=1)
- If session points to Group 1 but profiles are in Group 0 → empty result → UI spins
- **Fix**: `UPDATE Profiles SET GroupId = 1 WHERE GroupId = 0;` (for active profiles only)

### Cause 3: PageSize too large for WPF renderer
- PageSize > 20-30 causes WPF thread to choke rendering icons (Chrome, OS, Flag, Proxy, Open button)
- **Fix**: Keep pageSize ≤ 10 for stable UI

## Recovery Procedure (Exact Steps)

1. **Kill GPMLogin process**
   ```powershell
   Stop-Process -Name GPMLogin -Force -ErrorAction SilentlyContinue
   ```

2. **Restore database from backup** (if JsonData was corrupted)
   ```python
   import shutil
   shutil.copy2(
       r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\_backup\profile_data_backup.db',
       r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db'
   )
   ```

3. **Reset session files**
   ```python
   # profile_page_session.dat
   with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile_page_session.dat', 'w') as f:
       f.write('1,10,1')  # page=1, size=10, group=All

   # profile_page_setting.dat - keep default columns
   # {"ProxyTypeColumnVisible":true,"ProxyColumnVisible":false,"NoteColumnVisible":false,
   #  "LastRunColumnVisible":true,"TagColumnVisible":false,"OwnerColumnVisible":false,
   #  "StorageColumnVisible":false}
   ```

4. **Ensure active profiles have GroupId=1**
   ```sql
   UPDATE Profiles SET GroupId = 1 WHERE GroupId = 0 AND Name IN (...list of active profile names...);
   ```

5. **Set CreatedAt for correct sort order** (UI sorts by CreatedAt "Oldest first")
   ```python
   base = datetime(2024, 1, 1, 10, 0, 0)
   for idx, profile_id in enumerate(ordered_profile_ids):
       new_created = (base + timedelta(minutes=idx*10)).strftime('%Y-%m-%d %H:%M:%S')
       cur.execute('UPDATE Profiles SET CreatedAt = ? WHERE Id = ?', (new_created, profile_id))
   ```

6. **Restart GPMLogin** → UI loads instantly with correct order

## Profile Ordering Convention (Kibe Farm)
```
01_Rua → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10
→ 11 → 12-8801320930664 → 13-88001324341907 → 14-8801332045494 → 15-8801300413451 → 16-8801317040143
→ 10008 → 10009 → 10010 → 10011 → 10012 → 10013 → 10014 → 10015 → 10016 → 10017 → 10018 → 10019 → 10020 → 10021 → 10022 → 10023 → 10024
→ AMZ_Main
```

## Critical Rules
- **NEVER move profile folders** (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<ProfilePath>\`) — DB `ProfilePath` column maps 1:1
- **ALWAYS backup** `profile_data.db` → `_backup\profile_data_backup_YYYYMMDD.db` before ANY UPDATE
- **Hidden profiles (GroupId=0)**: 240 profiles in backup — filter `WHERE GroupId=0` when restoring, NEVER `LIMIT 5` (grabs original 16)
- **Duplicate names**: Some profiles exist in both GroupId=0 and GroupId=1 (e.g., `12-8801320930664`) — deduplicate before restore