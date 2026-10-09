# Chromium / GPMLogin Credential & Session Cookie Audit Technique

## 1. Non-destructive SQLite Inspection (`mode=ro`)
When inspecting live Chromium profile databases (`Login Data`, `Cookies`, `Web Data`) that may be open by background processes or sensitive to corruption:
- Always use URI read-only connection: `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`
- Query `logins`: `SELECT origin_url, action_url, username_value, length(password_value) FROM logins`
- Distinguish Google Account origin (`accounts.google.com` / `google.com`) vs external websites using Gmail as username.

## 2. Chromium Cookie Timestamp & Expiration Calculation
Chromium cookies store `expires_utc` as microseconds since **January 1, 1601 UTC** (Windows FileTime epoch).
To verify active/live session status in Python:

```python
import time

CHROME_EPOCH_DELTA = 11644473600  # seconds between 1601-01-01 and 1970-01-01
now_chrome = int((time.time() + CHROME_EPOCH_DELTA) * 1000000)

# In SQLite cookies query:
# expires_utc == 0 (Session Cookie) OR expires_utc > now_chrome (Active Non-Expired)
```

Critical Google Session Cookies:
`SID`, `HSID`, `SSID`, `SAPISID`, `APISID`, `__Secure-1PSID`, `__Secure-3PSID`, `__Secure-1PAPISID`, `__Secure-3PAPISID`, `OSID`, `__Secure-OSID`.

## 3. High-Speed Selective Zip Backup Inspection (Zero Disk Bloat)
Large GPM profile zip archives (e.g. 3.5 GB – 8 GB) contain thousands of cache/extension files. To audit credential state without extracting gigabytes to disk:
1. Open with `zipfile.ZipFile(zpath, 'r')`.
2. Filter namelist only for target metadata files:
   - `*/Default/Login Data`
   - `*/Default/Network/Cookies` (or `*/Default/Cookies`)
   - `*/Default/Preferences`
   - `*/Default/Web Data`
3. Extract only those 4 files per profile to a `tempfile.mkdtemp()`.
4. Run SQLite / JSON parser and instantly cleanup temp folder.
Audit runs in ~5-10 seconds for 250+ profiles instead of minutes.
