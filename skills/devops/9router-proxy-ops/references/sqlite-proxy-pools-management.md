# 9Router Proxy Pools Direct SQLite Management

Database path on Windows: `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`

## Table Schema: `proxyPools`
- `id` (TEXT, UUID v4)
- `isActive` (INTEGER, 1 or 0)
- `testStatus` (TEXT, 'active' / 'error' / 'untested')
- `data` (TEXT, JSON string)
- `createdAt` (TEXT, ISO-8601 UTC timestamp `YYYY-MM-DDTHH:MM:SS.mmmZ`)
- `updatedAt` (TEXT, ISO-8601 UTC timestamp `YYYY-MM-DDTHH:MM:SS.mmmZ`)

## JSON Structure inside `data`:
```json
{
  "name": "Imported test.taadaa.click:5101",
  "proxyUrl": "http://mobi1:TaadaaMobi%232026%21@test.taadaa.click:5101/",
  "noProxy": "",
  "type": "http",
  "strictProxy": 0,
  "lastTestedAt": "2026-08-20T04:17:47.174Z",
  "lastError": null
}
```
*Note: Username and Password in `proxyUrl` MUST be URL-encoded (e.g., `#` -> `%23`, `!` -> `%21`, `@` -> `%40`).*

## Syncing Farm Proxies from `PROXYgandienthoai.xlsx` to 9Router

When updating proxies on 9Router from the farm workbook:
1. Always delete only the targeted pool domain (e.g. `WHERE data LIKE '%test.taadaa.click%'`), DO NOT truncate `proxyPools` to preserve other active pools (`khoalee.duckdns.org`, `mirotik1.taadaa.click`, etc.).
2. Generate UUID v4 for new entries.
3. Keep URL encoding intact for credentials with special characters.
